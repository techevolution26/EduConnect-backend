from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.user import User


def create_notification(
    db: Session,
    user_id: str,
    notification_type: NotificationType,
    title: str,
    body: str | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
    )

    db.add(notification)
    return notification


def list_my_notifications(
    db: Session,
    user: User,
    skip: int = 0,
    limit: int = 30,
) -> tuple[list[Notification], int, int]:
    statement = (
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )

    total_statement = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id)
    )

    unread_statement = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.is_read == False,
        )
    )

    items = list(db.scalars(statement).all())
    total = db.scalar(total_statement) or 0
    unread_count = db.scalar(unread_statement) or 0

    return items, total, unread_count


def mark_notification_read(
    db: Session,
    notification_id: str,
    user: User,
) -> Notification | None:
    notification = db.scalars(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
        )
    ).first()

    if not notification:
        return None

    notification.is_read = True

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


def mark_all_notifications_read(db: Session, user: User) -> int:
    notifications = list(
        db.scalars(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.is_read == False,
            )
        ).all()
    )

    for notification in notifications:
        notification.is_read = True
        db.add(notification)

    db.commit()

    return len(notifications)