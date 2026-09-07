import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared_types.structured_script import (
    DialogueLine,
    SceneItem,
    StructuredScript,
)
from app.infrastructure.repositories.story_repository import StoryRepository
from app.models.story import Story as SQLStory
from app.models.story import StoryStatus as SQLStoryStatus


def make_structured_script() -> StructuredScript:
    return StructuredScript(
        title="The Empty Apartment",
        logline="A man receives calls from himself, one hour ahead.",
        tone="dread",
        language="ar",
        estimated_duration=90.0,
        scenes=[
            SceneItem(
                scene_number=1,
                purpose="establish isolation",
                location="empty apartment",
                time_of_day="night",
                characters=["Man"],
                action="He stares at his phone, waiting.",
                dialogue=[
                    DialogueLine(
                        character="Man",
                        line="It's happening again.",
                        emotion="terrified",
                    )
                ],
                narration="I knew the call was coming.",
                emotion="dread",
                estimated_duration=15.0,
            )
        ],
    )


@pytest.mark.asyncio
async def test_save_script_creates_structured_script(
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

    script = make_structured_script()

    repo = StoryRepository(db_session)

    result = await repo.save_script(
        story_id=story_id,
        script=script,
    )

    assert result is not None
    assert result.story_id == story_id
    assert result.title == script.title
    assert result.logline == script.logline
    assert result.tone == script.tone
    assert result.language == script.language
    assert result.estimated_duration == script.estimated_duration
    assert len(result.scenes) == 1
    assert result.scenes[0]["scene_number"] == 1
    assert result.scenes[0]["dialogue"][0]["line"] == "It's happening again."
