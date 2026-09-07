from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.rendering_service import (
    RenderingService,
    MissingRenderingInputError,
)
from shared_types.final_timeline import FinalTimeline, FinalSegment
from shared_types.music_asset import MusicAsset
from shared_types.voice_track import VoiceTrack, VoiceSegment


def make_timeline(story_id="story-1"):
    return FinalTimeline(
        story_id=story_id,
        total_duration=10.0,
        segments=[FinalSegment(scene_number=1, start_time=0.0, end_time=10.0)],
        music_assets=[MusicAsset(story_id=story_id, cue_number=1, asset=b"music", actual_duration=10.0)],
    )


def make_final_timeline_model(story_id="story-1"):
    return SimpleNamespace(
        story_id=story_id,
        total_duration=10.0,
        segments=[{"scene_number": 1, "start_time": 0.0, "end_time": 10.0}],
        visual_asset_ids=["visual-1"],
        music_asset_ids=["music-1"],
    )


def make_voice_track(story_id="story-1"):
    return VoiceTrack(
        story_id=story_id,
        segments=[
            VoiceSegment(
                scene_number=1,
                speaker="narrator",
                audio=b"voice-bytes",
                start_time=0.0,
                end_time=5.0,
            )
        ],
    )


def make_visual_asset_row():
    return SimpleNamespace(
        id="visual-1",
        scene_number=1,
        shot_number=1,
        asset_type="video",
        storage_key="visual-key-1",
        actual_duration=5.0,
    )


def make_music_asset_row():
    return SimpleNamespace(
        id="music-1",
        cue_number=1,
        storage_key="music-key-1",
        actual_duration=10.0,
    )


import os

def _default_output_dir():
    return os.path.join(os.path.expanduser("~"), ".rendering_test_tmp")


def make_service(
    final_timeline_repository=None,
    story_repository=None,
    visual_asset_repository=None,
    music_asset_repository=None,
    asset_storage=None,
    ffmpeg_runner=None,
    output_dir=None,
):
    output_dir = output_dir or _default_output_dir()
    return RenderingService(
        final_timeline_repository=final_timeline_repository or MagicMock(),
        story_repository=story_repository or MagicMock(),
        visual_asset_repository=visual_asset_repository or MagicMock(),
        music_asset_repository=music_asset_repository or MagicMock(),
        asset_storage=asset_storage or MagicMock(),
        ffmpeg_runner=ffmpeg_runner or MagicMock(),
        output_dir=output_dir,
    )


def make_happy_dependencies():
    final_timeline_repository = MagicMock()
    final_timeline_repository.get = AsyncMock(return_value=make_final_timeline_model())

    story_repository = MagicMock()
    story_repository.get_voice_track = AsyncMock(return_value=make_voice_track())

    visual_asset_repository = MagicMock()
    visual_asset_repository.get_by_id = AsyncMock(return_value=make_visual_asset_row())

    music_asset_repository = MagicMock()
    music_asset_repository.get_by_id = AsyncMock(return_value=make_music_asset_row())

    asset_storage = MagicMock()
    asset_storage.load = AsyncMock(side_effect=lambda key: f"bytes-for-{key}".encode())

    ffmpeg_runner = MagicMock()
    ffmpeg_runner.run = AsyncMock(return_value=None)

    return {
        "final_timeline_repository": final_timeline_repository,
        "story_repository": story_repository,
        "visual_asset_repository": visual_asset_repository,
        "music_asset_repository": music_asset_repository,
        "asset_storage": asset_storage,
        "ffmpeg_runner": ffmpeg_runner,
    }


@pytest.mark.asyncio
async def test_render_raises_when_timeline_missing():
    final_timeline_repository = MagicMock()
    final_timeline_repository.get = AsyncMock(return_value=None)
    service = make_service(final_timeline_repository=final_timeline_repository)

    with pytest.raises(MissingRenderingInputError):
        await service.render("story-1")


@pytest.mark.asyncio
async def test_render_raises_when_voice_track_missing():
    deps = make_happy_dependencies()
    deps["story_repository"].get_voice_track = AsyncMock(return_value=None)
    service = make_service(**deps)

    with pytest.raises(MissingRenderingInputError):
        await service.render("story-1")


@pytest.mark.asyncio
async def test_render_raises_when_visual_asset_missing():
    deps = make_happy_dependencies()
    deps["visual_asset_repository"].get_by_id = AsyncMock(return_value=None)
    service = make_service(**deps)

    with pytest.raises(MissingRenderingInputError):
        await service.render("story-1")


@pytest.mark.asyncio
async def test_render_raises_when_music_asset_missing():
    deps = make_happy_dependencies()
    deps["music_asset_repository"].get_by_id = AsyncMock(return_value=None)
    service = make_service(**deps)

    with pytest.raises(MissingRenderingInputError):
        await service.render("story-1")


@pytest.mark.asyncio
async def test_render_loads_visual_asset_bytes_via_asset_storage():
    deps = make_happy_dependencies()
    service = make_service(**deps)

    await service.render("story-1")

    deps["asset_storage"].load.assert_any_call("visual-key-1")


@pytest.mark.asyncio
async def test_render_loads_music_asset_bytes_via_asset_storage():
    deps = make_happy_dependencies()
    service = make_service(**deps)

    await service.render("story-1")

    deps["asset_storage"].load.assert_any_call("music-key-1")


@pytest.mark.asyncio
async def test_render_invokes_ffmpeg_runner_exactly_once():
    deps = make_happy_dependencies()
    service = make_service(**deps)

    await service.render("story-1")

    deps["ffmpeg_runner"].run.assert_awaited_once()


@pytest.mark.asyncio
async def test_render_returns_mp4_path_under_output_dir():
    deps = make_happy_dependencies()
    output_dir = _default_output_dir()
    service = make_service(output_dir=output_dir, **deps)

    result = await service.render("story-1")

    assert result.startswith(output_dir)
    assert result.endswith(".mp4")
