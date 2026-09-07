from abc import ABC, abstractmethod

from shared_types.story_dna import StoryDNA
from shared_types.structured_script import StructuredScript, SceneItem
from shared_types.shot_plan import ShotPlan
from shared_types.edit_plan import EditPlan
from shared_types.music_plan import MusicPlan


class AIProvider(ABC):
    """Abstract contract for AI generation."""

    @abstractmethod
    async def generate_story_dna(
        self,
        original_idea: str,
    ) -> StoryDNA:
        raise NotImplementedError

    async def generate_structured_script(
        self,
        story_dna: StoryDNA,
    ) -> StructuredScript:
        raise NotImplementedError(
            "This AI provider does not support structured script generation"
        )

    async def generate_shot_plan(
        self,
        story_id: str,
        scene: SceneItem,
        story_dna: StoryDNA,
        edit_plan: EditPlan,
    ) -> ShotPlan:
        raise NotImplementedError(
            "This AI provider does not support shot plan generation"
        )

    async def generate_music_plan(
        self,
        story_id: str,
        script: StructuredScript,
        story_dna: StoryDNA,
        edit_plan: EditPlan,
    ) -> MusicPlan:
        raise NotImplementedError(
            "This AI provider does not support music plan generation"
        )
