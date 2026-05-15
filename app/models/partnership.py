import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PartnershipPlan(str, enum.Enum):
    FREE = "FREE"
    MONTHLY_PARTNER = "MONTHLY_PARTNER"
    ANNUAL_PARTNER = "ANNUAL_PARTNER"
    STUDENT_PARTNER = "STUDENT_PARTNER"
    TEACHER_PARTNER = "TEACHER_PARTNER"


class PartnershipStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"
    PENDING = "PENDING"


class Partnership(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partnerships"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    plan: Mapped[PartnershipPlan] = mapped_column(Enum(PartnershipPlan), nullable=False)
    status: Mapped[PartnershipStatus] = mapped_column(
        Enum(PartnershipStatus),
        default=PartnershipStatus.PENDING,
        nullable=False,
    )

    referral_creator_id: Mapped[Optional[str]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    provider: Mapped[Optional[str]] = mapped_column(String(80))
    provider_reference: Mapped[Optional[str]] = mapped_column(String(255))

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))