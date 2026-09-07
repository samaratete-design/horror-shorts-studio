import pytest

from shared_types.structured_script import SceneItem
from shared_types.story_dna import StoryDNA
from shared_types.edit_plan import EditPlan, SceneCut
from shared_types.shot_plan import ShotPlan, Shot

from app.services.ai_provider import AIProvider
from app.services.visual_planning_service import (
    InvalidVisualPlanningRequestError,
    VisualPlanningError,
    VisualPlanningService,
)


def make_scene(scene_number: int = 1) -> SceneItem:
    return SceneItem(
        scene_number=scene_number,
        purpose="establish isolation",
        location="empty apartment",
        time_of_day="night",
        characters=["Man"],
        action="He stares at his phone, waiting.",
        dialogue=[],
        narration="I knew the call was coming.",
        emotion="dread",
        estimated_duration=10.0,
    )


def make_story_dna() -> StoryDNA:
    return StoryDNA(
        premise="A man is haunted by his phone.",
        setting="empty apartment",
        threat="a doppelganger",
        fear_mechanism="isolation",
        narrative_device="phone calls",
        conflict="man vs unknown caller",
        emotional_theme="paranoia",
        core_fear="loss of control",
        unique_story_hook="the caller knows his thoughts",
        visual_style="dark_realistic",
    )


def make_edit_plan(story_id: str = "story-1") -> EditPlan:
    return EditPlan(
        story_id=story_id,
        total_duration=20.0,
        cuts=[
            SceneCut(scene_number=1, start_time=0.0, end_time=10.0),
            SceneCut(scene_number=2, start_time=10.0, end_time=20.0),
        ],
    )


def make_shot_plan(
    story_id: str = "story-1",
    scene_number: int = 1,
    shot_durations=None,
    asset_type: str = "image",
) -> ShotPlan:
    if shot_durations is None:
        shot_durations = [5.0, 5.0]

    return ShotPlan(
        story_id=story_id,
        scene_number=scene_number,
        shots=[
            Shot(
                shot_number=i + 1,
                visual_prompt=f"shot {i + 1}",
                estimated_duration=d,
                asset_type=asset_type,
            )
            for i, d in enumerate(shot_durations)
        ],
    )


class FakeAIProvider(AIProvider):
    def __init__(self, shot_plan_to_return):
        self.shot_plan_to_return = shot_plan_to_return
        self.calls = []

    async def generate_story_dna(self, original_idea: str):
        raise NotImplementedError

    async def generate_music_plan(self, story_id, script, story_dna, edit_plan):
        raise NotImplementedError

    async def generate_shot_plan(self, story_id, scene, story_dna, edit_plan):
        self.calls.append((story_id, scene, story_dna, edit_plan))
        return self.shot_plan_to_return


class FailingAIProvider(AIProvider):
    async def generate_story_dna(self, original_idea: str):
        raise NotImplementedError

    async def generate_music_plan(self, story_id, script, story_dna, edit_plan):
        raise NotImplementedError

    async def generate_shot_plan(self, story_id, scene, story_dna, edit_plan):
        raise RuntimeError("shot model unavailable")


# 1. Invalid request — rejected before provider is called

@pytest.mark.asyncio
async def test_generate_rejects_none_scene_without_calling_provider():
    provider = FakeAIProvider(make_shot_plan())
    service = VisualPlanningService(provider)

    with pytest.raises(InvalidVisualPlanningRequestError):
        await service.generate(
            story_id="story-1", scene=None, story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_rejects_none_story_dna_without_calling_provider():
    provider = FakeAIProvider(make_shot_plan())
    service = VisualPlanningService(provider)

    with pytest.raises(InvalidVisualPlanningRequestError):
        await service.generate(
            story_id="story-1", scene=make_scene(), story_dna=None, edit_plan=make_edit_plan()
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_rejects_none_edit_plan_without_calling_provider():
    provider = FakeAIProvider(make_shot_plan())
    service = VisualPlanningService(provider)

    with pytest.raises(InvalidVisualPlanningRequestError):
        await service.generate(
            story_id="story-1", scene=make_scene(), story_dna=make_story_dna(), edit_plan=None
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_rejects_empty_story_id_without_calling_provider():
    provider = FakeAIProvider(make_shot_plan())
    service = VisualPlanningService(provider)

    with pytest.raises(InvalidVisualPlanningRequestError):
        await service.generate(
            story_id="", scene=make_scene(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )

    assert provider.calls == []


# 2. Input consistency — scene not found in edit_plan (rejected before provider call)

@pytest.mark.asyncio
async def test_generate_rejects_scene_not_found_in_edit_plan():
    provider = FakeAIProvider(make_shot_plan())
    service = VisualPlanningService(provider)

    scene = make_scene(scene_number=99)
    edit_plan = make_edit_plan()

    with pytest.raises(InvalidVisualPlanningRequestError, match="scene_number 99"):
        await service.generate(
            story_id="story-1", scene=scene, story_dna=make_story_dna(), edit_plan=edit_plan
        )

    assert provider.calls == []


# 3. Provider interaction

@pytest.mark.asyncio
async def test_generate_delegates_to_ai_provider_with_scene_story_dna_and_edit_plan():
    scene = make_scene(scene_number=1)
    story_dna = make_story_dna()
    edit_plan = make_edit_plan()
    expected_plan = make_shot_plan(scene_number=1, shot_durations=[10.0])
    provider = FakeAIProvider(expected_plan)
    service = VisualPlanningService(provider)

    result = await service.generate(
        story_id="story-1", scene=scene, story_dna=story_dna, edit_plan=edit_plan
    )

    assert len(provider.calls) == 1
    assert provider.calls[0] == ("story-1", scene, story_dna, edit_plan)
    assert result is expected_plan


@pytest.mark.asyncio
async def test_generate_wraps_provider_failure():
    service = VisualPlanningService(FailingAIProvider())

    with pytest.raises(VisualPlanningError) as exc_info:
        await service.generate(
            story_id="story-1", scene=make_scene(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )

    assert isinstance(exc_info.value.__cause__, RuntimeError)


# 4. Result validity

@pytest.mark.asyncio
async def test_generate_rejects_invalid_provider_result():
    provider = FakeAIProvider(None)
    service = VisualPlanningService(provider)

    with pytest.raises(VisualPlanningError):
        await service.generate(
            story_id="story-1", scene=make_scene(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )


# 5. Result identity

@pytest.mark.asyncio
async def test_generate_rejects_result_with_mismatched_story_id():
    wrong_plan = make_shot_plan(story_id="wrong-story", shot_durations=[10.0])
    provider = FakeAIProvider(wrong_plan)
    service = VisualPlanningService(provider)

    with pytest.raises(VisualPlanningError):
        await service.generate(
            story_id="story-1", scene=make_scene(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )


@pytest.mark.asyncio
async def test_generate_rejects_result_with_mismatched_scene_number():
    wrong_plan = make_shot_plan(scene_number=2, shot_durations=[10.0])
    provider = FakeAIProvider(wrong_plan)
    service = VisualPlanningService(provider)

    with pytest.raises(VisualPlanningError):
        await service.generate(
            story_id="story-1", scene=make_scene(scene_number=1), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )


# 6. Duration bounds — against the matching SceneCut only

@pytest.mark.asyncio
async def test_generate_accepts_shots_matching_scene_cut_duration():
    plan = make_shot_plan(scene_number=1, shot_durations=[4.0, 6.0])
    provider = FakeAIProvider(plan)
    service = VisualPlanningService(provider)

    result = await service.generate(
        story_id="story-1", scene=make_scene(scene_number=1), story_dna=make_story_dna(), edit_plan=make_edit_plan()
    )

    assert result is plan


@pytest.mark.asyncio
async def test_generate_rejects_shots_exceeding_scene_cut_duration():
    plan = make_shot_plan(scene_number=1, shot_durations=[6.0, 6.0])
    provider = FakeAIProvider(plan)
    service = VisualPlanningService(provider)

    with pytest.raises(VisualPlanningError):
        await service.generate(
            story_id="story-1", scene=make_scene(scene_number=1), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )


@pytest.mark.asyncio
async def test_generate_rejects_shots_short_of_scene_cut_duration():
    plan = make_shot_plan(scene_number=1, shot_durations=[3.0, 3.0, 3.0])
    provider = FakeAIProvider(plan)
    service = VisualPlanningService(provider)

    with pytest.raises(VisualPlanningError):
        await service.generate(
            story_id="story-1", scene=make_scene(scene_number=1), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )


# 7. Shot.asset_type contract

def test_shot_requires_asset_type():
    with pytest.raises(TypeError):
        Shot(
            shot_number=1,
            visual_prompt="a dark hallway",
            estimated_duration=2.0,
        )


def test_shot_accepts_image_asset_type():
    shot = Shot(
        shot_number=1,
        visual_prompt="a dark hallway",
        estimated_duration=2.0,
        asset_type="image",
    )

    assert shot.asset_type == "image"


def test_shot_accepts_video_asset_type():
    shot = Shot(
        shot_number=1,
        visual_prompt="a dark hallway",
        estimated_duration=2.0,
        asset_type="video",
    )

    assert shot.asset_type == "video"


@pytest.mark.asyncio
async def test_visual_planning_rejects_invalid_asset_type():
    plan = ShotPlan(
        story_id="story-1",
        scene_number=1,
        shots=[
            Shot(
                shot_number=1,
                visual_prompt="a dark hallway",
                estimated_duration=10.0,
                asset_type="gif",
            )
        ],
    )
    provider = FakeAIProvider(plan)
    service = VisualPlanningService(provider)

    with pytest.raises(VisualPlanningError):
        await service.generate(
            story_id="story-1", scene=make_scene(scene_number=1), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )


@pytest.mark.asyncio
async def test_visual_planning_preserves_asset_type():
    plan = ShotPlan(
        story_id="story-1",
        scene_number=1,
        shots=[
            Shot(
                shot_number=1,
                visual_prompt="a dark hallway",
                estimated_duration=4.0,
                asset_type="video",
            ),
            Shot(
                shot_number=2,
                visual_prompt="a closed door",
                estimated_duration=6.0,
                asset_type="image",
            ),
        ],
    )
    provider = FakeAIProvider(plan)
    service = VisualPlanningService(provider)

    result = await service.generate(
        story_id="story-1", scene=make_scene(scene_number=1), story_dna=make_story_dna(), edit_plan=make_edit_plan()
    )

    assert result.shots[0].asset_type == "video"
    assert result.shots[1].asset_type == "image"
