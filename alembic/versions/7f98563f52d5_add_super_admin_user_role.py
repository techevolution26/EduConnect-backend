"""add super admin user role

Revision ID: 7f98563f52d5
Revises: 2481109ac4ee
Create Date: 2026-08-30 00:26:18.766459

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "7f98563f52d5"
down_revision: Union[str, Sequence[str], None] = "2481109ac4ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE users
        MODIFY COLUMN role ENUM(
            'READER',
            'WRITER',
            'TEACHER',
            'STUDENT',
            'PARENT',
            'MODERATOR',
            'ADMIN',
            'SUPER_ADMIN'
        ) NOT NULL
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE users
        MODIFY COLUMN role ENUM(
            'READER',
            'WRITER',
            'TEACHER',
            'STUDENT',
            'PARENT',
            'MODERATOR',
            'ADMIN'
        ) NOT NULL
    """)
