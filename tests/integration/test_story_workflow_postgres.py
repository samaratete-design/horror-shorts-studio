import uuid

import pytest
from sqlalchemy import select

from app.models.story import Story, StoryStatus
from app.db.session import AsyncSessionLocal
from app.services.story_workflow_service import (
    StoryWorkflowService,
    StoryNotFoundError,
)
from app.infrastructure.repositories.story_repository import StoryRepository
from app.domain.story_workflow import (
    StoryStatus as DomainStoryStatus,
    InvalidTransitionError,
)


async def _create_draft_story(story_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        story = Story(
            id=story_id,
            title="Postgres Integration Horror",
            status=StoryStatus.DRAFT,
            original_idea=(
                "A man receives calls from himself one hour "
                "in the future."
            ),
            language="ar",
        )

        session.add(story)
        await session.commit()


async def _delete_story(story_id: uuid.UUID):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Story).where(Story.id == story_id)
        )

        story = result.scalar_one_or_none()

        if story is not None:
            await session.delete(story)
            await session.commit()


async def _get_status(story_id: uuid.UUID) -> StoryStatus:
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Story).where(Story.id == story_id)
        )

        story = result.scalar_one()
        return story.status


async def _transition(
    story_id: uuid.UUID,
    target_state: DomainStoryStatus,
):
    async with AsyncSessionLocal() as session:
        repository = StoryRepository(session)
        service = StoryWorkflowService(repository)

        result = await service.transition_story(
            str(story_id),
            target_state,
        )

        await session.commit()

        return result


# ---------------------------------------------------------------------------
# Happy path
# DRAFT -> ANALYZING -> GENERATING -> EDITING -> RENDERING
#         -> READY -> PUBLISHED -> ARCHIVED
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_story_workflow_draft_to_archived_postgres():
    story_id = uuid.uuid4()

    await _create_draft_story(story_id)

    try:
        await _transition(
            story_id,
            DomainStoryStatus.ANALYZING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.GENERATING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.EDITING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.RENDERING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.READY,
        )

        await _transition(
            story_id,
            DomainStoryStatus.PUBLISHED,
        )

        await _transition(
            story_id,
            DomainStoryStatus.ARCHIVED,
        )

        assert await _get_status(story_id) == StoryStatus.ARCHIVED

    finally:
        await _delete_story(story_id)


# ---------------------------------------------------------------------------
# FAILED -> DRAFT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_story_workflow_failed_to_draft_postgres():
    story_id = uuid.uuid4()

    await _create_draft_story(story_id)

    try:
        await _transition(
            story_id,
            DomainStoryStatus.ANALYZING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.FAILED,
        )

        assert await _get_status(story_id) == StoryStatus.FAILED

        await _transition(
            story_id,
            DomainStoryStatus.DRAFT,
        )

        assert await _get_status(story_id) == StoryStatus.DRAFT

    finally:
        await _delete_story(story_id)


# ---------------------------------------------------------------------------
# Negative: EDITING -> DRAFT
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_editing_to_draft_is_rejected_postgres():
    story_id = uuid.uuid4()

    await _create_draft_story(story_id)

    try:
        await _transition(
            story_id,
            DomainStoryStatus.ANALYZING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.GENERATING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.EDITING,
        )

        assert await _get_status(story_id) == StoryStatus.EDITING

        async with AsyncSessionLocal() as session:
            repository = StoryRepository(session)
            service = StoryWorkflowService(repository)

            with pytest.raises(InvalidTransitionError):
                await service.transition_story(
                    str(story_id),
                    DomainStoryStatus.DRAFT,
                )

        assert await _get_status(story_id) == StoryStatus.EDITING

    finally:
        await _delete_story(story_id)


# ---------------------------------------------------------------------------
# Negative: READY -> EDITING
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ready_to_editing_is_rejected_postgres():
    story_id = uuid.uuid4()

    await _create_draft_story(story_id)

    try:
        await _transition(
            story_id,
            DomainStoryStatus.ANALYZING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.GENERATING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.EDITING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.RENDERING,
        )

        await _transition(
            story_id,
            DomainStoryStatus.READY,
        )

        assert await _get_status(story_id) == StoryStatus.READY

        async with AsyncSessionLocal() as session:
            repository = StoryRepository(session)
            service = StoryWorkflowService(repository)

            with pytest.raises(InvalidTransitionError):
                await service.transition_story(
                    str(story_id),
                    DomainStoryStatus.EDITING,
                )

        assert await _get_status(story_id) == StoryStatus.READY

    finally:
        await _delete_story(story_id)


# ---------------------------------------------------------------------------
# Negative: ARCHIVED cannot transition anywhere
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_archived_rejects_transitions_postgres():
    story_id = uuid.uuid4()

    await _create_draft_story(story_id)

    try:
        for target_state in (
            DomainStoryStatus.ANALYZING,
            DomainStoryStatus.GENERATING,
            DomainStoryStatus.EDITING,
            DomainStoryStatus.RENDERING,
            DomainStoryStatus.READY,
            DomainStoryStatus.PUBLISHED,
            DomainStoryStatus.ARCHIVED,
        ):
            await _transition(story_id, target_state)

        assert await _get_status(story_id) == StoryStatus.ARCHIVED

        for target_state in (
            DomainStoryStatus.DRAFT,
            DomainStoryStatus.ANALYZING,
            DomainStoryStatus.PUBLISHED,
        ):
            async with AsyncSessionLocal() as session:
                repository = StoryRepository(session)
                service = StoryWorkflowService(repository)

                with pytest.raises(InvalidTransitionError):
                    await service.transition_story(
                        str(story_id),
                        target_state,
                    )

            assert await _get_status(story_id) == StoryStatus.ARCHIVED

    finally:
        await _delete_story(story_id)


# ---------------------------------------------------------------------------
# Negative: unknown story
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_story_raises_not_found_postgres():
    story_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        repository = StoryRepository(session)
        service = StoryWorkflowService(repository)

        with pytest.raises(StoryNotFoundError):
            await service.transition_story(
                str(story_id),
                DomainStoryStatus.ANALYZING,
            )
