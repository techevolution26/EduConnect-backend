"""fixing missing rows

Revision ID: 568c6b5dc7ca
Revises: be8d85389559
Create Date: 2026-06-30 15:20:12.621828
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "568c6b5dc7ca"
down_revision: Union[str, Sequence[str], None] = "be8d85389559"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

old_enum = sa.Enum(
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
    "TECHNOLOGY",
    "SCIENCE",
    "CARS",
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