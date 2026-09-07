from shared_types.structured_script import StructuredScript
from shared_types.edit_plan import EditPlan, SceneCut


class InvalidScriptError(Exception):
    """Raised when the script is missing or has no scenes to edit."""


class EditingService:
    """
    Deterministic transformation of a StructuredScript into an EditPlan.
    No external provider, no I/O — pure computation over scene durations.
    """

    async def edit(self, story_id: str, script: StructuredScript) -> EditPlan:
        if script is None:
            raise InvalidScriptError("script is required and cannot be None")

        if not script.scenes:
            raise InvalidScriptError("script must contain at least one scene")

        cuts: list[SceneCut] = []
        cursor = 0.0

        for scene in script.scenes:
            start = cursor
            end = cursor + scene.estimated_duration
            cuts.append(
                SceneCut(
                    scene_number=scene.scene_number,
                    start_time=start,
                    end_time=end,
                )
            )
            cursor = end

        return EditPlan(
            story_id=story_id,
            total_duration=cursor,
            cuts=cuts,
        )
