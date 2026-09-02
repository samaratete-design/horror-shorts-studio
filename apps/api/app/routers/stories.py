import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.story import Story, StoryStatus
from app.schemas.stories import CreateStoryRequest, CreateStoryResponse

router = APIRouter(prefix="/stories", tags=["stories"])


def _parse_story_id(story_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(story_id)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"'{story_id}' is not a valid story id (expected a UUID).")


@router.post("", response_model=CreateStoryResponse, status_code=201)
async def create_story(payload: CreateStoryRequest, db: AsyncSession = Depends(get_db)):
    story = Story(
        id=uuid.uuid4(),
        title=payload.title or payload.original_idea[:80],
        status=StoryStatus.DRAFT,
        original_idea=payload.original_idea,
        language=payload.language,
    )
    try:
        db.add(story)
        await db.commit()
        await db.refresh(story)
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=503, detail="Database is currently unavailable. Please retry.") from exc

    return CreateStoryResponse(
        id=str(story.id), status=story.status.value, original_idea=story.original_idea, title=story.title
    )


@router.get("/{story_id}", response_model=CreateStoryResponse)
async def get_story(story_id: str, db: AsyncSession = Depends(get_db)):
    parsed_id = _parse_story_id(story_id)
    try:
        story = await db.get(Story, parsed_id)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Database is currently unavailable. Please retry.") from exc

    if story is None:
        raise HTTPException(status_code=404, detail="Story not found")
    return CreateStoryResponse(
        id=str(story.id), status=story.status.value, original_idea=story.original_idea, title=story.title
    )
