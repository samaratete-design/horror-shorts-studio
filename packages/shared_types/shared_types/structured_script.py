from typing import List, Optional

from pydantic import BaseModel, Field


class DialogueLine(BaseModel):
    character: str
    line: str
    emotion: str = Field(
        ...,
        description="e.g., neutral, whispering, terrified, shocked",
    )


class SceneItem(BaseModel):
    scene_number: int
    purpose: str
    location: str
    time_of_day: str = Field(
        ...,
        description="e.g., night, twilight, day",
    )
    characters: List[str]
    action: str
    dialogue: List[DialogueLine] = Field(default_factory=list)
    narration: Optional[str] = None
    emotion: str = Field(
        ...,
        description="Dominant emotional tone of the scene",
    )
    estimated_duration: float = Field(
        ...,
        description="Duration in seconds",
    )


class StructuredScript(BaseModel):
    title: str
    logline: str
    tone: str
    language: str = "ar"
    estimated_duration: float
    scenes: List[SceneItem]
