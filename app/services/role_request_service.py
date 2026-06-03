from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.notification import NotificationType
from app.models.role_request import RoleRequestStatus, RoleUpgradeRequest
from app.models.user import User, UserRole
from app.services.notification_service import create_notification


REQUESTABLE_ROLES = {
    UserRole.WRITER,
    UserRole.TEACHER,
    UserRole.STUDENT,
    UserRole.PARENT,
}


def create_role_upgrade_request(
    db: Session,
    user: User,
    requested_role: UserRole,
    reason: str,
) -> RoleUpgradeRequest:
    if requested_role not in REQUESTABLE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This role cannot be requested through this form.",
        )

    if user.role == requested_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have this role.",
        )

    existing_pending = db.scalars(
        select(RoleUpgradeRequest).where(
            RoleUpgradeRequest.user_id == user.id,
            RoleUpgradeRequest.status == RoleRequestStatus.PENDING,
        )
    ).first()

    if existing_pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a pending role request.",
        )

    request = RoleUpgradeRequest(
        user_id=user.id,
        requested_role=requested_role.value,
        reason=reason,
        status=RoleRequestStatus.PENDING,
    )

    db.add(request)
    db.commit()
    db.refresh(request)

    return request


def list_my_role_requests(db: Session, user: User) -> list[RoleUpgradeRequest]:
    return list(
        db.scalars(
            select(RoleUpgradeRequest)
            .where(RoleUpgradeRequest.user_id == user.id)
            .order_by(RoleUpgradeRequest.created_at.desc())
        ).all()
    )


def list_admin_role_requests(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    status_filter: RoleRequestStatus | None = None,
) -> tuple[list[RoleUpgradeRequest], int]:
    statement = (
        select(RoleUpgradeRequest)
        .options(joinedload(RoleUpgradeRequest.user))
        .order_by(RoleUpgradeRequest.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    count_statement = select(func.count()).select_from(RoleUpgradeRequest)

    if status_filter:
        statement = statement.where(RoleUpgradeRequest.status == status_filter)
        count_statement = count_statement.where(
            RoleUpgradeRequest.status == status_filter
        )

    items = list(db.scalars(statement).all())
    total = db.scalar(count_statement) or 0

    return items, total


def get_role_request_or_404(db: Session, request_id: str) -> RoleUpgradeRequest:
    request = db.scalars(
        select(RoleUpgradeRequest)
        .options(joinedload(RoleUpgradeRequest.user))
        .where(RoleUpgradeRequest.id == request_id)
    ).first()

    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role upgrade request was not found.",
        )

    return request


def approve_role_request(
    db: Session,
    request_id: str,
    admin: User,
    admin_note: str | None = None,
) -> RoleUpgradeRequest:
    request = get_role_request_or_404(db, request_id)

    if request.status != RoleRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be approved.",
        )

    user = db.get(User, request.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Request owner was not found.",
        )

    user.role = UserRole(request.requested_role)
    user.is_verified = True

    request.status = RoleRequestStatus.APPROVED
    request.admin_note = admin_note
    request.reviewed_by_id = admin.id

    db.add(user)
    db.add(request)

    create_notification(
        db=db,
        user_id=user.id,
        notification_type=NotificationType.SYSTEM,
        title="Role request approved",
        body=f"Your request to become {request.requested_role} was approved.",
    )

    db.commit()
    db.refresh(request)

    return request


def reject_role_request(
    db: Session,
    request_id: str,
    admin: User,
    admin_note: str | None = None,
) -> RoleUpgradeRequest:
    request = get_role_request_or_404(db, request_id)

    if request.status != RoleRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending requests can be rejected.",
        )

    request.status = RoleRequestStatus.REJECTED
    request.admin_note = admin_note
    request.reviewed_by_id = admin.id

    db.add(request)

    create_notification(
        db=db,
        user_id=request.user_id,
        notification_type=NotificationType.SYSTEM,
        title="Role request rejected",
        body=admin_note or f"Your request to become {request.requested_role} was rejected.",
    )

    db.commit()
    db.refresh(request)

    return request