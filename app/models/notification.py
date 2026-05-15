import enum
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class NotificationType(str, enum.Enum):
    CONTENT_APPROVED = "CONTENT_APPROVED"
    CONTENT_REJECTED = "CONTENT_REJECTED"
    NEW_FOLLOWER = "NEW_FOLLOWER"
    COMMENT = "COMMENT"
    PARTNERSHIP = "PARTNERSHIP"
    SYSTEM = "SYSTEM"


class Notification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "notifications"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    notification_type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    body: Mapped[Optional[str]] = mapped_column(Text)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)