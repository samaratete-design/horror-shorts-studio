import pytest

from shared_types.edit_plan import EditPlan, SceneCut
from shared_types.voice_track import VoiceTrack, VoiceSegment
from shared_types.visual_asset import VisualAsset
from shared_types.music_asset import MusicAsset
from shared_types.final_timeline import FinalTimeline, FinalSegment

from app.services.assembly_service import (
    InvalidAssemblyRequestError,
    AssemblyError,
    AssemblyService,
)


def make_edit_plan(story_id="story-1"):
    return EditPlan(
        story_id=story_id,
        total_duration=25.0,
        cuts=[
            SceneCut(scene_number=1, start_time=0.0, end_time=10.0),
            SceneCut(scene_number=2, start_time=10.0, end_time=20.0),
            SceneCut(scene_number=3, start_time=20.0, end_time=25.0),
        ],
    )


def make_voice_track(story_id="story-1"):
    return VoiceTrack(
        story_id=story_id,
        segments=[
            # Scene 1: actual voice total = 8.11 (last end_time)
            VoiceSegment(scene_number=1, speaker="narrator", start_time=0.0, end_time=3.42, audio=b"a"),
            VoiceSegment(scene_number=1, speaker="Man", start_time=3.42, end_time=8.11, audio=b"a"),
            # Scene 2: actual voice total = 11.0
            VoiceSegment(scene_number=2, speaker="narrator", start_time=0.0, end_time=11.0, audio=b"a"),
            # Scene 3: NO voice segments at all
        ],
    )


def make_visual_assets(story_id="story-1"):
    return [
        # Scene 1: one video, actual_duration=9.5 (> voice's 8.11) -> visual wins
        VisualAsset(story_id=story_id, scene_number=1, shot_number=1, asset_type="video", asset=b"v", actual_duration=9.5),
        # Scene 2: only an image (no actual_duration) -> ignored, voice wins
        VisualAsset(story_id=story_id, scene_number=2, shot_number=1, asset_type="image", asset=b"i", actual_duration=None),
        # Scene 3: NO visual assets at all
    ]


def make_music_assets(story_id="story-1"):
    return [
        MusicAsset(story_id=story_id, cue_number=1, asset=b"m1", actual_duration=6.8),
    ]


# 1. Invalid request
@pytest.mark.asyncio
async def test_assemble_rejects_none_edit_plan():
    service = AssemblyService()
    with pytest.raises(InvalidAssemblyRequestError):
        await service.assemble(
            story_id="story-1", edit_plan=None, voice_track=make_voice_track(),
            visual_assets=make_visual_assets(), music_assets=make_music_assets(),
        )


@pytest.mark.asyncio
async def test_assemble_rejects_none_voice_track():
    service = AssemblyService()
    with pytest.raises(InvalidAssemblyRequestError):
        await service.assemble(
            story_id="story-1", edit_plan=make_edit_plan(), voice_track=None,
            visual_assets=make_visual_assets(), music_assets=make_music_assets(),
        )


# 2. Identity — mismatched story_id anywhere is rejected
@pytest.mark.asyncio
async def test_assemble_rejects_edit_plan_story_id_mismatch():
    service = AssemblyService()
    with pytest.raises(AssemblyError):
        await service.assemble(
            story_id="story-1", edit_plan=make_edit_plan(story_id="wrong"),
            voice_track=make_voice_track(), visual_assets=make_visual_assets(),
            music_assets=make_music_assets(),
        )


@pytest.mark.asyncio
async def test_assemble_rejects_visual_asset_story_id_mismatch():
    service = AssemblyService()
    bad_assets = make_visual_assets()
    bad_assets[0] = VisualAsset(
        story_id="wrong", scene_number=1, shot_number=1,
        asset_type="video", asset=b"v", actual_duration=9.5,
    )
    with pytest.raises(AssemblyError):
        await service.assemble(
            story_id="story-1", edit_plan=make_edit_plan(), voice_track=make_voice_track(),
            visual_assets=bad_assets, music_assets=make_music_assets(),
        )


# 3. Reconciliation: max(actual_voice, actual_visual), fallback to planned when both absent
@pytest.mark.asyncio
async def test_assemble_reconciles_scene_durations_correctly():
    service = AssemblyService()

    result = await service.assemble(
        story_id="story-1",
        edit_plan=make_edit_plan(),
        voice_track=make_voice_track(),
        visual_assets=make_visual_assets(),
        music_assets=make_music_assets(),
    )

    assert isinstance(result, FinalTimeline)
    assert result.story_id == "story-1"

    # Scene 1: visual (9.5) beats voice (8.11)
    assert result.segments[0].scene_number == 1
    assert result.segments[0].start_time == pytest.approx(0.0)
    assert result.segments[0].end_time == pytest.approx(9.5)

    # Scene 2: only voice counts (image has no actual_duration) -> 11.0, cumulative from scene 1's end
    assert result.segments[1].scene_number == 2
    assert result.segments[1].start_time == pytest.approx(9.5)
    assert result.segments[1].end_time == pytest.approx(9.5 + 11.0)

    # Scene 3: no voice, no visual -> falls back to planned duration (5.0)
    assert result.segments[2].scene_number == 3
    assert result.segments[2].end_time - result.segments[2].start_time == pytest.approx(5.0)

    # total_duration = cumulative end of last segment
    assert result.total_duration == pytest.approx(result.segments[-1].end_time)


# 4. Sequential, non-overlapping
@pytest.mark.asyncio
async def test_assemble_produces_sequential_non_overlapping_segments():
    service = AssemblyService()
    result = await service.assemble(
        story_id="story-1", edit_plan=make_edit_plan(), voice_track=make_voice_track(),
        visual_assets=make_visual_assets(), music_assets=make_music_assets(),
    )
    for i in range(len(result.segments) - 1):
        assert result.segments[i].end_time == result.segments[i + 1].start_time


# 5. Music assets pass through unchanged
@pytest.mark.asyncio
async def test_assemble_passes_through_music_assets_unchanged():
    service = AssemblyService()
    music = make_music_assets()
    result = await service.assemble(
        story_id="story-1", edit_plan=make_edit_plan(), voice_track=make_voice_track(),
        visual_assets=make_visual_assets(), music_assets=music,
    )
    assert result.music_assets == music
