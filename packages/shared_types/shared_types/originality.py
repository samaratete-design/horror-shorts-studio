from enum import Enum
from pydantic import BaseModel, Field


class OriginalityVerdict(str, Enum):
    APPROVED = "approved"
    REWRITE = "rewrite"
    HARD_REJECT = "hard_reject"


class DimensionConflict(BaseModel):
    dimension: str
    candidate_value: str
    matched_value: str
    matched_story_id: str
    similarity: float


class OriginalityDecision(BaseModel):
    verdict: OriginalityVerdict
    overall_similarity: float = Field(..., ge=0.0, le=1.0)
    most_similar_story_id: str | None = None
    conflicts: list[DimensionConflict] = Field(default_factory=list)
    structural_conflict_triggered: bool = False
    explanation: str
    recommendation: str | None = None

    class Config:
        use_enum_values = True
