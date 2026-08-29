"""
Gamification: XP ledger and badges.

DESIGN NOTE: xp_ledger is APPEND-ONLY -- rows are never updated or
deleted, only inserted. This gives a full audit trail ("why does this
student have 420 XP?"), makes it possible to correct a bad grant with a
negative-amount reversal row instead of mutating history, and lets
leaderboards be computed for any time window (all-time, this month, this
event) by filtering on `earned_at` rather than needing separate running
counters that can drift out of sync with reality.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class XPLedgerEntry(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "xp_ledger"

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # Polymorphic source reference, e.g. source_type="event_participation",
    # source_id=<event_participants.id>. Kept as a plain string rather than
    # a proper polymorphic FK since sources span several unrelated tables.
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    note: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    user = relationship("User", foreign_keys=[user_id])


class Badge(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "badges"

    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)  # lucide icon name
    xp_reward: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Condition definition evaluated by services/gamification_service.py,
    # e.g. {"type": "events_attended", "threshold": 5}. A small, explicit
    # set of condition types is checked in code rather than a generic rule
    # engine -- keeps this auditable and easy to extend deliberately.
    condition: Mapped[dict] = mapped_column("condition_json", JSON, default=dict, nullable=False)


class UserBadge(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "user_badges"
    __table_args__ = (
        UniqueConstraint("user_id", "badge_id", name="uq_user_badge_user_badge"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    badge_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("badges.id", ondelete="CASCADE"), nullable=False, index=True
    )
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user = relationship("User", foreign_keys=[user_id])
    badge = relationship("Badge", foreign_keys=[badge_id])
