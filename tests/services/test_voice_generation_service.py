from unittest.mock import AsyncMock

import pytest

from shared_types.structured_script import StructuredScript, SceneItem, DialogueLine
from shared_types.voice_track import VoiceTrack
from provider_abstractions.interfaces import VoiceProvider, GeneratedAudio

from app.services.voice_generation_service import (
    InvalidVoiceRequestError,
    VoiceGenerationError,
    VoiceGenerationService,
)


def make_script() -> StructuredScript:
    return StructuredScript(
        title="Test Script",
        logline="A test script.",
        tone="dread",
        language="ar",
        estimated_duration=30.0,
        scenes=[
            SceneItem(
                scene_number=1,
                purpose="establish isolation",
                location="empty apartment",
                time_of_day="night",
                characters=["Man"],
                action="He stares at his phone.",
                dialogue=[
                    DialogueLine(character="Man", line="Who's there?", emotion="fear"),
                    DialogueLine(character="Man", line="I know you're here.", emotion="anger"),
                ],
                narration="He had been alone for hours.",
                emotion="dread",
                estimated_duration=15.0,
            ),
        ],
    )


class FakeVoiceProvider(VoiceProvider):
    def __init__(self, audio_to_return: bytes = b"fake-audio", duration: float = 1.0):
        self.audio_to_return = audio_to_return
        self.duration = duration
        self.calls: list[tuple[str, str]] = []

    async def generate(self, text: str, voice: str) -> GeneratedAudio:
        self.calls.append((text, voice))
        return GeneratedAudio(audio=self.audio_to_return, duration=self.duration)


class FailingVoiceProvider(VoiceProvider):
    async def generate(self, text: str, voice: str) -> GeneratedAudio:
        raise RuntimeError("TTS engine unavailable")


class SequencedVoiceProvider(VoiceProvider):
    """Returns a different duration per call, in order — for timeline tests."""
    def __init__(self, durations: list[float], audio: bytes = b"a"):
        self.durations = durations
        self.audio = audio
        self.calls: list[tuple[str, str]] = []

    async def generate(self, text: str, voice: str) -> GeneratedAudio:
        idx = len(self.calls)
        self.calls.append((text, voice))
        return GeneratedAudio(audio=self.audio, duration=self.durations[idx])


# 1. Provider failure
@pytest.mark.asyncio
async def test_generate_wraps_provider_failure():
    service = VoiceGenerationService(FailingVoiceProvider())

    with pytest.raises(VoiceGenerationError) as exc_info:
        await service.generate(story_id="story-1", script=make_script())

    assert isinstance(exc_info.value.__cause__, RuntimeError)


# 2. Invalid request
@pytest.mark.asyncio
async def test_generate_rejects_empty_story_id_without_calling_provider():
    provider = FakeVoiceProvider()
    service = VoiceGenerationService(provider)
    with pytest.raises(InvalidVoiceRequestError):
        await service.generate(story_id="", script=make_script())

    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_rejects_none_script_without_calling_provider():
    provider = FakeVoiceProvider()
    service = VoiceGenerationService(provider)
    with pytest.raises(InvalidVoiceRequestError):
        await service.generate(story_id="story-1", script=None)

    assert provider.calls == []


@pytest.mark.asyncio
async def test_generate_rejects_script_with_no_scenes():
    provider = FakeVoiceProvider()
    service = VoiceGenerationService(provider)
    empty_script = StructuredScript(
        title="Empty", logline="x", tone="dread", language="ar",
        estimated_duration=0.0, scenes=[],
    )
    with pytest.raises(InvalidVoiceRequestError):
        await service.generate(story_id="story-1", script=empty_script)

    assert provider.calls == []


# 3. Provider called once per segment (narration + each dialogue line)
@pytest.mark.asyncio
async def test_generate_calls_provider_once_per_narration_and_dialogue_line():
    provider = FakeVoiceProvider()
    service = VoiceGenerationService(provider)

    await service.generate(story_id="story-1", script=make_script())

    # 1 narration + 2 dialogue lines = 3 calls
    assert len(provider.calls) == 3
    assert provider.calls[0] == ("He had been alone for hours.", "narrator_voice_dread")
    assert provider.calls[1] == ("Who's there?", "default_voice_fear")
    assert provider.calls[2] == ("I know you're here.", "default_voice_anger")


# 4. Result integrity
@pytest.mark.asyncio
async def test_generate_preserves_provider_audio_bytes_unchanged():
    expected_audio = b"exact-provider-bytes"
    provider = FakeVoiceProvider(audio_to_return=expected_audio)
    service = VoiceGenerationService(provider)

    track = await service.generate(story_id="story-1", script=make_script())

    assert isinstance(track, VoiceTrack)
    assert track.story_id == "story-1"
    assert all(seg.audio == expected_audio for seg in track.segments)
    assert track.segments[0].speaker == "narrator"
    assert track.segments[1].speaker == "Man"
    assert track.segments[2].speaker == "Man"
    assert track.segments[0].scene_number == 1


# 5. Provider isolation
@pytest.mark.asyncio
async def test_service_works_end_to_end_with_fake_provider_only():
    provider = FakeVoiceProvider()
    service = VoiceGenerationService(provider)

    track = await service.generate(story_id="story-99", script=make_script())

    assert isinstance(track, VoiceTrack)
    assert len(track.segments) == 3


# 6. Scene with narration=None
@pytest.mark.asyncio
async def test_generate_skips_narrator_when_narration_is_none():
    provider = FakeVoiceProvider()
    service = VoiceGenerationService(provider)
    script = StructuredScript(
        title="No Narration",
        logline="x",
        tone="dread",
        language="ar",
        estimated_duration=10.0,
        scenes=[
            SceneItem(
                scene_number=1,
                purpose="dialogue only",
                location="street",
                time_of_day="night",
                characters=["Woman"],
                action="She runs.",
                dialogue=[
                    DialogueLine(character="Woman", line="Help!", emotion="fear"),
                ],
                narration=None,
                emotion="dread",
                estimated_duration=5.0,
            ),
        ],
    )

    track = await service.generate(story_id="story-1", script=script)

    assert len(provider.calls) == 1
    assert provider.calls[0] == ("Help!", "default_voice_fear")
    assert all(seg.speaker != "narrator" for seg in track.segments)


# 7. Multi-scene ordering and scene_number integrity
@pytest.mark.asyncio
async def test_generate_preserves_scene_order_and_scene_numbers_across_multiple_scenes():
    provider = FakeVoiceProvider()
    service = VoiceGenerationService(provider)
    script = StructuredScript(
        title="Two Scenes",
        logline="x",
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
                dialogue=[
                    DialogueLine(character="Man", line="Hello?", emotion="fear"),
                ],
                narration="Scene one narration.",
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
                dialogue=[
                    DialogueLine(character="Man", line="No!", emotion="terror"),
                ],
                narration="Scene two narration.",
                emotion="terror",
                estimated_duration=10.0,
            ),
        ],
    )

    track = await service.generate(story_id="story-1", script=script)

    assert len(provider.calls) == 4
    assert provider.calls[0] == ("Scene one narration.", "narrator_voice_dread")
    assert provider.calls[1] == ("Hello?", "default_voice_fear")
    assert provider.calls[2] == ("Scene two narration.", "narrator_voice_terror")
    assert provider.calls[3] == ("No!", "default_voice_terror")

    assert [seg.scene_number for seg in track.segments] == [1, 1, 2, 2]


# RED #1 — VoiceSegment timing contract
def test_voice_segment_requires_timing():
    from shared_types.voice_track import VoiceSegment

    with pytest.raises(TypeError):
        VoiceSegment(
            scene_number=1,
            speaker="narrator",
            audio=b"audio",
        )


# RED #2 — GeneratedAudio contract
def test_generated_audio_is_frozen_and_holds_duration():
    ga = GeneratedAudio(audio=b"x", duration=1.5)
    assert ga.audio == b"x"
    assert ga.duration == 1.5
    with pytest.raises(Exception):
        ga.duration = 2.0  # frozen -> should raise


# RED #3 — cumulative timeline per scene, reset at scene boundary
@pytest.mark.asyncio
async def test_generate_builds_cumulative_timeline_per_scene_and_resets_at_boundary():
    # scene 1: narration(3.42) -> dialogue(2.45) -> dialogue(2.24)
    # scene 2: narration(2.96) -> dialogue(3.24)
    provider = SequencedVoiceProvider(durations=[3.42, 2.45, 2.24, 2.96, 3.24])
    service = VoiceGenerationService(provider)
    script = StructuredScript(
        title="Timeline Test",
        logline="x",
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
                dialogue=[
                    DialogueLine(character="Man", line="Who's there?", emotion="fear"),
                    DialogueLine(character="Man", line="I know you're here.", emotion="anger"),
                ],
                narration="He had been alone for hours.",
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
                dialogue=[
                    DialogueLine(character="Man", line="No!", emotion="terror"),
                ],
                narration="Scene two narration.",
                emotion="terror",
                estimated_duration=10.0,
            ),
        ],
    )

    track = await service.generate(story_id="story-1", script=script)

    scene1 = [s for s in track.segments if s.scene_number == 1]
    scene2 = [s for s in track.segments if s.scene_number == 2]

    # Scene 1 timeline, cumulative from 0.0
    assert scene1[0].start_time == pytest.approx(0.0)
    assert scene1[0].end_time == pytest.approx(3.42)
    assert scene1[1].start_time == pytest.approx(3.42)
    assert scene1[1].end_time == pytest.approx(5.87)
    assert scene1[2].start_time == pytest.approx(5.87)
    assert scene1[2].end_time == pytest.approx(8.11)

    # Scene 2 timeline MUST reset to 0.0 — not continue from scene 1
    assert scene2[0].start_time == pytest.approx(0.0)
    assert scene2[0].end_time == pytest.approx(2.96)
    assert scene2[1].start_time == pytest.approx(2.96)
    assert scene2[1].end_time == pytest.approx(6.20)
