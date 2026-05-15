from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Comment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "comments"

    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"),
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    content: Mapped["Content"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])


class Like(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "likes"

    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("content_id", "user_id", name="uq_content_like"),
    )


class Bookmark(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bookmarks"

    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("content_id", "user_id", name="uq_content_bookmark"),
    )


class Follow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "follows"

    follower_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    following_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("follower_id", "following_id", name="uq_user_follow"),
    )