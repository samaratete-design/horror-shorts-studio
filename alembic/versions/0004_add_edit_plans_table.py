"""add edit_plans table for edit plan persistence

Revision ID: 0004_add_edit_plans_table
Revises: 0003_add_scripts_table
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "0004_add_edit_plans_table"
down_revision: Union[str, None] = "0003_add_scripts_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "edit_plans",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("total_duration", sa.Float(), nullable=False),
        sa.Column("cuts", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id"),
    )


def downgrade() -> None:
    op.drop_table("edit_plans")
