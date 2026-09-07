import pytest

from shared_types.shot_plan import Shot

from app.services.visual_generation_service import (
    InvalidVisualGenerationRequestError,
    VisualGenerationError,
    VisualGenerationService,
)
from provider_abstractions.interfaces import GeneratedVideo


class FakeImageProvider:
    def __init__(self):
        self.calls = []

    async def generate(self, prompt: str, aspect_ratio: str = "9:16") -> bytes:
        self.calls.append((prompt, aspect_ratio))
        return b"image-bytes"


class FakeVideoProvider:
    def __init__(self, result=None, error=None):
        self.calls = []
        self.result = result
        self.error = error

    async def generate(self, prompt: str, duration_seconds: float) -> GeneratedVideo:
        self.calls.append((prompt, duration_seconds))

        if self.error:
            raise self.error

        return self.result


def make_shot(
    shot_number: int = 1,
    prompt: str = "dark realistic horror scene",
    duration: float = 6.0,
    asset_type: str = "image",
) -> Shot:
    return Shot(
        shot_number=shot_number,
        visual_prompt=prompt,
        estimated_duration=duration,
        asset_type=asset_type,
    )


@pytest.mark.asyncio
async def test_generates_image_asset_with_identity():
    provider = FakeImageProvider()

    service = VisualGenerationService(
        image_provider=provider,
        video_provider=None,
    )

    result = await service.generate_image(
        story_id="story-1",
        scene_number=2,
        shot=make_shot(),
    )

    assert result.story_id == "story-1"
    assert result.scene_number == 2
    assert result.shot_number == 1
    assert result.asset_type == "image"
    assert result.asset == b"image-bytes"
    assert result.actual_duration is None


@pytest.mark.asyncio
async def test_image_generation_delegates_prompt_and_default_aspect_ratio():
    provider = FakeImageProvider()

    service = VisualGenerationService(
        image_provider=provider,
        video_provider=None,
    )

    await service.generate_image(
        story_id="story-1",
        scene_number=2,
        shot=make_shot(prompt="cinematic abandoned hallway"),
    )

    assert provider.calls == [
        ("cinematic abandoned hallway", "9:16")
    ]


@pytest.mark.asyncio
async def test_generates_video_asset_with_actual_duration():
    provider = FakeVideoProvider(
        result=GeneratedVideo(
            video=b"video-bytes",
            duration=5.37,
        )
    )

    service = VisualGenerationService(
        image_provider=None,
        video_provider=provider,
    )

    result = await service.generate_video(
        story_id="story-1",
        scene_number=3,
        shot=make_shot(duration=6.0),
    )

    assert result.story_id == "story-1"
    assert result.scene_number == 3
    assert result.shot_number == 1
    assert result.asset_type == "video"
    assert result.asset == b"video-bytes"
    assert result.actual_duration == 5.37


@pytest.mark.asyncio
async def test_video_generation_passes_estimated_duration_as_requested_duration():
    provider = FakeVideoProvider(
        result=GeneratedVideo(
            video=b"video-bytes",
            duration=5.37,
        )
    )

    service = VisualGenerationService(
        image_provider=None,
        video_provider=provider,
    )

    await service.generate_video(
        story_id="story-1",
        scene_number=3,
        shot=make_shot(duration=6.0),
    )

    assert provider.calls == [
        ("dark realistic horror scene", 6.0)
    ]


@pytest.mark.asyncio
async def test_image_provider_failure_is_wrapped():
    provider = FakeImageProvider()

    async def failing_generate(prompt: str, aspect_ratio: str = "9:16") -> bytes:
        raise RuntimeError("provider failed")

    provider.generate = failing_generate

    service = VisualGenerationService(
        image_provider=provider,
        video_provider=None,
    )

    with pytest.raises(VisualGenerationError):
        await service.generate_image(
            story_id="story-1",
            scene_number=1,
            shot=make_shot(),
        )


@pytest.mark.asyncio
async def test_video_provider_failure_is_wrapped():
    provider = FakeVideoProvider(
        error=RuntimeError("provider failed")
    )

    service = VisualGenerationService(
        image_provider=None,
        video_provider=provider,
    )

    with pytest.raises(VisualGenerationError):
        await service.generate_video(
            story_id="story-1",
            scene_number=1,
            shot=make_shot(),
        )


@pytest.mark.asyncio
async def test_none_shot_is_rejected():
    service = VisualGenerationService(
        image_provider=FakeImageProvider(),
        video_provider=FakeVideoProvider(),
    )

    with pytest.raises(InvalidVisualGenerationRequestError):
        await service.generate_image(
            story_id="story-1",
            scene_number=1,
            shot=None,
        )


@pytest.mark.asyncio
async def test_none_story_id_is_rejected():
    service = VisualGenerationService(
        image_provider=FakeImageProvider(),
        video_provider=None,
    )

    with pytest.raises(InvalidVisualGenerationRequestError):
        await service.generate_image(
            story_id=None,
            scene_number=1,
            shot=make_shot(),
        )


@pytest.mark.asyncio
async def test_visual_asset_does_not_own_timeline():
    provider = FakeImageProvider()

    service = VisualGenerationService(
        image_provider=provider,
        video_provider=None,
    )

    result = await service.generate_image(
        story_id="story-1",
        scene_number=1,
        shot=make_shot(),
    )

    assert not hasattr(result, "start_time")
    assert not hasattr(result, "end_time")
