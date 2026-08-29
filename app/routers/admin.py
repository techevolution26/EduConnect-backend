from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import (
    require_admin,
    require_permission,
    require_role_or_permission,
    require_super_admin,
)
from app.core.permissions import Permission
from app.models.content import ContentStatus, ContentType
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminDashboardStats,
    AdminPermissionGrantRequest,
    AdminPermissionListResponse,
    AdminUpdateUserRoleRequest,
    AdminUpdateUserStatusRequest,
    AdminUserListResponse,
    AdminUserRead,
)
from app.schemas.content import ContentListResponse, ContentRead, ContentRejectRequest
from app.services.admin_service import (
    get_admin_dashboard_stats,
    grant_permission,
    list_admin_content,
    list_admin_users,
    list_permissions_for_user,
    revoke_permission,
    update_user_role,
    update_user_status,
)
from app.schemas.gamification import BadgeCreate, BadgeRead
from app.schemas.monetization import ReferralEarningListResponse
from app.services.content_service import (
    approve_content,
    get_content_or_404,
    list_pending_content,
    reject_content,
    toggle_featured_content,
)
from app.services.monetization_service import list_pending_payouts, mark_earning_paid

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------------------------------------------------------------------
# Dashboard -- readable by any admin-tier account regardless of granted
# permissions; it's a summary view, not a mutation.
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=AdminDashboardStats)
def get_dashboard_stats(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminDashboardStats:
    return get_admin_dashboard_stats(db)


# ---------------------------------------------------------------------------
# User management -- requires USERS_VIEW / USERS_MANAGE. Staff-role changes
# (MODERATOR/ADMIN/SUPER_ADMIN) are further restricted to SUPER_ADMIN inside
# services/admin_service.py::update_user_role, even for an admin who holds
# USERS_MANAGE -- that permission only covers ordinary member roles.
# ---------------------------------------------------------------------------

@router.get("/users", response_model=AdminUserListResponse)
def get_admin_users(
    current_user: Annotated[User, Depends(require_permission(Permission.USERS_VIEW))],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    role: UserRole | None = None,
    search: str | None = None,
) -> AdminUserListResponse:
    items, total = list_admin_users(db=db, skip=skip, limit=limit, role=role, search=search)
    return AdminUserListResponse(items=items, total=total, skip=skip, limit=limit)


@router.patch("/users/{user_id}/role", response_model=AdminUserRead)
def update_admin_user_role(
    user_id: str,
    payload: AdminUpdateUserRoleRequest,
    current_user: Annotated[User, Depends(require_permission(Permission.USERS_MANAGE))],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserRead:
    return update_user_role(
        db=db,
        user_id=user_id,
        role=payload.role,
        is_verified=payload.is_verified,
        acting_admin=current_user,
    )


@router.patch("/users/{user_id}/status", response_model=AdminUserRead)
def update_admin_user_status(
    user_id: str,
    payload: AdminUpdateUserStatusRequest,
    current_user: Annotated[User, Depends(require_permission(Permission.USERS_MANAGE))],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserRead:
    return update_user_status(
        db=db,
        user_id=user_id,
        is_active=payload.is_active,
        current_admin=current_user,
    )


# ---------------------------------------------------------------------------
# Scoped admin permission management -- SUPER_ADMIN only. This is the
# control surface for "factor admins down to specific functions": a super
# admin grants exactly the permissions a given admin needs and nothing more.
# ---------------------------------------------------------------------------

@router.get("/users/{user_id}/permissions", response_model=AdminPermissionListResponse)
def get_user_permissions(
    user_id: str,
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminPermissionListResponse:
    perms = list_permissions_for_user(db, user_id)
    return AdminPermissionListResponse(user_id=user_id, permissions=perms)


@router.post("/users/{user_id}/permissions", response_model=AdminPermissionListResponse)
def grant_user_permission(
    user_id: str,
    payload: AdminPermissionGrantRequest,
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminPermissionListResponse:
    grant_permission(db, user_id=user_id, permission=payload.permission, granted_by=current_user)
    perms = list_permissions_for_user(db, user_id)
    return AdminPermissionListResponse(user_id=user_id, permissions=perms)


@router.delete("/users/{user_id}/permissions/{permission}", response_model=AdminPermissionListResponse)
def revoke_user_permission(
    user_id: str,
    permission: Permission,
    current_user: Annotated[User, Depends(require_super_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminPermissionListResponse:
    revoke_permission(db, user_id=user_id, permission=permission)
    perms = list_permissions_for_user(db, user_id)
    return AdminPermissionListResponse(user_id=user_id, permissions=perms)


# ---------------------------------------------------------------------------
# Content administration
# ---------------------------------------------------------------------------

@router.get("/content", response_model=ContentListResponse)
def get_admin_content(
    current_user: Annotated[User, Depends(require_permission(Permission.CONTENT_MODERATE))],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: ContentStatus | None = None,
    content_type: ContentType | None = None,
    search: str | None = None,
) -> ContentListResponse:
    items, total = list_admin_content(
        db=db,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
        content_type=content_type,
        search=search,
    )
    return ContentListResponse(items=items, total=total)


@router.get("/content/pending", response_model=ContentListResponse)
def get_pending_content(
    current_user: Annotated[
        User, Depends(require_role_or_permission(UserRole.MODERATOR, Permission.CONTENT_MODERATE))
    ],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ContentListResponse:
    items, total = list_pending_content(db=db, skip=skip, limit=limit)
    return ContentListResponse(items=items, total=total)


@router.post("/content/{content_id}/approve", response_model=ContentRead)
def approve_pending_content(
    content_id: str,
    current_user: Annotated[
        User, Depends(require_role_or_permission(UserRole.MODERATOR, Permission.CONTENT_MODERATE))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return approve_content(db=db, content_id=content_id, moderator=current_user)


@router.post("/content/{content_id}/reject", response_model=ContentRead)
def reject_pending_content(
    content_id: str,
    payload: ContentRejectRequest,
    current_user: Annotated[
        User, Depends(require_role_or_permission(UserRole.MODERATOR, Permission.CONTENT_MODERATE))
    ],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return reject_content(db=db, content_id=content_id, moderator=current_user, reason=payload.reason)


@router.post("/content/{content_id}/feature", response_model=ContentRead)
def toggle_featured(
    content_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(require_permission(Permission.CONTENT_MANAGE))],
) -> ContentRead:
    content = get_content_or_404(db, content_id)
    return toggle_featured_content(db, content)


# ---------------------------------------------------------------------------
# Referral commission payouts -- part of the monetization layer. See
# services/monetization_service.py for how earnings are credited.
# ---------------------------------------------------------------------------

@router.get("/payouts/pending", response_model=ReferralEarningListResponse)
def get_pending_payouts(
    current_user: Annotated[User, Depends(require_permission(Permission.PAYOUTS_MANAGE))],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> ReferralEarningListResponse:
    items, total = list_pending_payouts(db, skip=skip, limit=limit)
    return ReferralEarningListResponse(items=items, total=total, skip=skip, limit=limit)


@router.post("/payouts/{earning_id}/mark-paid")
def mark_payout_paid(
    earning_id: str,
    current_user: Annotated[User, Depends(require_permission(Permission.PAYOUTS_MANAGE))],
    db: Annotated[Session, Depends(get_db)],
):
    return mark_earning_paid(db, earning_id)


# ---------------------------------------------------------------------------
# Badge definitions -- part of the events/gamification layer.
# ---------------------------------------------------------------------------

@router.post("/badges", response_model=BadgeRead, status_code=status.HTTP_201_CREATED)
def create_badge(
    payload: BadgeCreate,
    current_user: Annotated[User, Depends(require_permission(Permission.BADGES_MANAGE))],
    db: Annotated[Session, Depends(get_db)],
) -> BadgeRead:
    from app.models.gamification import Badge

    badge = Badge(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        icon=payload.icon,
        xp_reward=payload.xp_reward,
        condition=payload.condition,
    )
    db.add(badge)
    db.commit()
    db.refresh(badge)
    return badge
