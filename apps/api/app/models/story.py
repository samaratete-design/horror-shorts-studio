import enum
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import EMBEDDING_DIMENSIONS
from app.db.base import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class StoryStatus(str, enum.Enum):
    DRAFT = "draft"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    EDITING = "editing"
    RENDERING = "rendering"
    READY = "ready"
    PUBLISHED = "published"
    FAILED = "failed"
    ARCHIVED = "archived"


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    status: Mapped[StoryStatus] = mapped_column(
        SAEnum(StoryStatus),
        default=StoryStatus.DRAFT,
        nullable=False,
    )

    original_idea: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    # DEPRECATED: legacy free-text script column, superseded by
    # ScriptModel (structured, JSONB-backed). Scheduled for removal
    # in a future cleanup migration. Not written to by current code.
    generated_script: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    language: Mapped[str] = mapped_column(
        String(16),
        default="ar",
        nullable=False,
    )

    duration: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    dna: Mapped["StoryDNAModel | None"] = relationship(
        back_populates="story",
        uselist=False,
        cascade="all, delete-orphan",
    )

    script: Mapped["ScriptModel | None"] = relationship(
        back_populates="story",
        uselist=False,
        cascade="all, delete-orphan",
    )


    edit_plan: Mapped["EditPlanModel | None"] = relationship(
        back_populates="story",
        uselist=False,
        cascade="all, delete-orphan",
    )

    voice_track: Mapped["VoiceTrackModel | None"] = relationship(
        back_populates="story",
        uselist=False,
        cascade="all, delete-orphan",
    )

    visual_assets: Mapped[list["VisualAssetModel"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )

    music_assets: Mapped[list["MusicAssetModel"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )

    final_timeline: Mapped["FinalTimelineModel | None"] = relationship(
        back_populates="story",
        uselist=False,
        cascade="all, delete-orphan",
    )


class StoryDNAModel(Base):
    """
    Persistence model for StoryDNA.

    This model intentionally remains separate from the domain/Pydantic
    StoryDNA schema.
    """

    __tablename__ = "story_dna"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    premise: Mapped[str] = mapped_column(Text)
    setting: Mapped[str] = mapped_column(Text)
    threat: Mapped[str] = mapped_column(Text)
    fear_mechanism: Mapped[str] = mapped_column(Text)
    narrative_device: Mapped[str] = mapped_column(Text)

    twist_type: Mapped[str] = mapped_column(
        String(64),
    )

    ending_type: Mapped[str] = mapped_column(
        String(64),
    )

    pov: Mapped[str] = mapped_column(
        String(64),
    )

    time_period: Mapped[str] = mapped_column(
        String(64),
        default="present_day",
    )

    supernatural_element: Mapped[str] = mapped_column(
        Text,
        default="unknown",
    )

    conflict: Mapped[str] = mapped_column(Text)
    emotional_theme: Mapped[str] = mapped_column(Text)
    protagonist_archetype: Mapped[str] = mapped_column(
        String(128),
        default="ordinary_person",
    )

    antagonist_archetype: Mapped[str] = mapped_column(
        String(128),
        default="unknown_force",
    )

    core_fear: Mapped[str] = mapped_column(Text)

    visual_style: Mapped[str] = mapped_column(
        String(128),
        default="dark_realistic",
    )

    unique_story_hook: Mapped[str] = mapped_column(Text)

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS),
        nullable=True,
    )

    story: Mapped["Story"] = relationship(
        back_populates="dna",
    )


class ScriptModel(Base):
    """
    Persistence model for StructuredScript.

    This model intentionally remains separate from the domain/Pydantic
    StructuredScript schema. Nested scene/dialogue data is stored as
    JSONB rather than normalized into separate tables (YAGNI: no current
    need to query individual scenes at the DB level).
    """

    __tablename__ = "scripts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(Text)
    logline: Mapped[str] = mapped_column(Text)
    tone: Mapped[str] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16), default="ar")
    estimated_duration: Mapped[float] = mapped_column(Float)

    scenes: Mapped[list] = mapped_column(JSONB)

    story: Mapped["Story"] = relationship(
        back_populates="script",
    )


class EditPlanModel(Base):
    """
    Persistence model for EditPlan.

    This model intentionally remains separate from the domain/dataclass
    EditPlan schema. Nested scene-cut data is stored as JSONB rather than
    normalized into separate tables (YAGNI: no current need to query
    individual cuts at the DB level).
    """

    __tablename__ = "edit_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    total_duration: Mapped[float] = mapped_column(Float)

    cuts: Mapped[list] = mapped_column(JSONB)

    story: Mapped["Story"] = relationship(
        back_populates="edit_plan",
    )


class VoiceTrackModel(Base):
    """
    Persistence model for VoiceTrack.

    Segments are stored as JSONB; each segment's audio bytes are
    base64-encoded (JSONB cannot hold raw bytes directly).
    """

    __tablename__ = "voice_tracks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    segments: Mapped[list] = mapped_column(JSONB)

    story: Mapped["Story"] = relationship(
        back_populates="voice_track",
    )


class VisualAssetModel(Base):
    """
    Persistence model for a single VisualAsset (one row per shot).

    Unlike DNA/Script/EditPlan/VoiceTrack (one row per story), a story has
    MANY visual assets — one per (scene_number, shot_number, asset_type).
    That tuple is the natural key and carries a UNIQUE constraint so that
    regenerating the same shot upserts in place instead of duplicating.

    Media bytes are NOT stored here — only a storage_key reference into
    AssetStorage. actual_duration is nullable (image shots have none).
    """

    __tablename__ = "visual_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )

    scene_number: Mapped[int] = mapped_column(Integer, nullable=False)
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    asset_type: Mapped[str] = mapped_column(String(16), nullable=False)

    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    actual_duration: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    story: Mapped["Story"] = relationship(
        back_populates="visual_assets",
    )

    __table_args__ = (
        UniqueConstraint(
            "story_id", "scene_number", "shot_number", "asset_type",
            name="uq_visual_assets_story_scene_shot_type",
        ),
    )


class MusicAssetModel(Base):
    """
    Persistence model for a single MusicAsset (one row per cue).

    A story has MANY music assets — one per cue_number. That is the
    natural key, with a UNIQUE constraint so regenerating the same cue
    upserts in place instead of duplicating.

    Media bytes are NOT stored here — only a storage_key reference into
    AssetStorage.
    """

    __tablename__ = "music_assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )

    cue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    actual_duration: Mapped[float] = mapped_column(Float, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    story: Mapped["Story"] = relationship(
        back_populates="music_assets",
    )

    __table_args__ = (
        UniqueConstraint(
            "story_id", "cue_number",
            name="uq_music_assets_story_cue",
        ),
    )


class FinalTimelineModel(Base):
    """
    Persistence model for FinalTimeline — one row per story (like EditPlan).

    segments is a lightweight JSONB snapshot of the reconciled timing
    itself (scene_number/start_time/end_time) — not a duplicate of any
    other table's data, since it IS the reconciliation result.

    music_asset_ids / visual_asset_ids store REFERENCES ONLY (uuid
    strings into MusicAssetModel / VisualAssetModel) — never a copy of
    the underlying media bytes or asset metadata. visual_asset_ids exists
    because FinalSegment (the domain dataclass) carries no shot
    reference; this mapping is derived at save time by querying
    VisualAssetModel by scene_number, not by changing the domain type.
    """

    __tablename__ = "final_timelines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    total_duration: Mapped[float] = mapped_column(Float, nullable=False)
    segments: Mapped[list] = mapped_column(JSONB, nullable=False)
    music_asset_ids: Mapped[list] = mapped_column(JSONB, nullable=False)
    visual_asset_ids: Mapped[list] = mapped_column(JSONB, nullable=False)

    story: Mapped["Story"] = relationship(
        back_populates="final_timeline",
    )


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    story_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stories.id", ondelete="CASCADE"),
        nullable=False,
    )

    views: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    likes: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    comments: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    shares: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    retention_rate: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    swiped_away_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    average_view_duration: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    subscribers_gained: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    pattern_snapshot: Mapped[dict] = mapped_column(
        JSONB,
        default=dict,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
