import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared_types.edit_plan import EditPlan, SceneCut

from app.infrastructure.repositories.story_repository import StoryRepository
from app.models.story import Story as SQLStory
from app.models.story import StoryStatus as SQLStoryStatus


def make_edit_plan(story_id: str) -> EditPlan:
    return EditPlan(
        story_id=story_id,
        total_duration=25.0,
        cuts=[
            SceneCut(scene_number=1, start_time=0.0, end_time=10.0),
            SceneCut(scene_number=2, start_time=10.0, end_time=25.0),
        ],
    )


@pytest.mark.asyncio
async def test_save_edit_plan_creates_edit_plan(
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

    edit_plan = make_edit_plan(str(story_id))

    repo = StoryRepository(db_session)
    result = await repo.save_edit_plan(
        story_id=story_id,
        edit_plan=edit_plan,
    )

    assert result is not None
    assert result.story_id == story_id
    assert result.total_duration == 25.0
    assert len(result.cuts) == 2
    assert result.cuts[0]["scene_number"] == 1
    assert result.cuts[0]["start_time"] == 0.0
    assert result.cuts[1]["end_time"] == 25.0


@pytest.mark.asyncio
async def test_save_edit_plan_upserts_on_second_call(
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

    await repo.save_edit_plan(
        story_id=story_id,
        edit_plan=make_edit_plan(str(story_id)),
    )

    updated_plan = EditPlan(
        story_id=str(story_id),
        total_duration=40.0,
        cuts=[SceneCut(scene_number=1, start_time=0.0, end_time=40.0)],
    )
    result = await repo.save_edit_plan(
        story_id=story_id,
        edit_plan=updated_plan,
    )

    assert result.total_duration == 40.0
    assert len(result.cuts) == 1
