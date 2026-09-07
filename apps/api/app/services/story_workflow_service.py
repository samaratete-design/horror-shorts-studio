from typing import Protocol, Optional
from app.domain.story_workflow import (
    StoryWorkflow,
    StoryStatus,
)

class StoryRepositoryProtocol(Protocol):
    async def get_by_id(self, story_id: str) -> Optional[object]:
        ...
    async def update_status(self, story_id: str, new_status: str) -> object:
        ...

class StoryNotFoundError(Exception):
    pass

class StoryWorkflowService:
    def __init__(self, repository: StoryRepositoryProtocol):
        self.repository = repository

    async def transition_story(
        self,
        story_id: str,
        target_state: StoryStatus,
    ) -> object:
        story = await self.repository.get_by_id(story_id)
        if not story:
            raise StoryNotFoundError(
                f"Story with id '{story_id}' not found."
            )
        
        if hasattr(story, "status"):
            raw_status = story.status
        elif isinstance(story, dict):
            raw_status = story.get("status")
        else:
            raw_status = getattr(story, "status", None)

        if isinstance(raw_status, str):
            current_state = StoryStatus(raw_status.upper())
        else:
            current_state = StoryStatus(raw_status.name)

        StoryWorkflow.validate_transition(
            current_state,
            target_state,
        )
        updated_story = await self.repository.update_status(
            story_id,
            target_state.name,
        )
        return updated_story

    async def advance_to_generation(self, story_id: str) -> object:
        return await self.transition_story(story_id, StoryStatus.GENERATING)
