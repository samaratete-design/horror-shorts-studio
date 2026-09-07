from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.domain.story_workflow import StoryStatus, InvalidTransitionError
from app.infrastructure.repositories.story_repository import StoryRepository
from app.schemas.stories import CreateStoryResponse, StoryTransitionRequest
from app.services.story_workflow_service import (
    StoryWorkflowService,
    StoryNotFoundError,
)

router = APIRouter(prefix="/stories", tags=["story-workflow"])


def get_workflow_service(
    db: AsyncSession = Depends(get_db),
) -> StoryWorkflowService:
    repository = StoryRepository(db)
    return StoryWorkflowService(repository)


@router.post(
    "/{story_id}/transition",
    response_model=CreateStoryResponse,
)
async def transition_story(
    story_id: str,
    payload: StoryTransitionRequest,
    service: StoryWorkflowService = Depends(get_workflow_service),
):
    try:
        target_state = StoryStatus(payload.target_state.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid story state: '{payload.target_state}'.",
        )

    try:
        story = await service.transition_story(
            story_id,
            target_state,
        )
    except StoryNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
    except InvalidTransitionError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return CreateStoryResponse(
        id=str(story.id),
        status=story.status.value,
        original_idea=story.original_idea,
        title=story.title,
    )
