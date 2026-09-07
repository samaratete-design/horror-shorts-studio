"""align database schema with current SQLAlchemy models

Revision ID: 0002
Revises: 0001_initial_schema
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector


revision: str = "0002_align_models"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


story_status = sa.Enum(
    "DRAFT",
    "ANALYZING",
    "GENERATING",
    "EDITING",
    "RENDERING",
    "READY",
    "PUBLISHED",
    "FAILED",
    "ARCHIVED",
    name="storystatus",
)


def upgrade() -> None:
    # Current tables are empty, so rebuild them to match the models exactly.
    op.drop_table("performance_metrics")
    op.drop_table("story_dna")
    op.drop_table("stories")

    op.create_table(
        "stories",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", story_status, nullable=False),
        sa.Column("original_idea", sa.Text(), nullable=False),
        sa.Column("generated_script", sa.Text(), nullable=True),
        sa.Column("language", sa.String(16), nullable=False),
        sa.Column("duration", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "story_dna",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("premise", sa.Text(), nullable=False),
        sa.Column("setting", sa.Text(), nullable=False),
        sa.Column("threat", sa.Text(), nullable=False),
        sa.Column("fear_mechanism", sa.Text(), nullable=False),
        sa.Column("narrative_device", sa.Text(), nullable=False),
        sa.Column("twist_type", sa.String(64), nullable=False),
        sa.Column("ending_type", sa.String(64), nullable=False),
        sa.Column("pov", sa.String(64), nullable=False),
        sa.Column("time_period", sa.String(64), nullable=False),
        sa.Column("supernatural_element", sa.Text(), nullable=False),
        sa.Column("conflict", sa.Text(), nullable=False),
        sa.Column("emotional_theme", sa.Text(), nullable=False),
        sa.Column("protagonist_archetype", sa.String(128), nullable=False),
        sa.Column("antagonist_archetype", sa.String(128), nullable=False),
        sa.Column("core_fear", sa.Text(), nullable=False),
        sa.Column("visual_style", sa.String(128), nullable=False),
        sa.Column("unique_story_hook", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(256), nullable=True),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("story_id"),
    )

    op.create_table(
        "performance_metrics",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("story_id", UUID(as_uuid=True), nullable=False),
        sa.Column("views", sa.Integer(), nullable=False),
        sa.Column("likes", sa.Integer(), nullable=False),
        sa.Column("comments", sa.Integer(), nullable=False),
        sa.Column("shares", sa.Integer(), nullable=False),
        sa.Column("retention_rate", sa.Float(), nullable=True),
        sa.Column("swiped_away_pct", sa.Float(), nullable=True),
        sa.Column("average_view_duration", sa.Float(), nullable=True),
        sa.Column("subscribers_gained", sa.Integer(), nullable=False),
        sa.Column("pattern_snapshot", JSONB(), nullable=False),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["story_id"],
            ["stories.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("performance_metrics")
    op.drop_table("story_dna")
    op.drop_table("stories")

