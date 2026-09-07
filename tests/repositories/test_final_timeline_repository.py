import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared_types.final_timeline import FinalTimeline, FinalSegment

from app.infrastructure.repositories.final_timeline_repository import FinalTimelineRepository
from app.models.story import Story as SQLStory
from app.models.story import StoryStatus as SQLStoryStatus


async def make_story(db_session: AsyncSession) -> uuid.UUID:
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
    return story_id


def make_timeline(story_id: str) -> FinalTimeline:
    return FinalTimeline(
        story_id=story_id,
        total_duration=20.5,
        segments=[
            FinalSegment(scene_number=1, start_time=0.0, end_time=9.5),
            FinalSegment(scene_number=2, start_time=9.5, end_time=20.5),
        ],
        music_assets=[],
    )


@pytest.mark.asyncio
async def test_save_creates_final_timeline_with_segments_and_references(
    db_session: AsyncSession,
):
    story_id = await make_story(db_session)
    repo = FinalTimelineRepository(db_session)

    visual_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    music_ids = [str(uuid.uuid4())]

    result = await repo.save(
        story_id,
        make_timeline(str(story_id)),
        visual_asset_ids=visual_ids,
        music_asset_ids=music_ids,
    )

    assert result.story_id == story_id
    assert result.total_duration == pytest.approx(20.5)
    assert len(result.segments) == 2
    assert result.segments[0]["scene_number"] == 1
    assert result.segments[0]["start_time"] == pytest.approx(0.0)
    assert result.segments[0]["end_time"] == pytest.approx(9.5)
    assert result.visual_asset_ids == visual_ids
    assert result.music_asset_ids == music_ids


@pytest.mark.asyncio
async def test_save_upserts_on_second_call(db_session: AsyncSession):
    story_id = await make_story(db_session)
    repo = FinalTimelineRepository(db_session)

    await repo.save(
        story_id, make_timeline(str(story_id)),
        visual_asset_ids=["a"], music_asset_ids=["m"],
    )

    updated = FinalTimeline(
        story_id=str(story_id), total_duration=30.0,
        segments=[FinalSegment(scene_number=1, start_time=0.0, end_time=30.0)],
        music_assets=[],
    )
    result = await repo.save(
        story_id, updated, visual_asset_ids=["b", "c"], music_asset_ids=["n"],
    )

    assert result.total_duration == pytest.approx(30.0)
    assert len(result.segments) == 1
    assert result.visual_asset_ids == ["b", "c"]

    fetched = await repo.get(story_id)
    assert fetched.total_duration == pytest.approx(30.0)


@pytest.mark.asyncio
async def test_get_returns_none_when_not_saved(db_session: AsyncSession):
    story_id = await make_story(db_session)
    repo = FinalTimelineRepository(db_session)

    result = await repo.get(story_id)
    assert result is None
