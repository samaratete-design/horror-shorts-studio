import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories.story_repository import StoryRepository
from app.models.story import Story as SQLStory
from app.models.story import StoryStatus as SQLStoryStatus


@pytest.mark.asyncio
async def test_repository_get_and_update_status(
    db_session: AsyncSession,
):
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

    repo = StoryRepository(db_session)

    fetched = await repo.get_by_id(story_id)

    assert fetched is not None
    assert fetched.id == story_id
    assert fetched.status == SQLStoryStatus.DRAFT

    updated = await repo.update_status(
        story_id,
        SQLStoryStatus.ANALYZING.value,
    )

    assert updated is not None
    assert updated.id == story_id
    assert updated.status == SQLStoryStatus.ANALYZING
