import pytest

from shared_types.structured_script import StructuredScript, SceneItem
from shared_types.edit_plan import EditPlan, SceneCut

from app.services.editing_service import EditingService, InvalidScriptError


def make_scene(number: int, duration: float) -> SceneItem:
    return SceneItem(
        scene_number=number,
        purpose="test purpose",
        location="test location",
        time_of_day="night",
        characters=["Man"],
        action="does something",
        dialogue=[],
        narration="narration text",
        emotion="dread",
        estimated_duration=duration,
    )


def make_script(scenes) -> StructuredScript:
    return StructuredScript(
        title="Test Script",
        logline="A test script.",
        tone="dread",
        language="ar",
        estimated_duration=sum(s.estimated_duration for s in scenes),
        scenes=scenes,
    )


@pytest.mark.asyncio
async def test_edit_rejects_none_script():
    service = EditingService()

    with pytest.raises(InvalidScriptError):
        await service.edit("story-1", None)


@pytest.mark.asyncio
async def test_edit_rejects_script_with_no_scenes():
    service = EditingService()
    empty_script = make_script(scenes=[])

    with pytest.raises(InvalidScriptError):
        await service.edit("story-1", empty_script)


@pytest.mark.asyncio
async def test_edit_produces_sequential_non_overlapping_cuts():
    service = EditingService()
    script = make_script([make_scene(1, 10.0), make_scene(2, 15.0), make_scene(3, 5.0)])

    plan = await service.edit("story-1", script)

    assert isinstance(plan, EditPlan)
    assert plan.story_id == "story-1"
    assert plan.cuts == [
        SceneCut(scene_number=1, start_time=0.0, end_time=10.0),
        SceneCut(scene_number=2, start_time=10.0, end_time=25.0),
        SceneCut(scene_number=3, start_time=25.0, end_time=30.0),
    ]


@pytest.mark.asyncio
async def test_edit_total_duration_matches_sum_of_scene_durations():
    service = EditingService()
    script = make_script([make_scene(1, 12.5), make_scene(2, 7.5)])

    plan = await service.edit("story-1", script)

    assert plan.total_duration == 20.0


@pytest.mark.asyncio
async def test_edit_is_deterministic_for_same_input():
    service = EditingService()
    script = make_script([make_scene(1, 10.0), make_scene(2, 20.0)])

    plan_a = await service.edit("story-1", script)
    plan_b = await service.edit("story-1", script)

    assert plan_a == plan_b
