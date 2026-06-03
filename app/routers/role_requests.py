from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.models.role_request import RoleRequestStatus
from app.models.user import User
from app.schemas.role_request import (
    RoleUpgradeRequestCreate,
    RoleUpgradeRequestDetailRead,
    RoleUpgradeRequestListResponse,
    RoleUpgradeRequestRead,
    RoleUpgradeRequestReview,
)
from app.services.role_request_service import (
    approve_role_request,
    create_role_upgrade_request,
    list_admin_role_requests,
    list_my_role_requests,
    reject_role_request,
)

router = APIRouter(prefix="/role-requests", tags=["Role Requests"])


@router.post("", response_model=RoleUpgradeRequestRead)
def create_my_role_request(
    payload: RoleUpgradeRequestCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RoleUpgradeRequestRead:
    return create_role_upgrade_request(
        db=db,
        user=current_user,
        requested_role=payload.requested_role,
        reason=payload.reason,
    )


@router.get("/me", response_model=list[RoleUpgradeRequestRead])
def get_my_role_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[RoleUpgradeRequestRead]:
    return list_my_role_requests(db=db, user=current_user)


@router.get("/admin", response_model=RoleUpgradeRequestListResponse)
def get_admin_role_requests(
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: RoleRequestStatus | None = None,
) -> RoleUpgradeRequestListResponse:
    items, total = list_admin_role_requests(
        db=db,
        skip=skip,
        limit=limit,
        status_filter=status_filter,
    )

    return RoleUpgradeRequestListResponse(items=items, total=total)


@router.post("/admin/{request_id}/approve", response_model=RoleUpgradeRequestDetailRead)
def approve_admin_role_request(
    request_id: str,
    payload: RoleUpgradeRequestReview,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> RoleUpgradeRequestDetailRead:
    return approve_role_request(
        db=db,
        request_id=request_id,
        admin=current_user,
        admin_note=payload.admin_note,
    )


@router.post("/admin/{request_id}/reject", response_model=RoleUpgradeRequestDetailRead)
def reject_admin_role_request(
    request_id: str,
    payload: RoleUpgradeRequestReview,
    current_user: Annotated[User, Depends(require_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> RoleUpgradeRequestDetailRead:
    return reject_role_request(
        db=db,
        request_id=request_id,
        admin=current_user,
        admin_note=payload.admin_note,
    )