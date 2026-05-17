from typing import List, Optional

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Hub(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hubs"

    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500))

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="1",
        nullable=False,
    )

    contents: Mapped[List["Content"]] = relationship(back_populates="hub")
    members: Mapped[List["HubMember"]] = relationship(
        back_populates="hub",
        cascade="all, delete-orphan",
    )


class HubMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "hub_members"

    hub_id: Mapped[str] = mapped_column(
        ForeignKey("hubs.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    hub: Mapped["Hub"] = relationship(back_populates="members")

    __table_args__ = (
        UniqueConstraint("hub_id", "user_id", name="uq_hub_member"),
    )