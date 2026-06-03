from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.category import Category
from app.models.content import Content, ContentStatus
from app.models.education import ChildrenContent, EducationResource
from app.models.engagement import Follow
from app.models.hub import Hub, HubMember
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
        .order_by(
            Content.is_featured.desc(),
            Content.featured_at.desc(),
            Content.published_at.desc(),
            Content.created_at.desc(),
        )
        .offset(skip)
        .limit(limit)
    )

    count_statement = (
        select(func.count())
        .select_from(Content)
        .where(and_(*filters))
    )

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


def global_search(
    db: Session,
    query: str,
    limit: int = 10,
) -> dict:
    search_value = f"%{query.strip()}%"

    content_items = list(
        db.scalars(
            select(Content)
            .where(
                Content.status == ContentStatus.PUBLISHED,
                or_(
                    Content.title.ilike(search_value),
                    Content.slug.ilike(search_value),
                    Content.excerpt.ilike(search_value),
                    Content.body.ilike(search_value),
                ),
            )
            .order_by(Content.published_at.desc(), Content.created_at.desc())
            .limit(limit)
        ).all()
    )

    writers = list(
        db.scalars(
            select(User)
            .where(
                User.is_active == True,
                User.role.in_(
                    [
                        UserRole.WRITER,
                        UserRole.TEACHER,
                        UserRole.MODERATOR,
                        UserRole.ADMIN,
                    ]
                ),
                or_(
                    User.full_name.ilike(search_value),
                    User.username.ilike(search_value),
                    User.bio.ilike(search_value),
                ),
            )
            .order_by(User.created_at.desc())
            .limit(limit)
        ).all()
    )

    hubs = list(
        db.scalars(
            select(Hub)
            .where(
                Hub.is_active == True,
                or_(
                    Hub.name.ilike(search_value),
                    Hub.slug.ilike(search_value),
                    Hub.description.ilike(search_value),
                ),
            )
            .order_by(Hub.name.asc())
            .limit(limit)
        ).all()
    )

    categories = list(
        db.scalars(
            select(Category)
            .where(
                Category.is_active == True,
                or_(
                    Category.name.ilike(search_value),
                    Category.slug.ilike(search_value),
                    Category.description.ilike(search_value),
                ),
            )
            .order_by(Category.name.asc())
            .limit(limit)
        ).all()
    )

    education_resources = list(
        db.scalars(
            select(EducationResource)
            .options(joinedload(EducationResource.content))
            .join(Content, Content.id == EducationResource.content_id)
            .where(
                Content.status == ContentStatus.PUBLISHED,
                or_(
                    Content.title.ilike(search_value),
                    Content.excerpt.ilike(search_value),
                    Content.body.ilike(search_value),
                    EducationResource.curriculum.ilike(search_value),
                    EducationResource.grade_level.ilike(search_value),
                    EducationResource.subject.ilike(search_value),
                    EducationResource.resource_type.ilike(search_value),
                ),
            )
            .limit(limit)
        ).unique().all()
    )

    children_content = list(
        db.scalars(
            select(ChildrenContent)
            .options(joinedload(ChildrenContent.content))
            .join(Content, Content.id == ChildrenContent.content_id)
            .where(
                Content.status == ContentStatus.PUBLISHED,
                or_(
                    Content.title.ilike(search_value),
                    Content.excerpt.ilike(search_value),
                    Content.body.ilike(search_value),
                    ChildrenContent.age_group.ilike(search_value),
                ),
            )
            .limit(limit)
        ).unique().all()
    )

    return {
        "query": query,
        "content": content_items,
        "writers": writers,
        "hubs": hubs,
        "categories": categories,
        "education_resources": education_resources,
        "children_content": children_content,
    }