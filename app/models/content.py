import enum
from datetime import datetime
from typing import List, Optional
from xml.etree.ElementTree import Comment

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.category import Category
from app.models.hub import Hub
from app.models.user import User
from app.models.user import User


class ContentType(str, enum.Enum):
    ARTICLE = "ARTICLE"
    STORY = "STORY"
    POEM = "POEM"
    FAITH = "FAITH"
    EDUCATION = "EDUCATION"
    CHILDREN = "CHILDREN"
    NEWS = "NEWS"
    AUDIO = "AUDIO"


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

    author_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category_id: Mapped[Optional[str]] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"))
    hub_id: Mapped[Optional[str]] = mapped_column(ForeignKey("hubs.id", ondelete="SET NULL"))

    title: Mapped[str] = mapped_column(String(220), nullable=False)
    slug: Mapped[str] = mapped_column(String(260), unique=True, index=True, nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500))

    content_type: Mapped[ContentType] = mapped_column(Enum(ContentType), nullable=False)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus),
        default=ContentStatus.DRAFT,
        nullable=False,
    )
    visibility: Mapped[ContentVisibility] = mapped_column(
        Enum(ContentVisibility),
        default=ContentVisibility.PUBLIC,
        nullable=False,
    )

    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reading_time_minutes: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    author: Mapped["User"] = relationship(back_populates="contents")
    category: Mapped[Optional["Category"]] = relationship(back_populates="contents")
    hub: Mapped[Optional["Hub"]] = relationship(back_populates="contents")

    comments: Mapped[List["Comment"]] = relationship(
        back_populates="content",
        cascade="all, delete-orphan",
    )