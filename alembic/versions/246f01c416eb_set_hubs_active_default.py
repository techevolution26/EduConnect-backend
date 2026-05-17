"""set hubs active default

Revision ID: 246f01c416eb
Revises: e30fa7ca6b37
Create Date: 2026-05-18 00:27:13.914324

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '246f01c416eb'
down_revision: Union[str, Sequence[str], None] = 'e30fa7ca6b37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "hubs",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=sa.text("1"),
    )

    op.execute("UPDATE hubs SET is_active = 1 WHERE is_active IS NULL")


def downgrade() -> None:
    op.alter_column(
        "hubs",
        "is_active",
        existing_type=sa.Boolean(),
        nullable=False,
        server_default=None,
    )
