from __future__ import annotations

import base64

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.story import (
    EditPlanModel,
    VoiceTrackModel,
    ScriptModel,
    Story as SQLStory,
    StoryDNAModel,
    StoryStatus as SQLStoryStatus,
)
from shared_types.story_dna import StoryDNA
from shared_types.structured_script import StructuredScript
from shared_types.edit_plan import EditPlan, SceneCut
from shared_types.voice_track import VoiceTrack, VoiceSegment
from app.models.story import StoryDNAModel, ScriptModel, EditPlanModel, VoiceTrackModel


class StoryRepository:
    """Repository for Story persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_uuid(story_id: str | UUID) -> UUID:
        """Normalize story ID to UUID."""
        return story_id if isinstance(story_id, UUID) else UUID(str(story_id))

    @staticmethod
    def _enum_value(value: object) -> object:
        """Return enum value when applicable, otherwise return the value."""
        return getattr(value, "value", value)

    async def get_by_id(
        self,
        story_id: str | UUID,
    ) -> SQLStory | None:
        """Return a story by ID."""
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(SQLStory).where(SQLStory.id == story_uuid)
        )

        return result.scalar_one_or_none()

    async def update_status(
        self,
        story_id: str | UUID,
        status: str | SQLStoryStatus,
    ) -> SQLStory | None:
        """Update a story status and return the updated story."""
        story = await self.get_by_id(story_id)

        if story is None:
            return None

        if isinstance(status, SQLStoryStatus):
            story.status = status
        else:
            normalized_status = getattr(status, "value", status)
            normalized_status = str(normalized_status).lower()
            story.status = SQLStoryStatus(normalized_status)

        await self.session.commit()
        await self.session.refresh(story)

        return story

    async def save_dna(
        self,
        story_id: str | UUID,
        dna: StoryDNA,
    ) -> StoryDNAModel:
        """
        Create or update Story DNA for a story.

        Each story has at most one DNA record because
        story_dna.story_id is unique.
        """
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(StoryDNAModel).where(
                StoryDNAModel.story_id == story_uuid
            )
        )

        db_dna = result.scalar_one_or_none()

        if db_dna is None:
            db_dna = StoryDNAModel(
                story_id=story_uuid,
            )
            self.session.add(db_dna)

        db_dna.premise = dna.premise
        db_dna.setting = dna.setting
        db_dna.threat = dna.threat
        db_dna.fear_mechanism = dna.fear_mechanism
        db_dna.narrative_device = dna.narrative_device
        db_dna.twist_type = self._enum_value(dna.twist_type)
        db_dna.ending_type = self._enum_value(dna.ending_type)
        db_dna.pov = self._enum_value(dna.pov)
        db_dna.time_period = dna.time_period
        db_dna.supernatural_element = dna.supernatural_element
        db_dna.conflict = dna.conflict
        db_dna.emotional_theme = dna.emotional_theme
        db_dna.protagonist_archetype = dna.protagonist_archetype
        db_dna.antagonist_archetype = dna.antagonist_archetype
        db_dna.core_fear = dna.core_fear
        db_dna.visual_style = dna.visual_style
        db_dna.unique_story_hook = dna.unique_story_hook
        db_dna.embedding = dna.embedding

        await self.session.commit()
        await self.session.refresh(db_dna)

        return db_dna

    async def save_script(
        self,
        story_id: str | UUID,
        script: StructuredScript,
    ) -> ScriptModel:
        """
        Create or update the structured script for a story.

        Each story has at most one script record because
        ScriptModel.story_id is unique. Nested scene/dialogue data is
        stored as JSONB via model_dump().
        """
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(ScriptModel).where(
                ScriptModel.story_id == story_uuid
            )
        )

        db_script = result.scalar_one_or_none()

        if db_script is None:
            db_script = ScriptModel(
                story_id=story_uuid,
            )
            self.session.add(db_script)

        db_script.title = script.title
        db_script.logline = script.logline
        db_script.tone = script.tone
        db_script.language = script.language
        db_script.estimated_duration = script.estimated_duration
        db_script.scenes = [
            scene.model_dump() for scene in script.scenes
        ]

        await self.session.commit()
        await self.session.refresh(db_script)

        return db_script


    async def save_edit_plan(
        self,
        story_id,
        edit_plan: EditPlan,
    ) -> EditPlanModel:
        """
        Create or update the edit plan for a story.

        Each story has at most one edit plan record because
        EditPlanModel.story_id is unique. Cut data is stored as JSONB.
        """
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(EditPlanModel).where(
                EditPlanModel.story_id == story_uuid
            )
        )
        db_edit_plan = result.scalar_one_or_none()

        if db_edit_plan is None:
            db_edit_plan = EditPlanModel(
                story_id=story_uuid,
            )
            self.session.add(db_edit_plan)

        db_edit_plan.total_duration = edit_plan.total_duration
        db_edit_plan.cuts = [
            {
                "scene_number": cut.scene_number,
                "start_time": cut.start_time,
                "end_time": cut.end_time,
            }
            for cut in edit_plan.cuts
        ]

        await self.session.commit()
        await self.session.refresh(db_edit_plan)

        return db_edit_plan


    async def save_voice_track(
        self,
        story_id,
        voice_track: VoiceTrack,
    ) -> VoiceTrackModel:
        """
        Create or update the voice track for a story.

        Each story has at most one voice track record because
        VoiceTrackModel.story_id is unique. Audio bytes are base64-encoded
        for JSONB storage.
        """
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(VoiceTrackModel).where(
                VoiceTrackModel.story_id == story_uuid
            )
        )
        db_voice_track = result.scalar_one_or_none()

        if db_voice_track is None:
            db_voice_track = VoiceTrackModel(
                story_id=story_uuid,
            )
            self.session.add(db_voice_track)

        db_voice_track.segments = [
            {
                "scene_number": segment.scene_number,
                "speaker": segment.speaker,
                "start_time": segment.start_time,
                "end_time": segment.end_time,
                "audio_b64": base64.b64encode(segment.audio).decode("ascii"),
            }
            for segment in voice_track.segments
        ]

        await self.session.commit()
        await self.session.refresh(db_voice_track)

        return db_voice_track

    async def get_dna(
        self,
        story_id: str | UUID,
    ) -> StoryDNA | None:
        """Fetch and convert the persisted StoryDNA for a story, or None."""
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(StoryDNAModel).where(
                StoryDNAModel.story_id == story_uuid
            )
        )
        db_dna = result.scalar_one_or_none()

        if db_dna is None:
            return None

        return StoryDNA(
            story_id=str(db_dna.story_id),
            premise=db_dna.premise,
            setting=db_dna.setting,
            threat=db_dna.threat,
            fear_mechanism=db_dna.fear_mechanism,
            narrative_device=db_dna.narrative_device,
            twist_type=db_dna.twist_type,
            ending_type=db_dna.ending_type,
            pov=db_dna.pov,
            time_period=db_dna.time_period,
            supernatural_element=db_dna.supernatural_element,
            conflict=db_dna.conflict,
            emotional_theme=db_dna.emotional_theme,
            protagonist_archetype=db_dna.protagonist_archetype,
            antagonist_archetype=db_dna.antagonist_archetype,
            core_fear=db_dna.core_fear,
            visual_style=db_dna.visual_style,
            unique_story_hook=db_dna.unique_story_hook,
            embedding=db_dna.embedding,
        )

    async def get_script(
        self,
        story_id: str | UUID,
    ) -> StructuredScript | None:
        """Fetch and convert the persisted StructuredScript for a story, or None."""
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(ScriptModel).where(
                ScriptModel.story_id == story_uuid
            )
        )
        db_script = result.scalar_one_or_none()

        if db_script is None:
            return None

        return StructuredScript(
            title=db_script.title,
            logline=db_script.logline,
            tone=db_script.tone,
            language=db_script.language,
            estimated_duration=db_script.estimated_duration,
            scenes=db_script.scenes,
        )

    async def get_edit_plan(
        self,
        story_id: str | UUID,
    ) -> EditPlan | None:
        """Fetch and convert the persisted EditPlan for a story, or None."""
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(EditPlanModel).where(
                EditPlanModel.story_id == story_uuid
            )
        )
        db_edit_plan = result.scalar_one_or_none()

        if db_edit_plan is None:
            return None

        return EditPlan(
            story_id=str(db_edit_plan.story_id),
            total_duration=db_edit_plan.total_duration,
            cuts=[SceneCut(**cut) for cut in db_edit_plan.cuts],
        )

    async def get_voice_track(
        self,
        story_id: str | UUID,
    ) -> VoiceTrack | None:
        """Fetch and convert the persisted VoiceTrack for a story, or None."""
        story_uuid = self._to_uuid(story_id)

        result = await self.session.execute(
            select(VoiceTrackModel).where(
                VoiceTrackModel.story_id == story_uuid
            )
        )
        db_voice_track = result.scalar_one_or_none()

        if db_voice_track is None:
            return None

        return VoiceTrack(
            story_id=str(db_voice_track.story_id),
            segments=[
                VoiceSegment(
                    scene_number=seg["scene_number"],
                    speaker=seg["speaker"],
                    start_time=seg["start_time"],
                    end_time=seg["end_time"],
                    audio=base64.b64decode(seg["audio_b64"]),
                )
                for seg in db_voice_track.segments
            ],
        )
