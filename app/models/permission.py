"""
AdminPermission: a row means "this user has been granted this permission".

Only meaningful for ADMIN-role users -- SUPER_ADMIN bypasses this table
entirely (see core/permissions.py), and non-admin roles should never have
rows here (enforced in services/admin_service.py, not at the DB level,
to keep this a plain association table).
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class AdminPermission(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "admin_permissions"
    __table_args__ = (
        UniqueConstraint("user_id", "permission", name="uq_admin_permission_user_perm"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Stored as the Permission enum's string value (see core/permissions.py).
    # Kept as a plain String rather than a native DB enum so new permissions
    # can be added without an alter-type migration.
    permission: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Who granted this permission -- kept for audit purposes. Nullable
    # because permissions created by a data migration/seed won't have one.
    granted_by_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    user = relationship("User", foreign_keys=[user_id], back_populates="admin_permissions")
    granted_by = relationship("User", foreign_keys=[granted_by_id])
