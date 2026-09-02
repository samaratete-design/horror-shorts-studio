"""initial schema: stories, story_dna, performance_metrics

Revision ID: 0001
Revises:
Create Date: 2026-09-02

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector

from app.core.constants import EMBEDDING_DIMENSIONS

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

STORY_STATUS_VALUES = (
    "draft", "analyzing", "generating", "editing", "rendering",
    "ready", "published", "failed", "archived",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    story_status = postgresql.ENUM(*STORY_STATUS_VALUES, name="storystatus")
    story_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "stories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", story_status, nullable=False, server_default="draft"),
        sa.Column("original_idea", sa.Text, nullable=False),
        sa.Column("generated_script", sa.Text, nullable=True),
        sa.Column("language", sa.String(16), nullable=False, server_default="ar"),
        sa.Column("duration", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "story_dna",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "story_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("premise", sa.Text, nullable=False),
        sa.Column("setting", sa.Text, nullable=False),
        sa.Column("threat", sa.Text, nullable=False),
        sa.Column("fear_mechanism", sa.Text, nullable=False),
        sa.Column("narrative_device", sa.Text, nullable=False),
        sa.Column("twist_type", sa.String(64), nullable=False),
        sa.Column("ending_type", sa.String(64), nullable=False),
        sa.Column("pov", sa.String(64), nullable=False),
        sa.Column("time_period", sa.String(64), nullable=False, server_default="present_day"),
        sa.Column("supernatural_element", sa.Text, nullable=False, server_default="unknown"),
        sa.Column("conflict", sa.Text, nullable=False),
        sa.Column("emotional_theme", sa.Text, nullable=False),
        sa.Column("protagonist_archetype", sa.String(128), nullable=False, server_default="ordinary_person"),
        sa.Column("antagonist_archetype", sa.String(128), nullable=False, server_default="unknown_force"),
        sa.Column("core_fear", sa.Text, nullable=False),
        sa.Column("visual_style", sa.String(128), nullable=False, server_default="dark_realistic"),
        sa.Column("unique_story_hook", sa.Text, nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIMENSIONS), nullable=True),
    )
    op.execute(
        "CREATE INDEX story_dna_embedding_idx ON story_dna "
        "USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "performance_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("story_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stories.id", ondelete="CASCADE")),
        sa.Column("views", sa.Integer, nullable=False, server_default="0"),
        sa.Column("likes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("comments", sa.Integer, nullable=False, server_default="0"),
        sa.Column("shares", sa.Integer, nullable=False, server_default="0"),
        sa.Column("retention_rate", sa.Float, nullable=True),
        sa.Column("swiped_away_pct", sa.Float, nullable=True),
        sa.Column("average_view_duration", sa.Float, nullable=True),
        sa.Column("subscribers_gained", sa.Integer, nullable=False, server_default="0"),
        sa.Column("pattern_snapshot", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("performance_metrics")
    op.execute("DROP INDEX IF EXISTS story_dna_embedding_idx")
    op.drop_table("story_dna")
    op.drop_table("stories")
    postgresql.ENUM(*STORY_STATUS_VALUES, name="storystatus").drop(op.get_bind(), checkfirst=True)
