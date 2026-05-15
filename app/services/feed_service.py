from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.content import Content, ContentStatus
from app.models.engagement import Follow
from app.models.hub import HubMember
from app.models.user import User, UserRole


def list_discovery_feed(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = None,
    category_id: str | None = None,
    hub_id: str | None = None,
) -> tuple[list[Content], int]:
    filters = [Content.status == ContentStatus.PUBLISHED]

    if content_type:
        filters.append(Content.content_type == content_type)

    if category_id:
        filters.append(Content.category_id == category_id)

    if hub_id:
        filters.append(Content.hub_id == hub_id)

    statement = (
        select(Content)
        .where(and_(*filters))
        .order_by(Content.published_at.desc(), Content.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_statement = select(func.count()).select_from(Content).where(and_(*filters))

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total


def search_content(
    db: Session,
    query: str,
    skip: int = 0,
    limit: int = 20,
    content_type: str | None = None,
    category_id: str | None = None,
) -> tuple[list[Content], int]:
    search_value = f"%{query.strip()}%"

    filters = [
        Content.status == ContentStatus.PUBLISHED,
        or_(
            Content.title.ilike(search_value),
            Content.excerpt.ilike(search_value),
            Content.body.ilike(search_value),
            Content.slug.ilike(search_value),
        ),
    ]

    if content_type:
        filters.append(Content.content_type == content_type)

    if category_id:
        filters.append(Content.category_id == category_id)

    statement = (
        select(Content)
        .where(and_(*filters))
        .order_by(Content.published_at.desc(), Content.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_statement = select(func.count()).select_from(Content).where(and_(*filters))

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total


def get_followed_writer_ids(db: Session, user_id: str) -> list[str]:
    return list(
        db.scalars(
            select(Follow.following_id).where(Follow.follower_id == user_id)
        ).all()
    )


def get_joined_hub_ids(db: Session, user_id: str) -> list[str]:
    return list(
        db.scalars(
            select(HubMember.hub_id).where(HubMember.user_id == user_id)
        ).all()
    )


def list_personalized_feed(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Content], int]:
    followed_writer_ids = get_followed_writer_ids(db, user.id)
    joined_hub_ids = get_joined_hub_ids(db, user.id)

    personalization_filters = []

    if followed_writer_ids:
        personalization_filters.append(Content.author_id.in_(followed_writer_ids))

    if joined_hub_ids:
        personalization_filters.append(Content.hub_id.in_(joined_hub_ids))

    if user.role == UserRole.TEACHER:
        personalization_filters.append(Content.content_type == "EDUCATION")

    if user.role == UserRole.STUDENT:
        personalization_filters.append(Content.content_type == "EDUCATION")

    if user.role == UserRole.PARENT:
        personalization_filters.append(Content.content_type == "CHILDREN")

    base_filters = [Content.status == ContentStatus.PUBLISHED]

    if personalization_filters:
        filters = base_filters + [or_(*personalization_filters)]
    else:
        filters = base_filters

    statement = (
        select(Content)
        .where(and_(*filters))
        .order_by(Content.published_at.desc(), Content.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_statement = select(func.count()).select_from(Content).where(and_(*filters))

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total


def list_category_feed(
    db: Session,
    category_id: str,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Content], int]:
    return list_discovery_feed(
        db=db,
        skip=skip,
        limit=limit,
        category_id=category_id,
    )


def list_hub_feed(
    db: Session,
    hub_id: str,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Content], int]:
    return list_discovery_feed(
        db=db,
        skip=skip,
        limit=limit,
        hub_id=hub_id,
    )