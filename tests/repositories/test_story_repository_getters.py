import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.story_repository import StoryRepository
from app.models.story import Story as SQLStory
from app.models.story import StoryStatus as SQLStoryStatus
from app.models.story import StoryDNAModel, ScriptModel, EditPlanModel, VoiceTrackModel

from shared_types.story_dna import StoryDNA
from shared_types.structured_script import StructuredScript
from shared_types.edit_plan import EditPlan
from shared_types.voice_track import VoiceTrack


async def make_story(db_session: AsyncSession) -> uuid.UUID:
    story_id = uuid.uuid4()
    db_story = SQLStory(
        id=story_id,
        title="Test Horror Short",
        status=SQLStoryStatus.DRAFT,
        original_idea="Test idea",
        language="ar",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(db_story)
    await db_session.commit()
    return story_id


# --- get_dna ---

@pytest.mark.asyncio
async def test_get_dna_returns_none_when_no_dna_exists(db_session: AsyncSession):
    story_id = await make_story(db_session)
    repo = StoryRepository(db_session)

    result = await repo.get_dna(story_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_dna_returns_story_dna(db_session: AsyncSession):
    story_id = await make_story(db_session)

    db_dna = StoryDNAModel(
        story_id=story_id,
        premise="A man receives calls from himself.",
        setting="empty apartment",
        threat="a version of himself from the future",
        fear_mechanism="loss of control over one's own timeline",
        narrative_device="phone calls",
        twist_type="time_loop",
        ending_type="cliffhanger",
        pov="first_person",
        conflict="man vs his own future self",
        emotional_theme="paranoia",
        core_fear="losing agency over your own life",
        unique_story_hook="the calls get closer together each time",
    )
    db_session.add(db_dna)
    await db_session.commit()

    repo = StoryRepository(db_session)
    result = await repo.get_dna(story_id)

    assert isinstance(result, StoryDNA)
    assert result.story_id == str(story_id)
    assert result.premise == "A man receives calls from himself."
    assert result.twist_type == "time_loop"
    assert result.pov == "first_person"


# --- get_script ---

@pytest.mark.asyncio
async def test_get_script_returns_none_when_no_script_exists(db_session: AsyncSession):
    story_id = await make_story(db_session)
    repo = StoryRepository(db_session)

    result = await repo.get_script(story_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_script_returns_structured_script(db_session: AsyncSession):
    story_id = await make_story(db_session)

    db_script = ScriptModel(
        story_id=story_id,
        title="The Empty Apartment",
        logline="A man receives calls from himself, one hour ahead.",
        tone="dread",
        language="ar",
        estimated_duration=90.0,
        scenes=[
            {
                "scene_number": 1,
                "purpose": "establish isolation",
                "location": "empty apartment",
                "time_of_day": "night",
                "characters": ["Man"],
                "action": "He stares at his phone, waiting.",
                "dialogue": [],
                "narration": "I knew the call was coming.",
                "emotion": "dread",
                "estimated_duration": 15.0,
            }
        ],
    )
    db_session.add(db_script)
    await db_session.commit()

    repo = StoryRepository(db_session)
    result = await repo.get_script(story_id)

    assert isinstance(result, StructuredScript)
    assert result.title == "The Empty Apartment"
    assert len(result.scenes) == 1
    assert result.scenes[0].scene_number == 1
    assert result.scenes[0].estimated_duration == 15.0


# --- get_edit_plan ---

@pytest.mark.asyncio
async def test_get_edit_plan_returns_none_when_no_edit_plan_exists(db_session: AsyncSession):
    story_id = await make_story(db_session)
    repo = StoryRepository(db_session)

    result = await repo.get_edit_plan(story_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_edit_plan_returns_edit_plan(db_session: AsyncSession):
    story_id = await make_story(db_session)

    db_edit_plan = EditPlanModel(
        story_id=story_id,
        total_duration=20.0,
        cuts=[
            {"scene_number": 1, "start_time": 0.0, "end_time": 10.0},
            {"scene_number": 2, "start_time": 10.0, "end_time": 20.0},
        ],
    )
    db_session.add(db_edit_plan)
    await db_session.commit()

    repo = StoryRepository(db_session)
    result = await repo.get_edit_plan(story_id)

    assert isinstance(result, EditPlan)
    assert result.story_id == str(story_id)
    assert result.total_duration == 20.0
    assert len(result.cuts) == 2
    assert result.cuts[0].scene_number == 1
    assert result.cuts[1].end_time == 20.0


# --- get_voice_track ---

@pytest.mark.asyncio
async def test_get_voice_track_returns_none_when_no_voice_track_exists(db_session: AsyncSession):
    story_id = await make_story(db_session)
    repo = StoryRepository(db_session)

    result = await repo.get_voice_track(story_id)

    assert result is None


@pytest.mark.asyncio
async def test_get_voice_track_returns_voice_track_with_decoded_audio(db_session: AsyncSession):
    story_id = await make_story(db_session)

    import base64
    audio_bytes = b"fake-audio-bytes"

    db_voice_track = VoiceTrackModel(
        story_id=story_id,
        segments=[
            {
                "scene_number": 1,
                "speaker": "Man",
                "start_time": 0.0,
                "end_time": 3.42,
                "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
            }
        ],
    )
    db_session.add(db_voice_track)
    await db_session.commit()

    repo = StoryRepository(db_session)
    result = await repo.get_voice_track(story_id)

    assert isinstance(result, VoiceTrack)
    assert result.story_id == str(story_id)
    assert len(result.segments) == 1
    assert result.segments[0].audio == audio_bytes
    assert result.segments[0].start_time == 0.0
    assert result.segments[0].end_time == 3.42
