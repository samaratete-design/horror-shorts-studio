"""add scripts table for structured script persistence

Revision ID: 0003_add_scripts_table
Revises: 0002_align_models
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "0003_add_scripts_table"
down_revision: Union[str, None] = "0002_align_models"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scripts",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("logline", sa.Text(), nullable=False),
        sa.Column("tone", sa.String(64), nullable=False),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("estimated_duration", sa.Float(), nullable=False),
        sa.Column("scenes", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id"),
    )


def downgrade() -> None:
    op.drop_table("scripts")
