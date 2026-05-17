from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.hub import Hub, HubMember
from app.models.user import User
from app.schemas.hub import HubCreate, HubUpdate


def list_hubs(db: Session, include_inactive: bool = False) -> list[Hub]:
    statement = select(Hub).order_by(Hub.name.asc())

    if not include_inactive:
        statement = statement.where(Hub.is_active == True)

    return list(db.scalars(statement).all())


def get_hub_or_404(db: Session, hub_id: str) -> Hub:
    hub = db.get(Hub, hub_id)

    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub was not found.",
        )

    return hub


def get_hub_by_slug_or_404(db: Session, slug: str) -> Hub:
    hub = db.scalars(
        select(Hub)
        .options(joinedload(Hub.members))
        .where(
            Hub.slug == slug,
            Hub.is_active == True,
        )
    ).first()

    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub was not found.",
        )

    return hub


def create_hub(db: Session, payload: HubCreate) -> Hub:
    existing = db.scalars(
        select(Hub).where(Hub.slug == payload.slug)
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hub slug already exists.",
        )

    hub = Hub(
        name=payload.name,
        slug=payload.slug,
        description=payload.description,
        cover_image_url=payload.cover_image_url,
        is_active=True,
    )

    db.add(hub)
    db.commit()
    db.refresh(hub)

    return hub


def update_hub(db: Session, hub_id: str, payload: HubUpdate) -> Hub:
    hub = get_hub_or_404(db, hub_id)

    update_data = payload.model_dump(exclude_unset=True)

    if "slug" in update_data:
        existing = db.scalars(
            select(Hub).where(
                Hub.slug == update_data["slug"],
                Hub.id != hub.id,
            )
        ).first()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Hub slug already exists.",
            )

    for field, value in update_data.items():
        setattr(hub, field, value)

    db.add(hub)
    db.commit()
    db.refresh(hub)

    return hub


def join_hub(db: Session, hub_id: str, user: User) -> HubMember:
    hub = get_hub_or_404(db, hub_id)

    if not hub.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot join an inactive hub.",
        )

    existing = db.scalars(
        select(HubMember).where(
            HubMember.hub_id == hub_id,
            HubMember.user_id == user.id,
        )
    ).first()

    if existing:
        return existing

    member = HubMember(hub_id=hub_id, user_id=user.id)

    db.add(member)
    db.commit()
    db.refresh(member)

    return member


def leave_hub(db: Session, hub_id: str, user: User) -> None:
    membership = db.scalars(
        select(HubMember).where(
            HubMember.hub_id == hub_id,
            HubMember.user_id == user.id,
        )
    ).first()

    if membership:
        db.delete(membership)
        db.commit()