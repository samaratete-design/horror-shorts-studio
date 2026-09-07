import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from shared_types.story_dna import EndingType, POV, StoryDNA, TwistType
from app.infrastructure.repositories.story_repository import StoryRepository
from app.models.story import Story as SQLStory
from app.models.story import StoryDNAModel
from app.models.story import StoryStatus as SQLStoryStatus


@pytest.mark.asyncio
async def test_save_dna_updates_existing_dna_for_same_story(
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

    first_dna = StoryDNAModel(
        story_id=story_id,
        premise="Original premise",
        setting="old house",
        threat="unknown entity",
        fear_mechanism="isolation",
        narrative_device="recording",
        twist_type=TwistType.NONE,
        ending_type=EndingType.OPEN_LOOP,
        pov=POV.FIRST_PERSON,
        conflict="person vs entity",
        emotional_theme="fear",
        core_fear="being trapped",
        unique_story_hook="the house changes",
    )

    db_session.add(first_dna)
    await db_session.commit()

    new_dna = StoryDNA(
        premise="Updated premise",
        setting="abandoned apartment",
        threat="future version of himself",
        fear_mechanism="loss of control",
        narrative_device="phone calls",
        twist_type=TwistType.TIME_LOOP,
        ending_type=EndingType.CLIFFHANGER,
        pov=POV.FIRST_PERSON,
        conflict="man vs future self",
        emotional_theme="paranoia",
        core_fear="losing agency",
        unique_story_hook="the calls get closer together",
    )

    repo = StoryRepository(db_session)

    result = await repo.save_dna(
        story_id=story_id,
        dna=new_dna,
    )

    assert result.id == first_dna.id
    assert result.story_id == story_id
    assert result.premise == "Updated premise"
    assert result.setting == "abandoned apartment"
    assert result.threat == "future version of himself"
    assert result.twist_type == new_dna.twist_type
    assert result.ending_type == new_dna.ending_type
    assert result.pov == new_dna.pov
