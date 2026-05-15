from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.hub import Hub, HubMember
from app.schemas.hub import HubCreate, HubUpdate
from app.models.user import User


def list_hubs(db: Session) -> list[Hub]:
    return list(
        db.scalars(
            select(Hub)
            .where(Hub.is_active == True)
            .order_by(Hub.name.asc())
        ).all()
    )


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
        .where(Hub.slug == slug)
    ).first()

    if not hub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hub was not found.",
        )

    return hub


def create_hub(db: Session, payload: HubCreate) -> Hub:
    existing = db.scalars(select(Hub).where(Hub.slug == payload.slug)).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hub slug already exists.",
        )

    hub = Hub(**payload.model_dump())

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
    get_hub_or_404(db, hub_id)

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