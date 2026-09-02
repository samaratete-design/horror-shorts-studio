import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SAEnum, Float, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base
from app.core.constants import EMBEDDING_DIMENSIONS


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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[StoryStatus] = mapped_column(SAEnum(StoryStatus), default=StoryStatus.DRAFT, nullable=False)
    original_idea: Mapped[str] = mapped_column(Text, nullable=False)
    generated_script: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="ar")
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    dna: Mapped["StoryDNAModel"] = relationship(back_populates="story", uselist=False, cascade="all, delete-orphan")


class StoryDNAModel(Base):
    """Persistence model for shared_types.StoryDNA. Kept 1:1 with the pydantic schema."""

    __tablename__ = "story_dna"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"), unique=True)

    premise: Mapped[str] = mapped_column(Text)
    setting: Mapped[str] = mapped_column(Text)
    threat: Mapped[str] = mapped_column(Text)
    fear_mechanism: Mapped[str] = mapped_column(Text)
    narrative_device: Mapped[str] = mapped_column(Text)
    twist_type: Mapped[str] = mapped_column(String(64))
    ending_type: Mapped[str] = mapped_column(String(64))
    pov: Mapped[str] = mapped_column(String(64))
    time_period: Mapped[str] = mapped_column(String(64), default="present_day")
    supernatural_element: Mapped[str] = mapped_column(Text, default="unknown")
    conflict: Mapped[str] = mapped_column(Text)
    emotional_theme: Mapped[str] = mapped_column(Text)
    protagonist_archetype: Mapped[str] = mapped_column(String(128), default="ordinary_person")
    antagonist_archetype: Mapped[str] = mapped_column(String(128), default="unknown_force")
    core_fear: Mapped[str] = mapped_column(Text)
    visual_style: Mapped[str] = mapped_column(String(128), default="dark_realistic")
    unique_story_hook: Mapped[str] = mapped_column(Text)

    # Dimension is the single configured EMBEDDING_DIMENSIONS value (app.core.constants),
    # which must match EmbeddingProvider.dimensions for whichever provider is active.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIMENSIONS), nullable=True)

    story: Mapped["Story"] = relationship(back_populates="dna")


class PerformanceMetric(Base):
    __tablename__ = "performance_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    story_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("stories.id", ondelete="CASCADE"))
    views: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    shares: Mapped[int] = mapped_column(Integer, default=0)
    retention_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    swiped_away_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    average_view_duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    subscribers_gained: Mapped[int] = mapped_column(Integer, default=0)
    pattern_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
