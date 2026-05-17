from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin, require_moderator_or_admin
from app.models.user import User, UserRole
from app.schemas.admin import (
    AdminDashboardStats,
    AdminUpdateUserRoleRequest,
    AdminUpdateUserStatusRequest,
    AdminUserListResponse,
    AdminUserRead,
)
from app.schemas.content import ContentListResponse, ContentRead, ContentRejectRequest
from app.services.admin_service import (
    get_admin_dashboard_stats,
    list_admin_users,
    update_user_role,
    update_user_status,
)

from app.services.content_service import (
    approve_content,
    list_pending_content,
    reject_content,
)

from app.services.admin_service import (
    get_admin_dashboard_stats,
    list_admin_content,
    list_admin_users,
    update_user_role,
    update_user_status,
)

from app.models.content import ContentStatus, ContentType

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=AdminDashboardStats)
def get_dashboard_stats(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminDashboardStats:
    return get_admin_dashboard_stats(db)


@router.get("/users", response_model=AdminUserListResponse)
def get_admin_users(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    role: UserRole | None = None,
    search: str | None = None,
) -> AdminUserListResponse:
    items, total = list_admin_users(
        db=db,
        skip=skip,
        limit=limit,
        role=role,
        search=search,
    )

    return AdminUserListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserRead)
def update_admin_user_role(
    user_id: str,
    payload: AdminUpdateUserRoleRequest,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserRead:
    return update_user_role(
        db=db,
        user_id=user_id,
        role=payload.role,
        is_verified=payload.is_verified,
    )


@router.patch("/users/{user_id}/status", response_model=AdminUserRead)
def update_admin_user_status(
    user_id: str,
    payload: AdminUpdateUserStatusRequest,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUserRead:
    return update_user_status(
        db=db,
        user_id=user_id,
        is_active=payload.is_active,
        current_admin=current_user,
    )


@router.get("/content", response_model=ContentListResponse)
def get_admin_content(
    current_user: Annotated[User, Depends(require_admin)],
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
    current_user: Annotated[User, Depends(require_moderator_or_admin)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> ContentListResponse:
    items, total = list_pending_content(db=db, skip=skip, limit=limit)

    return ContentListResponse(items=items, total=total)


@router.post("/content/{content_id}/approve", response_model=ContentRead)
def approve_pending_content(
    content_id: str,
    current_user: Annotated[User, Depends(require_moderator_or_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return approve_content(
        db=db,
        content_id=content_id,
        moderator=current_user,
    )


@router.post("/content/{content_id}/reject", response_model=ContentRead)
def reject_pending_content(
    content_id: str,
    payload: ContentRejectRequest,
    current_user: Annotated[User, Depends(require_moderator_or_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> ContentRead:
    return reject_content(
        db=db,
        content_id=content_id,
        moderator=current_user,
        reason=payload.reason,
    )