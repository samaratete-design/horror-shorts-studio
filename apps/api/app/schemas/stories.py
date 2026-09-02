from pydantic import BaseModel

from shared_types.story_dna import StoryDNA
from shared_types.originality import OriginalityDecision


class CreateStoryRequest(BaseModel):
    original_idea: str
    language: str = "ar"
    title: str | None = None


class CreateStoryResponse(BaseModel):
    id: str
    status: str
    original_idea: str
    title: str | None


class OriginalityCheckRequest(BaseModel):
    dna: StoryDNA


class OriginalityCheckResponse(BaseModel):
    decision: OriginalityDecision
