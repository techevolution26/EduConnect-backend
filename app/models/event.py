"""
Marketing events: writing competitions, workshops/classes, and book clubs.

DESIGN NOTE: one `events` table with a `type` discriminator, not three
separate tables. The three event types share the same lifecycle (draft ->
published -> ongoing -> completed), the same participation model (RSVP ->
attend -> [submit] -> complete), and the same discovery surface (a single
/events listing filterable by type). Type-specific details (prize
description, book title, workshop session times) live in the `metadata`
JSON column rather than as separate nullable columns per type, since
they're structurally different per type and not the kind of thing you'd
filter/query by column in this codebase's access patterns.

`curriculum_tags` and `metadata` use SQLAlchemy's generic JSON type rather
than PostgreSQL-specific ARRAY/JSONB -- this project runs on MySQL (see
requirements.txt: PyMySQL, and the "MySQL compatibility" comment in the
is_featured migration), and JSON is the portable equivalent SQLAlchemy
translates correctly across both dialects.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class EventType(str, enum.Enum):
    COMPETITION = "COMPETITION"
    WORKSHOP = "WORKSHOP"
    BOOK_CLUB = "BOOK_CLUB"


class EventStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ONGOING = "ONGOING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ParticipationStatus(str, enum.Enum):
    RSVP = "RSVP"
    ATTENDED = "ATTENDED"
    SUBMITTED = "SUBMITTED"      # competitions: work submitted for judging
    COMPLETED = "COMPLETED"      # book clubs / workshops: finished the event
    WITHDREW = "WITHDREW"


class Event(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "events"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    type: Mapped[EventType] = mapped_column(Enum(EventType), nullable=False, index=True)
    status: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus), default=EventStatus.DRAFT, nullable=False, index=True
    )

    host_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Student targeting (ADR-4 "student-specific targeting" pillars).
    # Stored as JSON list of free-text tags (e.g. ["CBC", "KCSE", "Grade 8"])
    # rather than a normalized tag table -- curriculum taxonomies vary
    # enough across CBC/KCSE/8-4-4 that a flexible tag list is a better fit
    # than a rigid FK relationship for a first version.
    curriculum_tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    student_only: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    school_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("schools.id", ondelete="SET NULL"), nullable=True
    )

    # Monetization lever: if true, RSVPing requires an active partnership --
    # mirrors content_requires_partnership() in content_service.py. Lets a
    # host offer a "premium workshop" that only paying partners can join.
    requires_partnership: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    starts_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    max_participants: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Type-specific details: competitions -> {"prize": "..."},
    # book clubs -> {"book_title": "...", "author": "..."},
    # workshops -> {"sessions": [{"title": "...", "starts_at": "..."}]}
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    host = relationship("User", foreign_keys=[host_id])
    school = relationship("School", foreign_keys=[school_id])
    participants: Mapped[List["EventParticipant"]] = relationship(
        "EventParticipant", back_populates="event", cascade="all, delete-orphan"
    )


class EventParticipant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "event_participants"
    __table_args__ = (
        UniqueConstraint("event_id", "user_id", name="uq_event_participant_event_user"),
    )

    event_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("events.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[ParticipationStatus] = mapped_column(
        Enum(ParticipationStatus), default=ParticipationStatus.RSVP, nullable=False, index=True
    )
    xp_awarded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Competition submission payload, e.g. {"content_id": "...", "note": "..."}
    submission: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    event = relationship("Event", back_populates="participants")
    user = relationship("User", foreign_keys=[user_id])
