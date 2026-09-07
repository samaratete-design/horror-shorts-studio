import pytest

from shared_types.music_plan import MusicCue
from shared_types.music_asset import MusicAsset

from provider_abstractions.interfaces import MusicProvider, GeneratedMusic

from app.services.music_generation_service import (
    InvalidMusicGenerationRequestError,
    MusicGenerationError,
    MusicGenerationService,
)


def make_cue(cue_number: int = 1, start: float = 0.0, end: float = 7.0) -> MusicCue:
    return MusicCue(
        cue_number=cue_number,
        start_time=start,
        end_time=end,
        mood="rising_dread",
        music_prompt="low drone",
    )


class FakeMusicProvider(MusicProvider):
    def __init__(self, generated: GeneratedMusic):
        self.generated = generated
        self.calls: list[tuple] = []

    async def generate(self, prompt: str, duration_seconds: float) -> GeneratedMusic:
        self.calls.append((prompt, duration_seconds))
        return self.generated


class FailingMusicProvider(MusicProvider):
    async def generate(self, prompt: str, duration_seconds: float) -> GeneratedMusic:
        raise RuntimeError("music model unavailable")


# 1. Invalid request — rejected before provider is called
@pytest.mark.asyncio
async def test_generate_rejects_empty_story_id_without_calling_provider():
    provider = FakeMusicProvider(GeneratedMusic(audio=b"x", duration=7.0))
    service = MusicGenerationService(provider)

    with pytest.raises(InvalidMusicGenerationRequestError):
        await service.generate(story_id="", cue=make_cue())

    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_rejects_none_cue_without_calling_provider():
    provider = FakeMusicProvider(GeneratedMusic(audio=b"x", duration=7.0))
    service = MusicGenerationService(provider)

    with pytest.raises(InvalidMusicGenerationRequestError):
        await service.generate(story_id="story-1", cue=None)

    assert provider.calls == []


# 2. Provider failure wrapped
@pytest.mark.asyncio
async def test_generate_wraps_provider_failure():
    service = MusicGenerationService(FailingMusicProvider())

    with pytest.raises(MusicGenerationError) as exc_info:
        await service.generate(story_id="story-1", cue=make_cue())

    assert isinstance(exc_info.value.__cause__, RuntimeError)


# 3. Correct delegation: prompt + planned duration (end_time - start_time)
@pytest.mark.asyncio
async def test_generate_delegates_with_prompt_and_planned_duration():
    cue = make_cue(start=3.0, end=10.0)  # planned duration = 7.0
    provider = FakeMusicProvider(GeneratedMusic(audio=b"audio-bytes", duration=6.8))
    service = MusicGenerationService(provider)

    await service.generate(story_id="story-1", cue=cue)

    assert len(provider.calls) == 1
    assert provider.calls[0] == ("low drone", 7.0)


# 4. Result shape: MusicAsset built from service-known story_id/cue_number
#    and provider's actual audio/duration — no start_time/end_time
@pytest.mark.asyncio
async def test_generate_returns_music_asset_with_actual_duration_and_identity():
    cue = make_cue(cue_number=2, start=3.0, end=10.0)
    provider = FakeMusicProvider(GeneratedMusic(audio=b"exact-audio-bytes", duration=6.8))
    service = MusicGenerationService(provider)

    result = await service.generate(story_id="story-1", cue=cue)

    assert isinstance(result, MusicAsset)
    assert result.story_id == "story-1"
    assert result.cue_number == 2
    assert result.asset == b"exact-audio-bytes"
    assert result.actual_duration == pytest.approx(6.8)  # actual, NOT the planned 7.0
    assert not hasattr(result, "start_time")
    assert not hasattr(result, "end_time")
