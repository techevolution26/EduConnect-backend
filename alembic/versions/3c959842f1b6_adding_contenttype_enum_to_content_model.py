"""adding contentType enum to content_model

Revision ID: 3c959842f1b6
Revises: ec56bafefa73
Create Date: 2026-06-16 15:22:47.641198

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c959842f1b6'
down_revision: Union[str, Sequence[str], None] = 'ec56bafefa73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_enum = sa.Enum(
    "ARTICLE",
    "STORY",
    "POEM",
    "FAITH",
    "EDUCATION",
    "CHILDREN",
    "NEWS",
    "AUDIO",
    name="contenttype",
)

new_enum = sa.Enum(
    "ARTICLE",
    "STORY",
    "FICTION",
    "POEM",
    "FAITH",
    "EDUCATION",
    "CHILDREN",
    "NEWS",
    "AUDIO",
    "WRITING_TIPS",
    "SELF_IMPROVEMENT",
    "RELATIONSHIP",
    "MONEY_FINANCE",
    "MEDICINE",
    "PSYCHOLOGY",
    "MENTAL_HEALTH",
    "HUMOR",
    "WOMEN",
    "FITNESS",
    "SELF_AWARENESS",
    "PARENTING",
    name="contenttype",
)


def upgrade() -> None:
    op.alter_column(
        "contents",
        "content_type",
        existing_type=old_enum,
        type_=new_enum,
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "contents",
        "content_type",
        existing_type=new_enum,
        type_=old_enum,
        existing_nullable=False,
    )
