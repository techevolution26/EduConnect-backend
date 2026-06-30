from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.partnership_payment import PartnershipPayment


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

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    plan: Mapped[PartnershipPlan] = mapped_column(
        Enum(PartnershipPlan),
        nullable=False,
        index=True,
    )
    status: Mapped[PartnershipStatus] = mapped_column(
        Enum(PartnershipStatus),
        default=PartnershipStatus.PENDING,
        nullable=False,
        index=True,
    )

    referral_creator_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    provider_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="partnerships",
    )
    referral_creator = relationship(
        "User",
        foreign_keys=[referral_creator_id],
        back_populates="referral_partnerships",
    )

    payments: Mapped[list["PartnershipPayment"]] = relationship(
    "PartnershipPayment",
    back_populates="partnership",
    cascade="all, delete-orphan",
)