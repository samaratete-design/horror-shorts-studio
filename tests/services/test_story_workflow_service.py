import pytest
from unittest.mock import AsyncMock

from app.domain.story_workflow import (
    InvalidTransitionError,
    StoryStatus,
)
from app.services.story_workflow_service import (
    StoryNotFoundError,
    StoryWorkflowService,
)


class MockStory:
    def __init__(self, id: str, status: str):
        self.id = id
        self.status = status


@pytest.mark.asyncio
async def test_successful_transition():
    repo = AsyncMock()
    repo.get_by_id.return_value = MockStory("1", "DRAFT")
    repo.update_status.return_value = MockStory("1", "ANALYZING")

    service = StoryWorkflowService(repository=repo)

    result = await service.transition_story(
        "1",
        StoryStatus.ANALYZING,
    )

    assert result.status == "ANALYZING"

    repo.get_by_id.assert_awaited_once_with("1")
    repo.update_status.assert_awaited_once_with(
        "1",
        "ANALYZING",
    )


@pytest.mark.asyncio
async def test_invalid_transition_rejected():
    repo = AsyncMock()
    repo.get_by_id.return_value = MockStory("1", "DRAFT")

    service = StoryWorkflowService(repository=repo)

    with pytest.raises(InvalidTransitionError):
        await service.transition_story(
            "1",
            StoryStatus.RENDERING,
        )

    repo.update_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_story_not_found():
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    service = StoryWorkflowService(repository=repo)

    with pytest.raises(StoryNotFoundError):
        await service.transition_story(
            "999",
            StoryStatus.ANALYZING,
        )

    repo.update_status.assert_not_awaited()
