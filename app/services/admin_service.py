from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.content import Content, ContentStatus
from app.models.hub import Hub
from app.models.partnership import Partnership, PartnershipStatus
from app.models.user import User, UserRole
from app.models.content import ContentType


def count_users_by_role(db: Session, role: UserRole) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == role)
        )
        or 0
    )


def get_admin_dashboard_stats(db: Session) -> dict:
    total_users = db.scalar(select(func.count()).select_from(User)) or 0

    total_content = db.scalar(select(func.count()).select_from(Content)) or 0

    pending_content = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(Content.status == ContentStatus.PENDING_REVIEW)
        )
        or 0
    )

    published_content = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(Content.status == ContentStatus.PUBLISHED)
        )
        or 0
    )

    rejected_content = (
        db.scalar(
            select(func.count())
            .select_from(Content)
            .where(Content.status == ContentStatus.REJECTED)
        )
        or 0
    )

    total_categories = db.scalar(select(func.count()).select_from(Category)) or 0
    total_hubs = db.scalar(select(func.count()).select_from(Hub)) or 0

    total_partnerships = (
        db.scalar(select(func.count()).select_from(Partnership))
        or 0
    )

    active_partnerships = (
        db.scalar(
            select(func.count())
            .select_from(Partnership)
            .where(Partnership.status == PartnershipStatus.ACTIVE)
        )
        or 0
    )

    return {
        "total_users": total_users,
        "total_readers": count_users_by_role(db, UserRole.READER),
        "total_writers": count_users_by_role(db, UserRole.WRITER),
        "total_teachers": count_users_by_role(db, UserRole.TEACHER),
        "total_students": count_users_by_role(db, UserRole.STUDENT),
        "total_parents": count_users_by_role(db, UserRole.PARENT),
        "total_moderators": count_users_by_role(db, UserRole.MODERATOR),
        "total_admins": count_users_by_role(db, UserRole.ADMIN),
        "total_content": total_content,
        "pending_content": pending_content,
        "published_content": published_content,
        "rejected_content": rejected_content,
        "total_categories": total_categories,
        "total_hubs": total_hubs,
        "total_partnerships": total_partnerships,
        "active_partnerships": active_partnerships,
    }


def list_admin_users(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    role: UserRole | None = None,
    search: str | None = None,
) -> tuple[list[User], int]:
    filters = []

    if role:
        filters.append(User.role == role)

    if search:
        search_value = f"%{search.strip()}%"
        filters.append(
            (User.email.ilike(search_value))
            | (User.full_name.ilike(search_value))
            | (User.username.ilike(search_value))
        )

    statement = select(User)
    count_statement = select(func.count()).select_from(User)

    for item in filters:
        statement = statement.where(item)
        count_statement = count_statement.where(item)

    statement = (
        statement.order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    users = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return users, total


def get_admin_user_or_404(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User was not found.",
        )

    return user


def update_user_role(
    db: Session,
    user_id: str,
    role: UserRole,
    is_verified: bool | None = None,
) -> User:
    user = get_admin_user_or_404(db, user_id)

    user.role = role

    if is_verified is not None:
        user.is_verified = is_verified

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def update_user_status(
    db: Session,
    user_id: str,
    is_active: bool,
    current_admin: User,
) -> User:
    user = get_admin_user_or_404(db, user_id)

    if user.id == current_admin.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own admin account.",
        )

    user.is_active = is_active

    db.add(user)
    db.commit()
    db.refresh(user)

    return user

def list_admin_content(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status_filter: ContentStatus | None = None,
    content_type: ContentType | None = None,
    search: str | None = None,
) -> tuple[list[Content], int]:
    filters = []

    if status_filter:
        filters.append(Content.status == status_filter)

    if content_type:
        filters.append(Content.content_type == content_type)

    if search:
        search_value = f"%{search.strip()}%"
        filters.append(
            (Content.title.ilike(search_value))
            | (Content.slug.ilike(search_value))
            | (Content.excerpt.ilike(search_value))
            | (Content.body.ilike(search_value))
        )

    statement = select(Content)
    count_statement = select(func.count()).select_from(Content)

    for item in filters:
        statement = statement.where(item)
        count_statement = count_statement.where(item)

    statement = (
        statement.order_by(Content.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total