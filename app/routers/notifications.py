from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import MessageResponse
from app.schemas.notification import NotificationListResponse, NotificationRead
from app.services.notification_service import (
    list_my_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def get_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=30, ge=1, le=100),
) -> NotificationListResponse:
    items, total, unread_count = list_my_notifications(
        db=db,
        user=current_user,
        skip=skip,
        limit=limit,
    )

    return NotificationListResponse(
        items=items,
        total=total,
        unread_count=unread_count,
    )


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def read_notification(
    notification_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> NotificationRead:
    notification = mark_notification_read(
        db=db,
        notification_id=notification_id,
        user=current_user,
    )

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification was not found.",
        )

    return notification


@router.patch("/read-all", response_model=MessageResponse)
def read_all_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    count = mark_all_notifications_read(db=db, user=current_user)

    return MessageResponse(
        message=f"Marked {count} notification(s) as read.",
    )