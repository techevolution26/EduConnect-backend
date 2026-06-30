from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PaymentProvider(str, enum.Enum):
    MPESA = "MPESA"


class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


class PartnershipPayment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "partnership_payments"

    partnership_id: Mapped[str] = mapped_column(
        ForeignKey("partnerships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    provider: Mapped[PaymentProvider] = mapped_column(
        Enum(PaymentProvider),
        default=PaymentProvider.MPESA,
        nullable=False,
    )

    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus),
        default=PaymentStatus.INITIATED,
        nullable=False,
        index=True,
    )

    plan: Mapped[str] = mapped_column(String(40), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="KES", nullable=False)

    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)

    merchant_request_id: Mapped[Optional[str]] = mapped_column(String(120))
    checkout_request_id: Mapped[Optional[str]] = mapped_column(String(120), index=True)
    mpesa_receipt_number: Mapped[Optional[str]] = mapped_column(String(120))

    result_code: Mapped[Optional[str]] = mapped_column(String(20))
    result_desc: Mapped[Optional[str]] = mapped_column(Text)

    raw_request: Mapped[Optional[dict]] = mapped_column(JSON)
    raw_callback: Mapped[Optional[dict]] = mapped_column(JSON)

    requested_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    paid_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))
    failed_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True))

    partnership = relationship("Partnership", back_populates="payments")