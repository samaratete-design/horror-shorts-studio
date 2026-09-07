from enum import Enum
from typing import Set


class StoryStatus(str, Enum):
    DRAFT = "DRAFT"
    ANALYZING = "ANALYZING"
    GENERATING = "GENERATING"
    EDITING = "EDITING"
    RENDERING = "RENDERING"
    READY = "READY"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class InvalidTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""


class StoryWorkflow:
    TRANSITION_MATRIX: dict[StoryStatus, Set[StoryStatus]] = {
        StoryStatus.DRAFT: {StoryStatus.ANALYZING},
        StoryStatus.ANALYZING: {
            StoryStatus.GENERATING,
            StoryStatus.FAILED,
        },
        StoryStatus.GENERATING: {
            StoryStatus.EDITING,
            StoryStatus.FAILED,
        },
        StoryStatus.EDITING: {
            StoryStatus.RENDERING,
            StoryStatus.FAILED,
        },
        StoryStatus.RENDERING: {
            StoryStatus.READY,
            StoryStatus.FAILED,
        },
        StoryStatus.READY: {StoryStatus.PUBLISHED},
        StoryStatus.PUBLISHED: {StoryStatus.ARCHIVED},
        StoryStatus.FAILED: {StoryStatus.DRAFT},
        StoryStatus.ARCHIVED: set(),
    }

    @classmethod
    def validate_transition(
        cls,
        current_state: StoryStatus,
        target_state: StoryStatus,
    ) -> None:
        if current_state == target_state:
            return

        allowed_targets = cls.TRANSITION_MATRIX.get(
            current_state,
            set(),
        )

        if target_state not in allowed_targets:
            raise InvalidTransitionError(
                f"Transition from '{current_state}' "
                f"to '{target_state}' is not allowed."
            )
