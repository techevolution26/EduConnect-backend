from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ContentAssetType(str, enum.Enum):
    IMAGE = "IMAGE"
    FILE = "FILE"


class ContentAsset(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "content_assets"

    content_id: Mapped[str] = mapped_column(
        ForeignKey("contents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    asset_type: Mapped[ContentAssetType] = mapped_column(
        Enum(ContentAssetType),
        nullable=False,
    )

    url: Mapped[str] = mapped_column(String(500), nullable=False)
    filename: Mapped[Optional[str]] = mapped_column(String(255))
    mime_type: Mapped[Optional[str]] = mapped_column(String(120))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)

    content = relationship("Content", back_populates="assets")