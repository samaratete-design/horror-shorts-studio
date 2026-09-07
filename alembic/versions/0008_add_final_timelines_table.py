"""add final_timelines table for final timeline persistence

Revision ID: 0008_add_final_timelines_table
Revises: 0007_add_music_assets_table
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "0008_add_final_timelines_table"
down_revision: Union[str, None] = "0007_add_music_assets_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "final_timelines",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("total_duration", sa.Float(), nullable=False),
        sa.Column("segments", JSONB(), nullable=False),
        sa.Column("music_asset_ids", JSONB(), nullable=False),
        sa.Column("visual_asset_ids", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id"),
    )


def downgrade() -> None:
    op.drop_table("final_timelines")
