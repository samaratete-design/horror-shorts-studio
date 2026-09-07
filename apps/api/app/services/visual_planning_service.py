from __future__ import annotations

from shared_types.structured_script import SceneItem
from shared_types.story_dna import StoryDNA
from shared_types.edit_plan import EditPlan, SceneCut
from shared_types.shot_plan import ShotPlan

from app.services.ai_provider import AIProvider

_VALID_ASSET_TYPES = {"image", "video"}
_DURATION_EPSILON = 1e-6


class VisualPlanningError(Exception):
    """Raised when shot plan generation fails, or the resulting ShotPlan is invalid."""


class InvalidVisualPlanningRequestError(Exception):
    """Raised when the generation request itself is invalid, before the provider is called."""


class VisualPlanningService:
    """
    Turns a single SceneItem into a ShotPlan (a sequence of Shots).

    Validates the request (including that the scene has a matching SceneCut
    in the EditPlan), delegates to AIProvider.generate_shot_plan(), then
    validates the returned ShotPlan: identity (story_id/scene_number match),
    each Shot's asset_type is "image" or "video", and the shots' total
    estimated_duration matches the matching SceneCut's duration exactly
    (within floating-point epsilon). Assembly, not this service, owns any
    further pacing reconciliation against actual generated-asset durations.
    """

    def __init__(self, ai_provider: AIProvider):
        self._ai_provider = ai_provider

    async def generate(
        self,
        story_id: str,
        scene: SceneItem,
        story_dna: StoryDNA,
        edit_plan: EditPlan,
    ) -> ShotPlan:
        scene_cut = self._validate(story_id, scene, story_dna, edit_plan)

        try:
            result = await self._ai_provider.generate_shot_plan(
                story_id, scene, story_dna, edit_plan
            )
        except Exception as exc:
            raise VisualPlanningError("Shot plan generation failed") from exc

        self._validate_result(result, story_id, scene, scene_cut)

        return result

    @staticmethod
    def _validate(
        story_id: str,
        scene: SceneItem,
        story_dna: StoryDNA,
        edit_plan: EditPlan,
    ) -> SceneCut:
        if not story_id:
            raise InvalidVisualPlanningRequestError(
                "story_id is required and cannot be empty"
            )

        if scene is None:
            raise InvalidVisualPlanningRequestError(
                "scene is required and cannot be None"
            )

        if story_dna is None:
            raise InvalidVisualPlanningRequestError(
                "story_dna is required and cannot be None"
            )

        if edit_plan is None:
            raise InvalidVisualPlanningRequestError(
                "edit_plan is required and cannot be None"
            )

        scene_cut = next(
            (cut for cut in edit_plan.cuts if cut.scene_number == scene.scene_number),
            None,
        )
        if scene_cut is None:
            raise InvalidVisualPlanningRequestError(
                f"scene_number {scene.scene_number} not found in edit_plan"
            )

        return scene_cut

    @staticmethod
    def _validate_result(
        result: ShotPlan,
        story_id: str,
        scene: SceneItem,
        scene_cut: SceneCut,
    ) -> None:
        if result is None:
            raise VisualPlanningError("AIProvider returned no ShotPlan")

        if result.story_id != story_id:
            raise VisualPlanningError(
                f"ShotPlan.story_id mismatch: requested {story_id!r}, "
                f"got {result.story_id!r}"
            )

        if result.scene_number != scene.scene_number:
            raise VisualPlanningError(
                f"ShotPlan.scene_number mismatch: requested {scene.scene_number!r}, "
                f"got {result.scene_number!r}"
            )

        for shot in result.shots:
            if shot.asset_type not in _VALID_ASSET_TYPES:
                raise VisualPlanningError(
                    f"Shot.asset_type must be one of {sorted(_VALID_ASSET_TYPES)}, "
                    f"got {shot.asset_type!r}"
                )

        total_shot_duration = sum(shot.estimated_duration for shot in result.shots)
        scene_cut_duration = scene_cut.end_time - scene_cut.start_time

        if abs(total_shot_duration - scene_cut_duration) > _DURATION_EPSILON:
            raise VisualPlanningError(
                f"Sum of shot durations ({total_shot_duration}) does not match "
                f"scene cut duration ({scene_cut_duration}) for "
                f"scene_number {scene.scene_number}"
            )
