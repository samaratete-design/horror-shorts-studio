"""add visual_assets table for visual asset persistence

Revision ID: 0006_add_visual_assets_table
Revises: 0005_add_voice_tracks_table
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "0006_add_visual_assets_table"
down_revision: Union[str, None] = "0005_add_voice_tracks_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visual_assets",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("scene_number", sa.Integer(), nullable=False),
        sa.Column("shot_number", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("storage_key", sa.Text(), nullable=False),
        sa.Column("actual_duration", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "story_id", "scene_number", "shot_number", "asset_type",
            name="uq_visual_assets_story_scene_shot_type",
        ),
    )


def downgrade() -> None:
    op.drop_table("visual_assets")
