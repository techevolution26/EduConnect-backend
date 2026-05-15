from __future__ import annotations
import enum
from typing import List, Optional

from sqlalchemy import Boolean, Enum, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserRole(str, enum.Enum):
    READER = "READER"
    WRITER = "WRITER"
    TEACHER = "TEACHER"
    STUDENT = "STUDENT"
    PARENT = "PARENT"
    MODERATOR = "MODERATOR"
    ADMIN = "ADMIN"


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(80), unique=True, index=True)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.READER,
        nullable=False,
    )

    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    bio: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    contents: Mapped[List["Content"]] = relationship(
        back_populates="author",
        cascade="all, delete-orphan",
    )