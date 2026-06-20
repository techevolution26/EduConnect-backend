from __future__ import annotations

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.category import Category
from app.models.hub import Hub
from app.models.read_session import ContentReadSession
from app.models.user import User
from app.models.content_asset import ContentAsset


class ContentType(str, enum.Enum):
    ARTICLE = "ARTICLE"
    STORY = "STORY"
    FICTION = "FICTION"
    POEM = "POEM"
    FAITH = "FAITH"
    EDUCATION = "EDUCATION"
    CHILDREN = "CHILDREN"
    NEWS = "NEWS"
    AUDIO = "AUDIO"
    WRITING_TIPS = "WRITING_TIPS"
    SELF_IMPROVEMENT = "SELF_IMPROVEMENT"
    RELATIONSHIP = "RELATIONSHIP"
    MONEY_FINANCE = "MONEY_FINANCE"
    MEDICINE = "MEDICINE"
    PSYCHOLOGY = "PSYCHOLOGY"
    MENTAL_HEALTH = "MENTAL_HEALTH"
    HUMOR = "HUMOR"
    WOMEN = "WOMEN"
    FITNESS = "FITNESS"
    SELF_AWARENESS = "SELF_AWARENESS"
    PARENTING = "PARENTING"
    TECHNOLOGY = "TECHNOLOGY"


class ContentStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    PUBLISHED = "PUBLISHED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"


class ContentVisibility(str, enum.Enum):
    PUBLIC = "PUBLIC"
    PARTNERS_ONLY = "PARTNERS_ONLY"
    PRIVATE = "PRIVATE"


class Content(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "contents"

    author_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    hub_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("hubs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(220), nullable=False)
    slug: Mapped[str] = mapped_column(String(260), unique=True, index=True, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    content_type: Mapped[ContentType] = mapped_column(
        Enum(ContentType),
        nullable=False,
        index=True,
    )
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus),
        default=ContentStatus.DRAFT,
        nullable=False,
        index=True,
    )
    visibility: Mapped[ContentVisibility] = mapped_column(
        Enum(ContentVisibility),
        default=ContentVisibility.PUBLIC,
        nullable=False,
        index=True,
    )

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    reading_time_minutes: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    views_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
        index=True,
    )

    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        index=True,
    )
    featured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    author: Mapped["User"] = relationship(back_populates="contents")
    category: Mapped[Optional["Category"]] = relationship(back_populates="contents")
    hub: Mapped[Optional["Hub"]] = relationship(back_populates="contents")

    assets: Mapped[List["ContentAsset"]] = relationship(
        "ContentAsset",
        back_populates="content",
        cascade="all, delete-orphan",
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="content",
        cascade="all, delete-orphan",
    )
    
    read_sessions: Mapped[List["ContentReadSession"]] = relationship(
    "ContentReadSession",
    back_populates="content",
    cascade="all, delete-orphan",
)