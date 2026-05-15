from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import Content, ContentStatus
from app.models.engagement import Follow
from app.models.user import User, UserRole


WRITER_ROLES = {
    UserRole.WRITER,
    UserRole.TEACHER,
    UserRole.ADMIN,
    UserRole.MODERATOR,
}


def is_writer_user(user: User) -> bool:
    return user.role in WRITER_ROLES


def get_writer_or_404(db: Session, writer_id: str) -> User:
    writer = db.get(User, writer_id)

    if not writer or not is_writer_user(writer):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Writer was not found.",
        )

    return writer


def get_writer_stats(db: Session, writer_id: str) -> dict[str, int]:
    followers_count = db.scalar(
        select(func.count())
        .select_from(Follow)
        .where(Follow.following_id == writer_id)
    ) or 0

    published_count = db.scalar(
        select(func.count())
        .select_from(Content)
        .where(
            Content.author_id == writer_id,
            Content.status == ContentStatus.PUBLISHED,
        )
    ) or 0

    return {
        "followers_count": followers_count,
        "published_count": published_count,
    }


def list_writers(db: Session) -> list[User]:
    return list(
        db.scalars(
            select(User)
            .where(
                User.is_active == True,
                User.role.in_(list(WRITER_ROLES)),
            )
            .order_by(User.created_at.desc())
        ).all()
    )


def list_writer_content(
    db: Session,
    writer_id: str,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Content], int]:
    get_writer_or_404(db, writer_id)

    statement = (
        select(Content)
        .where(
            Content.author_id == writer_id,
            Content.status == ContentStatus.PUBLISHED,
        )
        .order_by(Content.published_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_statement = (
        select(func.count())
        .select_from(Content)
        .where(
            Content.author_id == writer_id,
            Content.status == ContentStatus.PUBLISHED,
        )
    )

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total