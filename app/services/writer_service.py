from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.content import Content, ContentStatus
from app.models.engagement import Follow
from app.models.user import User, UserRole

# NOTE: includes SUPER_ADMIN for consistency with ensure_can_write_content
# in content_service.py -- a super admin who authors content should be
# treated as a writer for search/display purposes, not just permitted to
# write but then invisible everywhere writers are listed.
WRITER_ROLES = {
    UserRole.WRITER,
    UserRole.TEACHER,
    UserRole.ADMIN,
    UserRole.SUPER_ADMIN,
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


def get_writer_stats(db: Session, writer_id: str) -> dict[str, int | float]:
    total_content = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(Content.author_id == writer_id)
        )
        or 0
    )

    drafts = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(
                Content.author_id == writer_id,
                Content.status == ContentStatus.DRAFT,
            )
        )
        or 0
    )

    pending = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(
                Content.author_id == writer_id,
                Content.status == ContentStatus.PENDING_REVIEW,
            )
        )
        or 0
    )

    published = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(
                Content.author_id == writer_id,
                Content.status == ContentStatus.PUBLISHED,
            )
        )
        or 0
    )

    rejected = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(
                Content.author_id == writer_id,
                Content.status == ContentStatus.REJECTED,
            )
        )
        or 0
    )

    followers_count = (
        db.scalar(
            select(func.count())
            .select_from(Follow)
            .where(Follow.following_id == writer_id)
        )
        or 0
    )

    # Placeholders for now until qualified-read / payout tables are wired.
    likes_received = 0
    comments_received = 0
    bookmarks_received = 0
    qualified_reads = 0
    estimated_partner_reads = 0

    estimated_earnings_total = 0.0
    estimated_earnings_pending = 0.0
    estimated_monthly_earnings = 0.0

    return {
        "total_content": total_content,
        "drafts": drafts,
        "pending": pending,
        "published_count": published,
        "rejected": rejected,
        "followers_count": followers_count,
        "likes_received": likes_received,
        "comments_received": comments_received,
        "bookmarks_received": bookmarks_received,
        "qualified_reads": qualified_reads,
        "estimated_partner_reads": estimated_partner_reads,
        "estimated_earnings_total": estimated_earnings_total,
        "estimated_earnings_pending": estimated_earnings_pending,
        "estimated_monthly_earnings": estimated_monthly_earnings,
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


def get_writer_relationship(db: Session, writer_id: str, user: User) -> dict:
    writer = get_writer_or_404(db, writer_id)

    is_self = writer.id == user.id
    following = False

    if not is_self:
        existing = db.scalars(
            select(Follow).where(
                Follow.follower_id == user.id,
                Follow.following_id == writer_id,
            )
        ).first()

        following = existing is not None

    return {
        "following": following,
        "is_self": is_self,
    }
