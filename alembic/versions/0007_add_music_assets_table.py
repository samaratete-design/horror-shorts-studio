"""add music_assets table for music asset persistence

Revision ID: 0007_add_music_assets_table
Revises: 0006_add_visual_assets_table
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0007_add_music_assets_table"
down_revision: Union[str, None] = "0006_add_visual_assets_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "music_assets",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("cue_number", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("actual_duration", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "story_id", "cue_number",
            name="uq_music_assets_story_cue",
        ),
    )


def downgrade() -> None:
    op.drop_table("music_assets")
