import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RoleRequestStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class RoleUpgradeRequest(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "role_upgrade_requests"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    requested_role: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[RoleRequestStatus] = mapped_column(
        Enum(RoleRequestStatus),
        default=RoleRequestStatus.PENDING,
        server_default=RoleRequestStatus.PENDING.value,
        nullable=False,
    )

    admin_note: Mapped[Optional[str]] = mapped_column(Text)
    reviewed_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
    )

    user = relationship("User", foreign_keys=[user_id])
    reviewed_by = relationship("User", foreign_keys=[reviewed_by_id])