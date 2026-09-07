import uuid
from unittest.mock import AsyncMock

import pytest

from shared_types.story_dna import StoryDNA, TwistType, EndingType, POV
from shared_types.structured_script import StructuredScript, SceneItem
from shared_types.edit_plan import EditPlan, SceneCut
from shared_types.voice_track import VoiceTrack, VoiceSegment
from shared_types.shot_plan import ShotPlan, Shot
from shared_types.visual_asset import VisualAsset
from shared_types.music_plan import MusicPlan, MusicCue
from shared_types.music_asset import MusicAsset
from shared_types.final_timeline import FinalTimeline, FinalSegment

from app.domain.story_workflow import StoryStatus
from app.services.story_workflow_orchestrator import (
    StoryWorkflowOrchestrator,
    MissingAssemblyPreconditionError,
)


# ---------------------------------------------------------------------------
# Fixtures / builders
# ---------------------------------------------------------------------------

def make_story_dna(story_id: str) -> StoryDNA:
    return StoryDNA(
        story_id=story_id,
        premise="A man receives calls from himself one hour in the future.",
        setting="empty apartment",
        threat="a version of himself from the future",
        fear_mechanism="loss of control over one's own timeline",
        narrative_device="phone calls",
        twist_type=TwistType.TIME_LOOP,
        ending_type=EndingType.CLIFFHANGER,
        pov=POV.FIRST_PERSON,
        conflict="man vs his own future self",
        emotional_theme="paranoia",
        core_fear="losing agency over your own life",
        unique_story_hook="the calls get closer together each time",
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


def make_script(scenes=None) -> StructuredScript:
    if scenes is None:
        scenes = [make_scene(scene_number=1)]
    return StructuredScript(
        title="The Empty Apartment",
        logline="A man receives calls from himself, one hour ahead.",
        tone="dread",
        language="ar",
        estimated_duration=90.0,
        scenes=scenes,
    )


def make_edit_plan(story_id: str, cuts=None) -> EditPlan:
    if cuts is None:
        cuts = [SceneCut(scene_number=1, start_time=0.0, end_time=10.0)]
    total = max(c.end_time for c in cuts)
    return EditPlan(story_id=story_id, total_duration=total, cuts=cuts)


def make_voice_track(story_id: str) -> VoiceTrack:
    return VoiceTrack(
        story_id=story_id,
        segments=[
            VoiceSegment(
                scene_number=1,
                speaker="narrator",
                start_time=0.0,
                end_time=10.0,
                audio=b"voice-bytes",
            )
        ],
    )


def make_shot_plan(story_id: str, scene_number: int = 1, shots=None) -> ShotPlan:
    if shots is None:
        shots = [
            Shot(
                shot_number=1,
                visual_prompt="a dark hallway",
                estimated_duration=10.0,
                asset_type="image",
            )
        ]
    return ShotPlan(story_id=story_id, scene_number=scene_number, shots=shots)


def make_visual_asset(
    story_id: str, scene_number: int = 1, shot_number: int = 1, asset_type: str = "image"
) -> VisualAsset:
    return VisualAsset(
        story_id=story_id,
        scene_number=scene_number,
        shot_number=shot_number,
        asset_type=asset_type,
        asset=b"asset-bytes",
        actual_duration=None if asset_type == "image" else 10.0,
    )


def make_music_plan(story_id: str, cues=None) -> MusicPlan:
    if cues is None:
        cues = [
            MusicCue(
                cue_number=1,
                start_time=0.0,
                end_time=10.0,
                mood="dread",
                music_prompt="a low ominous drone",
            )
        ]
    return MusicPlan(story_id=story_id, total_duration=10.0, cues=cues)


def make_music_asset(story_id: str, cue_number: int = 1) -> MusicAsset:
    return MusicAsset(
        story_id=story_id,
        cue_number=cue_number,
        asset=b"music-bytes",
        actual_duration=10.0,
    )


def make_final_timeline(story_id: str, music_assets=None) -> FinalTimeline:
    return FinalTimeline(
        story_id=story_id,
        total_duration=10.0,
        segments=[FinalSegment(scene_number=1, start_time=0.0, end_time=10.0)],
        music_assets=music_assets or [],
    )


def make_orchestrator(
    workflow_service=None,
    generation_service=None,
    repository=None,
    script_generation_service=None,
    editing_service=None,
    voice_generation_service=None,
    visual_planning_service=None,
    visual_generation_service=None,
    music_planning_service=None,
    music_generation_service=None,
    assembly_service=None,
    visual_asset_repository=None,
    music_asset_repository=None,
    final_timeline_repository=None,
):
    return StoryWorkflowOrchestrator(
        workflow_service=workflow_service or AsyncMock(),
        generation_service=generation_service or AsyncMock(),
        repository=repository or AsyncMock(),
        script_generation_service=script_generation_service or AsyncMock(),
        editing_service=editing_service or AsyncMock(),
        voice_generation_service=voice_generation_service or AsyncMock(),
        visual_planning_service=visual_planning_service or AsyncMock(),
        visual_generation_service=visual_generation_service or AsyncMock(),
        music_planning_service=music_planning_service or AsyncMock(),
        music_generation_service=music_generation_service or AsyncMock(),
        assembly_service=assembly_service or AsyncMock(),
        visual_asset_repository=visual_asset_repository or AsyncMock(),
        music_asset_repository=music_asset_repository or AsyncMock(),
        final_timeline_repository=final_timeline_repository or AsyncMock(),
    )


def make_full_repository(story_id: str, script=None, dna=None, edit_plan=None, voice_track=None):
    """A repository AsyncMock preconfigured with all 4 precondition getters
    returning valid data, so tests can override only what they care about."""
    repository = AsyncMock()
    repository.get_dna.return_value = dna or make_story_dna(story_id)
    repository.get_script.return_value = script or make_script()
    repository.get_edit_plan.return_value = edit_plan or make_edit_plan(story_id)
    repository.get_voice_track.return_value = voice_track or make_voice_track(story_id)
    return repository


def make_happy_path_orchestrator(story_id: str, **overrides):
    """A fully-wired orchestrator where every dependency succeeds with
    single-scene / single-cue / single-shot data, for tests that need the
    full pipeline to complete without error."""
    dna = make_story_dna(story_id)
    script = make_script()
    edit_plan = make_edit_plan(story_id)
    voice_track = make_voice_track(story_id)
    shot_plan = make_shot_plan(story_id)
    visual_asset = make_visual_asset(story_id)
    music_plan = make_music_plan(story_id)
    music_asset = make_music_asset(story_id)
    final_timeline = make_final_timeline(story_id)

    repository = overrides.pop("repository", None) or make_full_repository(
        story_id, script=script, dna=dna, edit_plan=edit_plan, voice_track=voice_track
    )

    visual_planning_service = overrides.pop("visual_planning_service", None) or AsyncMock()
    visual_planning_service.generate.return_value = shot_plan

    visual_generation_service = overrides.pop("visual_generation_service", None) or AsyncMock()
    visual_generation_service.generate_image.return_value = visual_asset
    visual_generation_service.generate_video.return_value = visual_asset

    music_planning_service = overrides.pop("music_planning_service", None) or AsyncMock()
    music_planning_service.generate.return_value = music_plan

    music_generation_service = overrides.pop("music_generation_service", None) or AsyncMock()
    music_generation_service.generate.return_value = music_asset

    assembly_service = overrides.pop("assembly_service", None) or AsyncMock()
    assembly_service.assemble.return_value = final_timeline

    visual_asset_repository = overrides.pop("visual_asset_repository", None)
    if visual_asset_repository is None:
        visual_asset_repository = AsyncMock()
        visual_asset_repository.list_by_scene.return_value = [
            AsyncMock(id=uuid.uuid4())
        ]

    music_asset_repository = overrides.pop("music_asset_repository", None)
    if music_asset_repository is None:
        music_asset_repository = AsyncMock()
        music_asset_repository.list_by_story.return_value = [AsyncMock(id=uuid.uuid4())]

    final_timeline_repository = overrides.pop("final_timeline_repository", None) or AsyncMock()

    workflow_service = overrides.pop("workflow_service", None) or AsyncMock()

    return make_orchestrator(
        workflow_service=workflow_service,
        repository=repository,
        visual_planning_service=visual_planning_service,
        visual_generation_service=visual_generation_service,
        music_planning_service=music_planning_service,
        music_generation_service=music_generation_service,
        assembly_service=assembly_service,
        visual_asset_repository=visual_asset_repository,
        music_asset_repository=music_asset_repository,
        final_timeline_repository=final_timeline_repository,
        **overrides,
    ), {
        "dna": dna,
        "script": script,
        "edit_plan": edit_plan,
        "voice_track": voice_track,
        "shot_plan": shot_plan,
        "visual_asset": visual_asset,
        "music_plan": music_plan,
        "music_asset": music_asset,
        "final_timeline": final_timeline,
    }


# ---------------------------------------------------------------------------
# 1. Preconditions / data retrieval
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_fetches_all_precondition_data():
    story_id = str(uuid.uuid4())
    orchestrator, data = make_happy_path_orchestrator(story_id)

    await orchestrator.advance_to_assembly(story_id)

    orchestrator._repository.get_dna.assert_awaited_once_with(story_id)
    orchestrator._repository.get_script.assert_awaited_once_with(story_id)
    orchestrator._repository.get_edit_plan.assert_awaited_once_with(story_id)
    orchestrator._repository.get_voice_track.assert_awaited_once_with(story_id)


@pytest.mark.asyncio
async def test_advance_to_assembly_raises_when_dna_missing():
    story_id = str(uuid.uuid4())
    repository = make_full_repository(story_id)
    repository.get_dna.return_value = None

    orchestrator = make_orchestrator(repository=repository)

    with pytest.raises(MissingAssemblyPreconditionError):
        await orchestrator.advance_to_assembly(story_id)

    repository.get_script.assert_not_awaited()
    repository.get_edit_plan.assert_not_awaited()
    repository.get_voice_track.assert_not_awaited()


@pytest.mark.asyncio
async def test_advance_to_assembly_raises_when_script_missing():
    story_id = str(uuid.uuid4())
    repository = make_full_repository(story_id)
    repository.get_script.return_value = None

    orchestrator = make_orchestrator(repository=repository)

    with pytest.raises(MissingAssemblyPreconditionError):
        await orchestrator.advance_to_assembly(story_id)

    repository.get_edit_plan.assert_not_awaited()
    repository.get_voice_track.assert_not_awaited()


@pytest.mark.asyncio
async def test_advance_to_assembly_raises_when_edit_plan_missing():
    story_id = str(uuid.uuid4())
    repository = make_full_repository(story_id)
    repository.get_edit_plan.return_value = None

    orchestrator = make_orchestrator(repository=repository)

    with pytest.raises(MissingAssemblyPreconditionError):
        await orchestrator.advance_to_assembly(story_id)

    repository.get_voice_track.assert_not_awaited()


@pytest.mark.asyncio
async def test_advance_to_assembly_raises_when_voice_track_missing():
    story_id = str(uuid.uuid4())
    repository = make_full_repository(story_id)
    repository.get_voice_track.return_value = None

    orchestrator = make_orchestrator(repository=repository)

    with pytest.raises(MissingAssemblyPreconditionError):
        await orchestrator.advance_to_assembly(story_id)


@pytest.mark.asyncio
async def test_advance_to_assembly_missing_precondition_transitions_to_failed():
    story_id = str(uuid.uuid4())
    repository = make_full_repository(story_id)
    repository.get_dna.return_value = None

    workflow_service = AsyncMock()
    orchestrator = make_orchestrator(repository=repository, workflow_service=workflow_service)

    with pytest.raises(MissingAssemblyPreconditionError):
        await orchestrator.advance_to_assembly(story_id)

    workflow_service.transition_story.assert_awaited_once_with(story_id, StoryStatus.FAILED)


# ---------------------------------------------------------------------------
# 2. Shot planning orchestration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_calls_visual_planning_once_per_scene():
    story_id = str(uuid.uuid4())
    scenes = [make_scene(scene_number=1), make_scene(scene_number=2)]
    script = make_script(scenes=scenes)
    edit_plan = make_edit_plan(
        story_id,
        cuts=[
            SceneCut(scene_number=1, start_time=0.0, end_time=10.0),
            SceneCut(scene_number=2, start_time=10.0, end_time=20.0),
        ],
    )

    orchestrator, data = make_happy_path_orchestrator(
        story_id,
        repository=make_full_repository(story_id, script=script, edit_plan=edit_plan),
    )
    orchestrator._visual_planning_service.generate.return_value = make_shot_plan(story_id)

    await orchestrator.advance_to_assembly(story_id)

    assert orchestrator._visual_planning_service.generate.await_count == 2
    calls = orchestrator._visual_planning_service.generate.await_args_list
    assert calls[0].args == (story_id, scenes[0], data["dna"], edit_plan)
    assert calls[1].args == (story_id, scenes[1], data["dna"], edit_plan)


# ---------------------------------------------------------------------------
# 3. Dynamic per-shot visual generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_dispatches_image_shots_to_generate_image():
    story_id = str(uuid.uuid4())
    shot = Shot(
        shot_number=1, visual_prompt="a dark hallway", estimated_duration=10.0, asset_type="image"
    )
    shot_plan = make_shot_plan(story_id, shots=[shot])

    orchestrator, data = make_happy_path_orchestrator(story_id)
    orchestrator._visual_planning_service.generate.return_value = shot_plan

    await orchestrator.advance_to_assembly(story_id)

    orchestrator._visual_generation_service.generate_image.assert_awaited_once_with(
        story_id, 1, shot
    )
    orchestrator._visual_generation_service.generate_video.assert_not_awaited()


@pytest.mark.asyncio
async def test_advance_to_assembly_dispatches_video_shots_to_generate_video():
    story_id = str(uuid.uuid4())
    shot = Shot(
        shot_number=1, visual_prompt="a dark hallway", estimated_duration=10.0, asset_type="video"
    )
    shot_plan = make_shot_plan(story_id, shots=[shot])

    orchestrator, data = make_happy_path_orchestrator(story_id)
    orchestrator._visual_planning_service.generate.return_value = shot_plan

    await orchestrator.advance_to_assembly(story_id)

    orchestrator._visual_generation_service.generate_video.assert_awaited_once_with(
        story_id, 1, shot
    )
    orchestrator._visual_generation_service.generate_image.assert_not_awaited()


@pytest.mark.asyncio
async def test_advance_to_assembly_dispatches_mixed_shots_independently():
    story_id = str(uuid.uuid4())
    image_shot = Shot(
        shot_number=1, visual_prompt="a hallway", estimated_duration=4.0, asset_type="image"
    )
    video_shot = Shot(
        shot_number=2, visual_prompt="a door creaks open", estimated_duration=6.0, asset_type="video"
    )
    shot_plan = make_shot_plan(story_id, shots=[image_shot, video_shot])

    orchestrator, data = make_happy_path_orchestrator(story_id)
    orchestrator._visual_planning_service.generate.return_value = shot_plan

    await orchestrator.advance_to_assembly(story_id)

    orchestrator._visual_generation_service.generate_image.assert_awaited_once_with(
        story_id, 1, image_shot
    )
    orchestrator._visual_generation_service.generate_video.assert_awaited_once_with(
        story_id, 1, video_shot
    )


@pytest.mark.asyncio
async def test_advance_to_assembly_collects_all_visual_assets_for_assembly():
    story_id = str(uuid.uuid4())
    image_shot = Shot(
        shot_number=1, visual_prompt="a hallway", estimated_duration=4.0, asset_type="image"
    )
    video_shot = Shot(
        shot_number=2, visual_prompt="a door creaks open", estimated_duration=6.0, asset_type="video"
    )
    shot_plan = make_shot_plan(story_id, shots=[image_shot, video_shot])
    image_asset = make_visual_asset(story_id, shot_number=1, asset_type="image")
    video_asset = make_visual_asset(story_id, shot_number=2, asset_type="video")

    orchestrator, data = make_happy_path_orchestrator(story_id)
    orchestrator._visual_planning_service.generate.return_value = shot_plan
    orchestrator._visual_generation_service.generate_image.return_value = image_asset
    orchestrator._visual_generation_service.generate_video.return_value = video_asset

    await orchestrator.advance_to_assembly(story_id)

    assembled_visual_assets = orchestrator._assembly_service.assemble.await_args.args[3]
    assert assembled_visual_assets == [image_asset, video_asset]


# ---------------------------------------------------------------------------
# 4. Music planning
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_calls_music_planning_once_with_script_dna_edit_plan():
    story_id = str(uuid.uuid4())
    orchestrator, data = make_happy_path_orchestrator(story_id)

    await orchestrator.advance_to_assembly(story_id)

    orchestrator._music_planning_service.generate.assert_awaited_once_with(
        story_id, data["script"], data["dna"], data["edit_plan"]
    )


# ---------------------------------------------------------------------------
# 5. Per-cue music generation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_calls_music_generation_once_per_cue():
    story_id = str(uuid.uuid4())
    cues = [
        MusicCue(cue_number=1, start_time=0.0, end_time=5.0, mood="dread", music_prompt="drone 1"),
        MusicCue(cue_number=2, start_time=5.0, end_time=10.0, mood="panic", music_prompt="drone 2"),
    ]
    music_plan = make_music_plan(story_id, cues=cues)

    orchestrator, data = make_happy_path_orchestrator(story_id)
    orchestrator._music_planning_service.generate.return_value = music_plan

    await orchestrator.advance_to_assembly(story_id)

    assert orchestrator._music_generation_service.generate.await_count == 2
    calls = orchestrator._music_generation_service.generate.await_args_list
    assert calls[0].args == (story_id, cues[0])
    assert calls[1].args == (story_id, cues[1])


@pytest.mark.asyncio
async def test_advance_to_assembly_collects_all_music_assets_for_assembly():
    story_id = str(uuid.uuid4())
    cues = [
        MusicCue(cue_number=1, start_time=0.0, end_time=5.0, mood="dread", music_prompt="drone 1"),
        MusicCue(cue_number=2, start_time=5.0, end_time=10.0, mood="panic", music_prompt="drone 2"),
    ]
    music_plan = make_music_plan(story_id, cues=cues)
    asset_1 = make_music_asset(story_id, cue_number=1)
    asset_2 = make_music_asset(story_id, cue_number=2)

    orchestrator, data = make_happy_path_orchestrator(story_id)
    orchestrator._music_planning_service.generate.return_value = music_plan
    orchestrator._music_generation_service.generate.side_effect = [asset_1, asset_2]

    await orchestrator.advance_to_assembly(story_id)

    assembled_music_assets = orchestrator._assembly_service.assemble.await_args.args[4]
    assert assembled_music_assets == [asset_1, asset_2]


# ---------------------------------------------------------------------------
# 6. Assembly invocation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_calls_assembly_service_with_edit_plan_and_voice_track():
    story_id = str(uuid.uuid4())
    orchestrator, data = make_happy_path_orchestrator(story_id)

    await orchestrator.advance_to_assembly(story_id)

    call_args = orchestrator._assembly_service.assemble.await_args.args
    assert call_args[0] == story_id
    assert call_args[1] == data["edit_plan"]
    assert call_args[2] == data["voice_track"]


# ---------------------------------------------------------------------------
# 7. FinalTimeline persistence
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_resolves_visual_asset_ids_per_segment():
    story_id = str(uuid.uuid4())
    final_timeline = make_final_timeline(story_id)

    id_1 = uuid.uuid4()
    scene_asset_row = AsyncMock(id=id_1)

    visual_asset_repository = AsyncMock()
    visual_asset_repository.list_by_scene.return_value = [scene_asset_row]

    orchestrator, data = make_happy_path_orchestrator(
        story_id, visual_asset_repository=visual_asset_repository
    )
    orchestrator._assembly_service.assemble.return_value = final_timeline

    await orchestrator.advance_to_assembly(story_id)

    visual_asset_repository.list_by_scene.assert_awaited_once_with(story_id, 1)
    save_call = orchestrator._final_timeline_repository.save.await_args
    assert save_call.args[2] == [str(id_1)]


@pytest.mark.asyncio
async def test_advance_to_assembly_resolves_music_asset_ids_once_for_whole_story():
    story_id = str(uuid.uuid4())
    id_1 = uuid.uuid4()
    id_2 = uuid.uuid4()

    music_asset_repository = AsyncMock()
    music_asset_repository.list_by_story.return_value = [
        AsyncMock(id=id_1),
        AsyncMock(id=id_2),
    ]

    orchestrator, data = make_happy_path_orchestrator(
        story_id, music_asset_repository=music_asset_repository
    )

    await orchestrator.advance_to_assembly(story_id)

    music_asset_repository.list_by_story.assert_awaited_once_with(story_id)
    save_call = orchestrator._final_timeline_repository.save.await_args
    assert save_call.args[3] == [str(id_1), str(id_2)]


@pytest.mark.asyncio
async def test_advance_to_assembly_saves_final_timeline():
    story_id = str(uuid.uuid4())
    final_timeline = make_final_timeline(story_id)

    orchestrator, data = make_happy_path_orchestrator(story_id)
    orchestrator._assembly_service.assemble.return_value = final_timeline

    await orchestrator.advance_to_assembly(story_id)

    save_call = orchestrator._final_timeline_repository.save.await_args
    assert save_call.args[0] == story_id
    assert save_call.args[1] == final_timeline


# ---------------------------------------------------------------------------
# 8. Final transition EDITING -> RENDERING
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_transitions_to_rendering_on_success():
    story_id = str(uuid.uuid4())
    workflow_service = AsyncMock()

    orchestrator, data = make_happy_path_orchestrator(
        story_id, workflow_service=workflow_service
    )

    await orchestrator.advance_to_assembly(story_id)

    workflow_service.transition_story.assert_awaited_once_with(
        story_id, StoryStatus.RENDERING
    )


@pytest.mark.asyncio
async def test_advance_to_assembly_transitions_to_rendering_only_after_save():
    story_id = str(uuid.uuid4())
    call_order = []

    final_timeline_repository = AsyncMock()

    async def save_side_effect(*args, **kwargs):
        call_order.append("save_final_timeline")

    final_timeline_repository.save.side_effect = save_side_effect

    workflow_service = AsyncMock()

    async def transition_side_effect(sid, status):
        call_order.append(("transition", status))

    workflow_service.transition_story.side_effect = transition_side_effect

    orchestrator, data = make_happy_path_orchestrator(
        story_id,
        workflow_service=workflow_service,
        final_timeline_repository=final_timeline_repository,
    )

    await orchestrator.advance_to_assembly(story_id)

    assert call_order == ["save_final_timeline", ("transition", StoryStatus.RENDERING)]


# ---------------------------------------------------------------------------
# 9. Failure behavior
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_visual_planning_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    workflow_service = AsyncMock()

    orchestrator, data = make_happy_path_orchestrator(
        story_id, workflow_service=workflow_service
    )
    orchestrator._visual_planning_service.generate.side_effect = RuntimeError("visual planning failed")

    with pytest.raises(RuntimeError, match="visual planning failed"):
        await orchestrator.advance_to_assembly(story_id)

    workflow_service.transition_story.assert_awaited_once_with(story_id, StoryStatus.FAILED)


@pytest.mark.asyncio
async def test_advance_to_assembly_visual_generation_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    workflow_service = AsyncMock()

    orchestrator, data = make_happy_path_orchestrator(
        story_id, workflow_service=workflow_service
    )
    orchestrator._visual_generation_service.generate_image.side_effect = RuntimeError(
        "visual generation failed"
    )

    with pytest.raises(RuntimeError, match="visual generation failed"):
        await orchestrator.advance_to_assembly(story_id)

    workflow_service.transition_story.assert_awaited_once_with(story_id, StoryStatus.FAILED)


@pytest.mark.asyncio
async def test_advance_to_assembly_music_planning_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    workflow_service = AsyncMock()

    orchestrator, data = make_happy_path_orchestrator(
        story_id, workflow_service=workflow_service
    )
    orchestrator._music_planning_service.generate.side_effect = RuntimeError("music planning failed")

    with pytest.raises(RuntimeError, match="music planning failed"):
        await orchestrator.advance_to_assembly(story_id)

    workflow_service.transition_story.assert_awaited_once_with(story_id, StoryStatus.FAILED)


@pytest.mark.asyncio
async def test_advance_to_assembly_music_generation_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    workflow_service = AsyncMock()

    orchestrator, data = make_happy_path_orchestrator(
        story_id, workflow_service=workflow_service
    )
    orchestrator._music_generation_service.generate.side_effect = RuntimeError(
        "music generation failed"
    )

    with pytest.raises(RuntimeError, match="music generation failed"):
        await orchestrator.advance_to_assembly(story_id)

    workflow_service.transition_story.assert_awaited_once_with(story_id, StoryStatus.FAILED)


@pytest.mark.asyncio
async def test_advance_to_assembly_assembly_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    workflow_service = AsyncMock()

    orchestrator, data = make_happy_path_orchestrator(
        story_id, workflow_service=workflow_service
    )
    orchestrator._assembly_service.assemble.side_effect = RuntimeError("assembly failed")

    with pytest.raises(RuntimeError, match="assembly failed"):
        await orchestrator.advance_to_assembly(story_id)

    workflow_service.transition_story.assert_awaited_once_with(story_id, StoryStatus.FAILED)


@pytest.mark.asyncio
async def test_advance_to_assembly_save_final_timeline_failure_transitions_to_failed():
    story_id = str(uuid.uuid4())
    workflow_service = AsyncMock()
    final_timeline_repository = AsyncMock()
    final_timeline_repository.save.side_effect = RuntimeError("save final timeline failed")

    orchestrator, data = make_happy_path_orchestrator(
        story_id,
        workflow_service=workflow_service,
        final_timeline_repository=final_timeline_repository,
    )

    with pytest.raises(RuntimeError, match="save final timeline failed"):
        await orchestrator.advance_to_assembly(story_id)

    workflow_service.transition_story.assert_awaited_once_with(story_id, StoryStatus.FAILED)


@pytest.mark.asyncio
async def test_advance_to_assembly_failure_does_not_transition_to_rendering():
    story_id = str(uuid.uuid4())
    workflow_service = AsyncMock()

    orchestrator, data = make_happy_path_orchestrator(
        story_id, workflow_service=workflow_service
    )
    orchestrator._assembly_service.assemble.side_effect = RuntimeError("assembly failed")

    with pytest.raises(RuntimeError):
        await orchestrator.advance_to_assembly(story_id)

    rendering_calls = [
        call
        for call in workflow_service.transition_story.await_args_list
        if call.args[1] == StoryStatus.RENDERING
    ]
    assert rendering_calls == []


# ---------------------------------------------------------------------------
# 10. Ordering guarantees
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_advance_to_assembly_runs_full_pipeline_in_order():
    story_id = str(uuid.uuid4())
    call_order = []

    dna = make_story_dna(story_id)
    script = make_script()
    edit_plan = make_edit_plan(story_id)
    voice_track = make_voice_track(story_id)
    shot_plan = make_shot_plan(story_id)
    visual_asset = make_visual_asset(story_id)
    music_plan = make_music_plan(story_id)
    music_asset = make_music_asset(story_id)
    final_timeline = make_final_timeline(story_id)

    repository = AsyncMock()

    async def get_dna_side_effect(sid):
        call_order.append("get_dna")
        return dna

    async def get_script_side_effect(sid):
        call_order.append("get_script")
        return script

    async def get_edit_plan_side_effect(sid):
        call_order.append("get_edit_plan")
        return edit_plan

    async def get_voice_track_side_effect(sid):
        call_order.append("get_voice_track")
        return voice_track

    repository.get_dna.side_effect = get_dna_side_effect
    repository.get_script.side_effect = get_script_side_effect
    repository.get_edit_plan.side_effect = get_edit_plan_side_effect
    repository.get_voice_track.side_effect = get_voice_track_side_effect

    visual_planning_service = AsyncMock()

    async def visual_planning_side_effect(sid, scene, story_dna, ep):
        call_order.append("visual_planning")
        return shot_plan

    visual_planning_service.generate.side_effect = visual_planning_side_effect

    visual_generation_service = AsyncMock()

    async def generate_image_side_effect(sid, scene_number, shot):
        call_order.append("generate_image")
        return visual_asset

    visual_generation_service.generate_image.side_effect = generate_image_side_effect

    music_planning_service = AsyncMock()

    async def music_planning_side_effect(sid, s, story_dna, ep):
        call_order.append("music_planning")
        return music_plan

    music_planning_service.generate.side_effect = music_planning_side_effect

    music_generation_service = AsyncMock()

    async def music_generation_side_effect(sid, cue):
        call_order.append("music_generation")
        return music_asset

    music_generation_service.generate.side_effect = music_generation_side_effect

    assembly_service = AsyncMock()

    async def assemble_side_effect(sid, ep, vt, visual_assets, music_assets):
        call_order.append("assembly")
        return final_timeline

    assembly_service.assemble.side_effect = assemble_side_effect

    visual_asset_repository = AsyncMock()

    async def list_by_scene_side_effect(sid, scene_number):
        call_order.append("list_by_scene")
        return []

    visual_asset_repository.list_by_scene.side_effect = list_by_scene_side_effect

    music_asset_repository = AsyncMock()

    async def list_by_story_side_effect(sid):
        call_order.append("list_by_story")
        return []

    music_asset_repository.list_by_story.side_effect = list_by_story_side_effect

    final_timeline_repository = AsyncMock()

    async def save_side_effect(sid, timeline, visual_ids, music_ids):
        call_order.append("save_final_timeline")

    final_timeline_repository.save.side_effect = save_side_effect

    workflow_service = AsyncMock()

    async def transition_side_effect(sid, status):
        call_order.append(("transition", status))

    workflow_service.transition_story.side_effect = transition_side_effect

    orchestrator = make_orchestrator(
        workflow_service=workflow_service,
        repository=repository,
        visual_planning_service=visual_planning_service,
        visual_generation_service=visual_generation_service,
        music_planning_service=music_planning_service,
        music_generation_service=music_generation_service,
        assembly_service=assembly_service,
        visual_asset_repository=visual_asset_repository,
        music_asset_repository=music_asset_repository,
        final_timeline_repository=final_timeline_repository,
    )

    await orchestrator.advance_to_assembly(story_id)

    assert call_order == [
        "get_dna",
        "get_script",
        "get_edit_plan",
        "get_voice_track",
        "visual_planning",
        "generate_image",
        "music_planning",
        "music_generation",
        "assembly",
        "list_by_scene",
        "list_by_story",
        "save_final_timeline",
        ("transition", StoryStatus.RENDERING),
    ]
