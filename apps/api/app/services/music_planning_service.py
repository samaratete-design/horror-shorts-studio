from shared_types.structured_script import StructuredScript
from shared_types.story_dna import StoryDNA
from shared_types.edit_plan import EditPlan
from shared_types.music_plan import MusicPlan

from app.services.ai_provider import AIProvider


class MusicPlanningError(Exception):
    """Raised when music plan generation fails."""


class InvalidMusicPlanningRequestError(Exception):
    """Raised when the generation request is invalid, before the provider is called."""


class MusicPlanningService:
    """
    Turns a whole StructuredScript into a MusicPlan (a story-wide mood arc
    of MusicCues), timed against the official Planned Timeline (EditPlan).

    This service holds no opinion on musical content — it validates the
    request, delegates to AIProvider.generate_music_plan(), and verifies
    the returned MusicPlan actually matches the requested story_id and
    the EditPlan's total_duration before handing it back. Cues are NOT
    required to align with SceneCut boundaries — they only need to fit
    within [0, edit_plan.total_duration].
    """

    def __init__(self, ai_provider: AIProvider):
        self._ai_provider = ai_provider

    async def generate(
        self,
        story_id: str,
        script: StructuredScript,
        story_dna: StoryDNA,
        edit_plan: EditPlan,
    ) -> MusicPlan:
        self._validate(script, story_dna, edit_plan)

        try:
            result = await self._ai_provider.generate_music_plan(
                story_id, script, story_dna, edit_plan
            )
        except Exception as exc:
            raise MusicPlanningError("Music plan generation failed") from exc

        self._validate_identity(result, story_id, edit_plan)

        return result

    @staticmethod
    def _validate(
        script: StructuredScript, story_dna: StoryDNA, edit_plan: EditPlan
    ) -> None:
        if script is None:
            raise InvalidMusicPlanningRequestError("script is required and cannot be None")

        if story_dna is None:
            raise InvalidMusicPlanningRequestError("story_dna is required and cannot be None")

        if edit_plan is None:
            raise InvalidMusicPlanningRequestError("edit_plan is required and cannot be None")

    @staticmethod
    def _validate_identity(
        result: MusicPlan, story_id: str, edit_plan: EditPlan
    ) -> None:
        if result.story_id != story_id:
            raise MusicPlanningError(
                f"MusicPlan.story_id mismatch: requested {story_id!r}, got {result.story_id!r}"
            )

        if result.total_duration != edit_plan.total_duration:
            raise MusicPlanningError(
                f"MusicPlan.total_duration mismatch: expected {edit_plan.total_duration!r}, "
                f"got {result.total_duration!r}"
            )

        for cue in result.cues:
            if cue.start_time < 0 or cue.end_time > edit_plan.total_duration:
                raise MusicPlanningError(
                    f"MusicCue {cue.cue_number} out of bounds: "
                    f"[{cue.start_time}, {cue.end_time}] not within [0, {edit_plan.total_duration}]"
                )
