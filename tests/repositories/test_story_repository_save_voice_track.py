import base64
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared_types.voice_track import VoiceTrack, VoiceSegment

from app.infrastructure.repositories.story_repository import StoryRepository
from app.models.story import Story as SQLStory
from app.models.story import StoryStatus as SQLStoryStatus


def make_voice_track(story_id: str) -> VoiceTrack:
    return VoiceTrack(
        story_id=story_id,
        segments=[
            VoiceSegment(
                scene_number=1, speaker="narrator",
                start_time=0.0, end_time=3.42,
                audio=b"narration-audio",
            ),
            VoiceSegment(
                scene_number=1, speaker="Man",
                start_time=3.42, end_time=5.87,
                audio=b"dialogue-audio",
            ),
        ],
    )


@pytest.mark.asyncio
async def test_save_voice_track_creates_voice_track(
    db_session: AsyncSession,
):
    story_id = uuid.uuid4()

    db_story = SQLStory(
        id=story_id,
        title="Test Horror Short",
        status=SQLStoryStatus.DRAFT,
        original_idea="A haunted house",
        language="ar",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(db_story)
    await db_session.commit()

    voice_track = make_voice_track(str(story_id))

    repo = StoryRepository(db_session)
    result = await repo.save_voice_track(
        story_id=story_id,
        voice_track=voice_track,
    )

    assert result is not None
    assert result.story_id == story_id
    assert len(result.segments) == 2
    assert result.segments[0]["scene_number"] == 1
    assert result.segments[0]["speaker"] == "narrator"
    assert result.segments[0]["start_time"] == pytest.approx(0.0)
    assert result.segments[0]["end_time"] == pytest.approx(3.42)
    assert result.segments[1]["start_time"] == pytest.approx(3.42)
    assert result.segments[1]["end_time"] == pytest.approx(5.87)
    assert base64.b64decode(result.segments[0]["audio_b64"]) == b"narration-audio"
    assert base64.b64decode(result.segments[1]["audio_b64"]) == b"dialogue-audio"


@pytest.mark.asyncio
async def test_save_voice_track_upserts_on_second_call(
    db_session: AsyncSession,
):
    story_id = uuid.uuid4()

    db_story = SQLStory(
        id=story_id,
        title="Test Horror Short",
        status=SQLStoryStatus.DRAFT,
        original_idea="A haunted house",
        language="ar",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(db_story)
    await db_session.commit()

    repo = StoryRepository(db_session)
    await repo.save_voice_track(
        story_id=story_id,
        voice_track=make_voice_track(str(story_id)),
    )

    updated_track = VoiceTrack(
        story_id=str(story_id),
        segments=[
            VoiceSegment(
                scene_number=1, speaker="narrator",
                start_time=0.0, end_time=1.0,
                audio=b"new-audio",
            ),
        ],
    )
    result = await repo.save_voice_track(
        story_id=story_id,
        voice_track=updated_track,
    )

    assert len(result.segments) == 1
    assert result.segments[0]["start_time"] == pytest.approx(0.0)
    assert result.segments[0]["end_time"] == pytest.approx(1.0)
    assert base64.b64decode(result.segments[0]["audio_b64"]) == b"new-audio"
