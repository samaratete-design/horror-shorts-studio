from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import FinalTimelineModel
from shared_types.final_timeline import FinalTimeline


class FinalTimelineRepository:
    """
    Repository for FinalTimeline persistence — one row per story, same
    upsert pattern as EditPlan/VoiceTrack.

    segments is stored as a lightweight JSONB snapshot of the
    reconciliation result itself (not a duplicate of any other table).
    music_asset_ids / visual_asset_ids store REFERENCES ONLY (uuid
    strings) into MusicAssetModel / VisualAssetModel — never a copy of
    the underlying bytes or metadata. visual_asset_ids is derived by the
    caller from VisualAssetRepository.list_by_scene() per segment, since
    FinalSegment itself carries no shot reference.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_uuid(story_id: str | UUID) -> UUID:
        return story_id if isinstance(story_id, UUID) else UUID(str(story_id))

    async def save(
        self,
        story_id: str | UUID,
        timeline: FinalTimeline,
        visual_asset_ids: list[str],
        music_asset_ids: list[str],
    ) -> FinalTimelineModel:
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(FinalTimelineModel).where(
                FinalTimelineModel.story_id == story_uuid
            )
        )
        db_timeline = result.scalar_one_or_none()

        if db_timeline is None:
            db_timeline = FinalTimelineModel(
                story_id=story_uuid,
            )
            self.session.add(db_timeline)

        db_timeline.total_duration = timeline.total_duration
        db_timeline.segments = [
            {
                "scene_number": seg.scene_number,
                "start_time": seg.start_time,
                "end_time": seg.end_time,
            }
            for seg in timeline.segments
        ]
        db_timeline.visual_asset_ids = visual_asset_ids
        db_timeline.music_asset_ids = music_asset_ids

        await self.session.commit()
        await self.session.refresh(db_timeline)

        return db_timeline

    async def get(self, story_id: str | UUID) -> FinalTimelineModel | None:
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(FinalTimelineModel).where(
                FinalTimelineModel.story_id == story_uuid
            )
        )
        return result.scalar_one_or_none()
