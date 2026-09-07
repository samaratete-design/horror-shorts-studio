import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared_types.story_dna import EndingType, POV, StoryDNA, TwistType
from app.infrastructure.repositories.story_repository import StoryRepository
from app.models.story import Story as SQLStory
from app.models.story import StoryStatus as SQLStoryStatus


@pytest.mark.asyncio
async def test_save_dna_creates_story_dna(
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

    dna = StoryDNA(
        premise="A haunted house that remembers its visitors.",
        setting="abandoned house",
        threat="the house itself",
        fear_mechanism="loss of control",
        narrative_device="recorded messages",
        twist_type=TwistType.IDENTITY_REVEAL,
        ending_type=EndingType.CLIFFHANGER,
        pov=POV.FIRST_PERSON,
        conflict="person vs haunted house",
        emotional_theme="paranoia",
        core_fear="being trapped",
        unique_story_hook="the house changes based on who enters",
    )

    repo = StoryRepository(db_session)

    result = await repo.save_dna(
        story_id=story_id,
        dna=dna,
    )

    assert result is not None
    assert result.story_id == story_id
    assert result.premise == dna.premise
    assert result.setting == dna.setting
    assert result.threat == dna.threat
    assert result.twist_type == dna.twist_type
    assert result.ending_type == dna.ending_type
    assert result.pov == dna.pov
