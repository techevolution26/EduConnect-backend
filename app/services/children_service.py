from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.content import Content, ContentStatus, ContentType
from app.models.education import ChildrenContent
from app.models.user import User, UserRole
from app.schemas.education import ChildrenContentCreate


def ensure_can_create_children_content(user: User) -> None:
    if user.role not in {UserRole.ADMIN, UserRole.MODERATOR}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins or moderators can add content to the children section.",
        )


def get_children_content_or_404(db: Session, children_content_id: str) -> ChildrenContent:
    item = db.scalars(
        select(ChildrenContent)
        .options(joinedload(ChildrenContent.content))
        .where(ChildrenContent.id == children_content_id)
    ).first()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Children content was not found.",
        )

    return item


def create_children_content(
    db: Session,
    payload: ChildrenContentCreate,
    user: User,
) -> ChildrenContent:
    ensure_can_create_children_content(user)

    content = db.get(Content, payload.content_id)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content was not found.",
        )

    if content.content_type != ContentType.CHILDREN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Content type must be CHILDREN.",
        )

    if content.status != ContentStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Children content must be approved and published first.",
        )

    existing = db.scalars(
        select(ChildrenContent).where(
            ChildrenContent.content_id == payload.content_id
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This content is already in the children section.",
        )

    item = ChildrenContent(**payload.model_dump())

    db.add(item)
    db.commit()
    db.refresh(item)

    return item


def list_children_content(
    db: Session,
    age_group: str | None = None,
) -> list[ChildrenContent]:
    statement = (
        select(ChildrenContent)
        .join(Content, Content.id == ChildrenContent.content_id)
        .options(joinedload(ChildrenContent.content))
        .where(Content.status == ContentStatus.PUBLISHED)
        .order_by(ChildrenContent.created_at.desc())
    )

    if age_group:
        statement = statement.where(ChildrenContent.age_group == age_group)

    return list(db.scalars(statement).all())