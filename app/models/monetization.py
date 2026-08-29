"""
Monetization models.

ReferralEarning turns `Partnership.referral_creator_id` -- a field that
already existed in the original schema but had NOTHING reading or writing
to it beyond storing the referrer's ID -- into an actual revenue-share
mechanism: when a referred user's payment succeeds, the referring creator
is credited a commission, visible to them and payable by an admin holding
PAYOUTS_MANAGE.

This directly serves the "monetize the idea" goal: it gives writers/
teachers/students a concrete incentive to share partnership links, since
they now earn from conversions they drive.
"""
from __future__ import annotations

import enum

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ReferralEarningStatus(str, enum.Enum):
    PENDING = "PENDING"    # earned, not yet paid out
    PAID = "PAID"          # paid out to the creator
    VOID = "VOID"          # reversed (e.g. underlying payment was refunded)


class ReferralEarning(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "referral_earnings"

    referrer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    partnership_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("partnerships.id", ondelete="CASCADE"), nullable=False
    )
    partnership_payment_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("partnership_payments.id", ondelete="CASCADE"), nullable=False
    )

    # Snapshot the amount and rate at time of crediting -- if the commission
    # rate changes later, historical earnings shouldn't silently recompute.
    source_amount_kes: Mapped[int] = mapped_column(Integer, nullable=False)
    commission_rate_bps: Mapped[int] = mapped_column(Integer, nullable=False)  # basis points, e.g. 1000 = 10%
    commission_amount_kes: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[ReferralEarningStatus] = mapped_column(
        Enum(ReferralEarningStatus),
        default=ReferralEarningStatus.PENDING,
        nullable=False,
        index=True,
    )

    referrer = relationship("User", foreign_keys=[referrer_id])
