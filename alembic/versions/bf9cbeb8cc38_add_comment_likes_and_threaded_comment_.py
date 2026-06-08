"""add comment likes and threaded comment relations

Revision ID: bf9cbeb8cc38
Revises: db023dc74026
Create Date: 2026-06-09 00:24:22.631866

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf9cbeb8cc38'
down_revision: Union[str, Sequence[str], None] = 'db023dc74026'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "comment_likes" not in inspector.get_table_names():
        op.create_table(
            "comment_likes",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("comment_id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.ForeignKeyConstraint(["comment_id"], ["comments.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("comment_id", "user_id", name="uq_comment_likes_comment_user"),
        )
        op.create_index("ix_comment_likes_comment_id", "comment_likes", ["comment_id"], unique=False)
        op.create_index("ix_comment_likes_user_id", "comment_likes", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "comment_likes" in inspector.get_table_names():
        op.drop_index("ix_comment_likes_user_id", table_name="comment_likes")
        op.drop_index("ix_comment_likes_comment_id", table_name="comment_likes")
        op.drop_table("comment_likes")
