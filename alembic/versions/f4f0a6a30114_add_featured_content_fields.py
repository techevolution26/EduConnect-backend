"""add featured content fields

Revision ID: f4f0a6a30114
Revises: bcbc827e3be5
Create Date: 2026-05-27 13:51:04.216086

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4f0a6a30114'
down_revision: Union[str, Sequence[str], None] = 'bcbc827e3be5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "contents",
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default="0",  # Changed from "false" to "0" for MySQL compatibility
        ),
    )

    op.add_column(
        "contents",
        sa.Column(
            "featured_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_contents_is_featured",
        "contents",
        ["is_featured"],
    )


def downgrade() -> None:
    op.drop_index("ix_contents_is_featured", table_name="contents")
    op.drop_column("contents", "featured_at")
    op.drop_column("contents", "is_featured")
