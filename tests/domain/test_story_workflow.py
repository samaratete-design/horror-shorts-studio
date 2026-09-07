import pytest

from app.domain.story_workflow import (
    InvalidTransitionError,
    StoryStatus,
    StoryWorkflow,
)


@pytest.mark.parametrize(
    "current,target",
    [
        (StoryStatus.DRAFT, StoryStatus.ANALYZING),
        (StoryStatus.ANALYZING, StoryStatus.GENERATING),
        (StoryStatus.ANALYZING, StoryStatus.FAILED),
        (StoryStatus.GENERATING, StoryStatus.EDITING),
        (StoryStatus.GENERATING, StoryStatus.FAILED),
        (StoryStatus.EDITING, StoryStatus.RENDERING),
        (StoryStatus.EDITING, StoryStatus.FAILED),
        (StoryStatus.RENDERING, StoryStatus.READY),
        (StoryStatus.RENDERING, StoryStatus.FAILED),
        (StoryStatus.READY, StoryStatus.PUBLISHED),
        (StoryStatus.PUBLISHED, StoryStatus.ARCHIVED),
        (StoryStatus.FAILED, StoryStatus.DRAFT),
    ],
)
def test_valid_transitions(current, target):
    StoryWorkflow.validate_transition(current, target)


@pytest.mark.parametrize(
    "current,target",
    [
        (StoryStatus.DRAFT, StoryStatus.RENDERING),
        (StoryStatus.DRAFT, StoryStatus.PUBLISHED),
        (StoryStatus.GENERATING, StoryStatus.READY),
        (StoryStatus.PUBLISHED, StoryStatus.DRAFT),
        (StoryStatus.ARCHIVED, StoryStatus.DRAFT),
        (StoryStatus.READY, StoryStatus.DRAFT),
    ],
)
def test_invalid_transitions(current, target):
    with pytest.raises(InvalidTransitionError):
        StoryWorkflow.validate_transition(current, target)


@pytest.mark.parametrize("state", list(StoryStatus))
def test_same_state_is_valid(state):
    StoryWorkflow.validate_transition(state, state)
