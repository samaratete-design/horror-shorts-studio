import pytest
from unittest.mock import AsyncMock
from apps.api.app.services.story_workflow_service import (
    StoryWorkflowService,
    StoryNotFoundError,
)
from apps.api.app.domain.story_workflow import StoryStatus

@pytest.mark.anyio
async def test_advance_to_generation_valid():
    repo = AsyncMock()
    repo.get_by_id.return_value = {"id": "1", "status": "ANALYZING"}
    repo.update_status.return_value = {"id": "1", "status": "GENERATING"}

    service = StoryWorkflowService(repository=repo)
    result = await service.advance_to_generation("1")

    assert result["status"] == "GENERATING"
    repo.update_status.assert_called_once_with("1", "GENERATING")

@pytest.mark.anyio
async def test_advance_to_generation_repository_mandatory():
    with pytest.raises(TypeError):
        StoryWorkflowService() # type: ignore

@pytest.mark.anyio
async def test_advance_to_generation_invalid_source_state():
    repo = AsyncMock()
    repo.get_by_id.return_value = {"id": "1", "status": "DRAFT"}

    service = StoryWorkflowService(repository=repo)
    with pytest.raises(Exception):
        await service.advance_to_generation("1")

@pytest.mark.anyio
async def test_advance_to_generation_story_not_found():
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    service = StoryWorkflowService(repository=repo)
    with pytest.raises(StoryNotFoundError):
        await service.advance_to_generation("1")

@pytest.mark.anyio
async def test_advance_to_generation_persistence_failure():
    repo = AsyncMock()
    repo.get_by_id.return_value = {"id": "1", "status": "ANALYZING"}
    repo.update_status.side_effect = Exception("DB error")

    service = StoryWorkflowService(repository=repo)
    with pytest.raises(Exception):
        await service.advance_to_generation("1")
