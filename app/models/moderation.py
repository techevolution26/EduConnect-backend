import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReportStatus(str, enum.Enum):
    OPEN = "OPEN"
    REVIEWING = "REVIEWING"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class ModerationAction(str, enum.Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    HIDDEN = "HIDDEN"
    RESTORED = "RESTORED"
    FLAGGED = "FLAGGED"


class Report(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reports"

    reporter_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[Optional[str]] = mapped_column(ForeignKey("contents.id", ondelete="CASCADE"))

    reason: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        default=ReportStatus.OPEN,
        nullable=False,
    )


class ModerationLog(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "moderation_logs"

    moderator_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content_id: Mapped[Optional[str]] = mapped_column(ForeignKey("contents.id", ondelete="SET NULL"))

    action: Mapped[ModerationAction] = mapped_column(Enum(ModerationAction), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text)