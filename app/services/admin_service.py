from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import STAFF_ROLES, Permission
from app.models.category import Category
from app.models.content import Content, ContentStatus
from app.models.hub import Hub
from app.models.partnership import Partnership, PartnershipStatus
from app.models.permission import AdminPermission
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
        "total_super_admins": count_users_by_role(db, UserRole.SUPER_ADMIN),
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
    *,
    acting_admin: User,
) -> User:
    """
    Update a user's role.

    HARDENED: previously any ADMIN could set ANY user's role to ANY value,
    including ADMIN or SUPER_ADMIN -- a direct privilege-escalation path
    (a single compromised or malicious admin account could mint new
    super admins, including itself via a second account). Now:

      - Only a SUPER_ADMIN may assign or remove a STAFF_ROLE
        (MODERATOR / ADMIN / SUPER_ADMIN).
      - Only a SUPER_ADMIN may change the role of an existing staff
        member (moderator, admin, or another super admin) at all --
        a scoped admin cannot touch staff accounts even to change them
        to a non-staff role.
      - A plain ADMIN (acting via a granted USERS_MANAGE permission,
        checked at the router layer) may only move a user between the
        ordinary member roles: READER, WRITER, TEACHER, STUDENT, PARENT.
    """
    user = get_admin_user_or_404(db, user_id)

    target_is_staff_now = user.role in STAFF_ROLES
    target_would_be_staff = role in STAFF_ROLES

    if acting_admin.role != UserRole.SUPER_ADMIN:
        if target_is_staff_now or target_would_be_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Only a super admin can assign or modify staff roles "
                    "(moderator, admin, super admin)."
                ),
            )

    # Safety net: never allow the last remaining super admin to be demoted,
    # even by another super admin acting on themselves or by mistake --
    # this would lock the platform out of its top administrative tier.
    if user.role == UserRole.SUPER_ADMIN and role != UserRole.SUPER_ADMIN:
        remaining_super_admins = count_users_by_role(db, UserRole.SUPER_ADMIN)
        if remaining_super_admins <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the last remaining super admin account.",
            )

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

    # HARDENED: a scoped ADMIN could previously deactivate another admin or
    # even the super admin, which is a lockout / sabotage vector. Only a
    # super admin may deactivate a staff account (moderator/admin/super
    # admin). Non-staff accounts can still be deactivated by any admin
    # holding USERS_MANAGE (checked at the router layer).
    if user.role in STAFF_ROLES and current_admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a super admin can change another staff member's account status.",
        )

    if (
        user.role == UserRole.SUPER_ADMIN
        and not is_active
        and count_users_by_role(db, UserRole.SUPER_ADMIN) <= 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate the last remaining super admin account.",
        )

    user.is_active = is_active

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# ---------------------------------------------------------------------------
# Scoped admin permission management (super admin only -- see routers/admin.py)
# ---------------------------------------------------------------------------

def list_permissions_for_user(db: Session, user_id: str) -> list[str]:
    return list(
        db.scalars(
            select(AdminPermission.permission).where(AdminPermission.user_id == user_id)
        ).all()
    )


def grant_permission(
    db: Session,
    user_id: str,
    permission: Permission,
    granted_by: User,
) -> AdminPermission:
    target = get_admin_user_or_404(db, user_id)

    if target.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scoped permissions can only be granted to ADMIN-role accounts. "
            "SUPER_ADMIN already has every permission implicitly.",
        )

    existing = db.scalars(
        select(AdminPermission).where(
            AdminPermission.user_id == user_id,
            AdminPermission.permission == permission.value,
        )
    ).first()

    if existing:
        return existing

    grant = AdminPermission(
        user_id=user_id,
        permission=permission.value,
        granted_by_id=granted_by.id,
    )
    db.add(grant)
    db.commit()
    db.refresh(grant)
    return grant


def revoke_permission(db: Session, user_id: str, permission: Permission) -> None:
    existing = db.scalars(
        select(AdminPermission).where(
            AdminPermission.user_id == user_id,
            AdminPermission.permission == permission.value,
        )
    ).first()

    if existing:
        db.delete(existing)
        db.commit()


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