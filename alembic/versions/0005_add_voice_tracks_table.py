"""add voice_tracks table for voice track persistence

Revision ID: 0005_add_voice_tracks_table
Revises: 0004_add_edit_plans_table
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision: str = "0005_add_voice_tracks_table"
down_revision: Union[str, None] = "0004_add_edit_plans_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "voice_tracks",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("segments", JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id"),
    )


def downgrade() -> None:
    op.drop_table("voice_tracks")
