import pytest

from shared_types.structured_script import StructuredScript, SceneItem
from shared_types.story_dna import StoryDNA
from shared_types.edit_plan import EditPlan, SceneCut
from shared_types.music_plan import MusicPlan, MusicCue

from app.services.ai_provider import AIProvider
from app.services.music_planning_service import (
    InvalidMusicPlanningRequestError,
    MusicPlanningError,
    MusicPlanningService,
)


def make_script() -> StructuredScript:
    return StructuredScript(
        title="Test Script",
        logline="A test script.",
        tone="dread",
        language="ar",
        estimated_duration=20.0,
        scenes=[
            SceneItem(
                scene_number=1,
                purpose="setup",
                location="apartment",
                time_of_day="night",
                characters=["Man"],
                action="He waits.",
                dialogue=[],
                narration="Scene one.",
                emotion="dread",
                estimated_duration=10.0,
            ),
            SceneItem(
                scene_number=2,
                purpose="escalation",
                location="hallway",
                time_of_day="night",
                characters=["Man"],
                action="He runs.",
                dialogue=[],
                narration="Scene two.",
                emotion="terror",
                estimated_duration=10.0,
            ),
        ],
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


def make_music_plan(story_id: str = "story-1", total_duration: float = 20.0) -> MusicPlan:
    return MusicPlan(
        story_id=story_id,
        total_duration=total_duration,
        cues=[
            # NOTE: cue boundary deliberately does NOT align with SceneCut
            # boundaries (7.0 falls inside scene 1's 0-10 range) — this is
            # allowed by design; cues only need to fit within [0, total_duration].
            MusicCue(cue_number=1, start_time=0.0, end_time=7.0, mood="rising_dread", music_prompt="low drone"),
            MusicCue(cue_number=2, start_time=7.0, end_time=20.0, mood="terror_sting", music_prompt="sharp strings"),
        ],
    )


class FakeAIProvider(AIProvider):
    def __init__(self, music_plan_to_return: MusicPlan):
        self.music_plan_to_return = music_plan_to_return
        self.calls: list[tuple] = []

    async def generate_story_dna(self, original_idea: str) -> StoryDNA:
        raise NotImplementedError

    async def generate_music_plan(self, story_id, script, story_dna, edit_plan) -> MusicPlan:
        self.calls.append((story_id, script, story_dna, edit_plan))
        return self.music_plan_to_return


class FailingAIProvider(AIProvider):
    async def generate_story_dna(self, original_idea: str) -> StoryDNA:
        raise NotImplementedError

    async def generate_music_plan(self, story_id, script, story_dna, edit_plan) -> MusicPlan:
        raise RuntimeError("music model unavailable")


# 1. Invalid request — rejected before provider is called
@pytest.mark.asyncio
async def test_generate_rejects_none_script_without_calling_provider():
    provider = FakeAIProvider(make_music_plan())
    service = MusicPlanningService(provider)

    with pytest.raises(InvalidMusicPlanningRequestError):
        await service.generate(
            story_id="story-1", script=None, story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_rejects_none_story_dna_without_calling_provider():
    provider = FakeAIProvider(make_music_plan())
    service = MusicPlanningService(provider)

    with pytest.raises(InvalidMusicPlanningRequestError):
        await service.generate(
            story_id="story-1", script=make_script(), story_dna=None, edit_plan=make_edit_plan()
        )

    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_rejects_none_edit_plan_without_calling_provider():
    provider = FakeAIProvider(make_music_plan())
    service = MusicPlanningService(provider)

    with pytest.raises(InvalidMusicPlanningRequestError):
        await service.generate(
            story_id="story-1", script=make_script(), story_dna=make_story_dna(), edit_plan=None
        )

    assert provider.calls == []


# 2. Provider failure wrapped
@pytest.mark.asyncio
async def test_generate_wraps_provider_failure():
    service = MusicPlanningService(FailingAIProvider())

    with pytest.raises(MusicPlanningError) as exc_info:
        await service.generate(
            story_id="story-1", script=make_script(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )

    assert isinstance(exc_info.value.__cause__, RuntimeError)


# 3. Correct delegation
@pytest.mark.asyncio
async def test_generate_delegates_to_ai_provider_with_all_inputs():
    script = make_script()
    story_dna = make_story_dna()
    edit_plan = make_edit_plan()
    provider = FakeAIProvider(make_music_plan())
    service = MusicPlanningService(provider)

    result = await service.generate(
        story_id="story-1", script=script, story_dna=story_dna, edit_plan=edit_plan
    )

    assert len(provider.calls) == 1
    assert provider.calls[0] == ("story-1", script, story_dna, edit_plan)
    assert isinstance(result, MusicPlan)


# 4. Identity validation — story_id mismatch rejected
@pytest.mark.asyncio
async def test_generate_rejects_result_with_mismatched_story_id():
    wrong_plan = make_music_plan(story_id="wrong-story")
    provider = FakeAIProvider(wrong_plan)
    service = MusicPlanningService(provider)

    with pytest.raises(MusicPlanningError):
        await service.generate(
            story_id="story-1", script=make_script(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )


# 5. Identity validation — total_duration mismatch with edit_plan rejected
@pytest.mark.asyncio
async def test_generate_rejects_result_with_mismatched_total_duration():
    wrong_plan = make_music_plan(total_duration=999.0)
    provider = FakeAIProvider(wrong_plan)
    service = MusicPlanningService(provider)

    with pytest.raises(MusicPlanningError):
        await service.generate(
            story_id="story-1", script=make_script(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )


# 6. Cues must fit within [0, total_duration] — but NOT aligned to SceneCut boundaries
@pytest.mark.asyncio
async def test_generate_accepts_cues_not_aligned_to_scene_cut_boundaries():
    provider = FakeAIProvider(make_music_plan())  # cue boundary at 7.0, scene boundary at 10.0
    service = MusicPlanningService(provider)

    result = await service.generate(
        story_id="story-1", script=make_script(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
    )

    assert len(result.cues) == 2
    assert result.cues[0].end_time == pytest.approx(7.0)  # NOT 10.0 — proves no scene-boundary lock


# 7. Cue exceeding total_duration is rejected
@pytest.mark.asyncio
async def test_generate_rejects_cue_exceeding_total_duration():
    out_of_bounds_plan = MusicPlan(
        story_id="story-1",
        total_duration=20.0,
        cues=[MusicCue(cue_number=1, start_time=15.0, end_time=25.0, mood="x", music_prompt="x")],
    )
    provider = FakeAIProvider(out_of_bounds_plan)
    service = MusicPlanningService(provider)

    with pytest.raises(MusicPlanningError):
        await service.generate(
            story_id="story-1", script=make_script(), story_dna=make_story_dna(), edit_plan=make_edit_plan()
        )
