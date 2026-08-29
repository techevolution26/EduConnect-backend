"""align role and timestamp defaults with models

Revision ID: 1c8e53f6ce8c
Revises: 7f98563f52d5
Create Date: 2026-08-30 00:51:08.866824

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1c8e53f6ce8c"
down_revision: Union[str, Sequence[str], None] = "7f98563f52d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ---------------------------------------------------------------
    # TimestampMixin compatibility
    #
    # ---------------------------------------------------------------

    for table in (
        "admin_permissions",
        "schools",
        "student_profiles",
        "events",
        "event_participants",
        "badges",
        "referral_earnings",
    ):
        op.alter_column(
            table,
            "created_at",
            existing_type=sa.DateTime(),
            server_default=sa.func.now(),
            existing_nullable=False,
        )
        op.alter_column(
            table,
            "updated_at",
            existing_type=sa.DateTime(),
            server_default=sa.func.now(),
            existing_nullable=False,
        )
