from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContentReadSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_read_sessions"

    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_active_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    active_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_scroll_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    tab_visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_qualified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    content = relationship("Content", back_populates="read_sessions")
    user = relationship("User", back_populates="read_sessions")