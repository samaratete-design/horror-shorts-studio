"""
Story DNA: the structured fingerprint of a horror story.

This is intentionally NOT free text. Every field is a discrete,
comparable dimension so the Originality Engine can measure similarity
dimension-by-dimension instead of relying on a single fuzzy embedding score.
"""
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class POV(str, Enum):
    FIRST_PERSON = "first_person"
    SECOND_PERSON = "second_person"
    THIRD_PERSON_LIMITED = "third_person_limited"
    THIRD_PERSON_OMNISCIENT = "third_person_omniscient"
    FOUND_FOOTAGE = "found_footage"


class TwistType(str, Enum):
    IDENTITY_REVEAL = "identity_reveal"
    RECONTEXTUALIZATION = "recontextualization"
    UNRELIABLE_NARRATOR = "unreliable_narrator"
    TIME_LOOP = "time_loop"
    ALREADY_DEAD = "already_dead"
    THE_THREAT_WAS_PROTECTIVE = "the_threat_was_protective"
    IT_WAS_THE_NARRATOR = "it_was_the_narrator"
    NESTED_REALITY = "nested_reality"
    NONE = "none"


class EndingType(str, Enum):
    OPEN_LOOP = "open_loop"
    TRAGIC = "tragic"
    AMBIGUOUS = "ambiguous"
    RECONTEXTUALIZATION = "recontextualization"
    ESCAPE = "escape"
    FULL_CIRCLE = "full_circle"
    CLIFFHANGER = "cliffhanger"


class StoryDNA(BaseModel):
    """Structured, comparable fingerprint of a single story concept."""

    id: Optional[str] = None
    story_id: Optional[str] = None

    premise: str = Field(..., description="One-sentence core concept")
    setting: str = Field(..., description="e.g. isolated cabin, apartment 3B, empty subway car")
    threat: str = Field(..., description="The source of danger, e.g. a doppelganger, a cursed object")
    fear_mechanism: str = Field(..., description="What makes it scary: isolation, uncanny valley, loss of control...")
    narrative_device: str = Field(..., description="e.g. phone calls, video tapes, diary entries, live stream")
    twist_type: TwistType = TwistType.NONE
    ending_type: EndingType = EndingType.OPEN_LOOP
    pov: POV = POV.FIRST_PERSON
    time_period: str = Field(default="present_day")
    supernatural_element: str = Field(default="unknown")
    conflict: str = Field(..., description="Core dramatic conflict")
    emotional_theme: str = Field(..., description="e.g. grief, guilt, paranoia, loss of identity")
    protagonist_archetype: str = Field(default="ordinary_person")
    antagonist_archetype: str = Field(default="unknown_force")
    core_fear: str = Field(..., description="The primal fear this story exploits")
    visual_style: str = Field(default="dark_realistic")
    unique_story_hook: str = Field(..., description="What makes THIS telling distinct")

    embedding: Optional[list[float]] = Field(
        default=None, description="Vector embedding of the full DNA, populated by EmbeddingProvider"
    )

    class Config:
        use_enum_values = True


# The dimensions compared individually by the Originality Engine.
# Order matters only for readability; comparison is dimension-independent.
STRUCTURAL_DIMENSIONS: list[str] = [
    "setting",
    "threat",
    "fear_mechanism",
    "narrative_device",
    "twist_type",
    "ending_type",
    "pov",
    "core_fear",
]

StoryDNADimension = str  # alias for typing clarity in the originality engine
