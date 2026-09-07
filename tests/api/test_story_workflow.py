import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.deps import get_db
from app.routers.story_workflow import get_workflow_service
from app.models.story import Story, StoryStatus
from app.domain.story_workflow import (
    StoryStatus as DomainStoryStatus,
    StoryWorkflow,
    InvalidTransitionError,
)
from app.services.story_workflow_service import StoryNotFoundError


class FakeAsyncSession:
    """
    Small in-memory DB double for API-level workflow tests.

    Repository/service/database integration is covered separately by
    repository and service tests.
    """

    def __init__(self):
        self.stories: dict[uuid.UUID, Story] = {}

    def add(self, story: Story):
        self.stories[story.id] = story

    async def commit(self):
        return None

    async def refresh(self, story: Story):
        return None

    async def get(self, model, story_id):
        return self.stories.get(story_id)


class FakeWorkflowService:
    """
    API-test double that preserves the real StoryWorkflow transition rules.
    """

    def __init__(self, session: FakeAsyncSession):
        self.session = session

    async def transition_story(
        self,
        story_id: str,
        target_state: DomainStoryStatus,
    ):
        try:
            parsed_id = uuid.UUID(story_id)
        except ValueError:
            raise StoryNotFoundError(f"Story '{story_id}' not found.")

        story = self.session.stories.get(parsed_id)

        if story is None:
            raise StoryNotFoundError("Story not found")

        current_state = DomainStoryStatus(story.status.value.upper())

        StoryWorkflow.validate_transition(
            current_state,
            target_state,
        )

        # Keep SQLAlchemy model state canonical.
        story.status = StoryStatus(target_state.value.lower())

        return story


@pytest.fixture
def fake_session():
    session = FakeAsyncSession()

    story = Story(
        id=uuid.uuid4(),
        title="Test Horror Story",
        status=StoryStatus.DRAFT,
        original_idea="A man receives calls from himself one hour in the future.",
        language="ar",
    )

    session.add(story)

    return session, story


@pytest.fixture
def client(fake_session):
    session, _ = fake_session

    async def override_get_db():
        yield session

    def override_workflow_service():
        return FakeWorkflowService(session)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_workflow_service] = override_workflow_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_workflow_happy_path(client, fake_session):
    """
    DRAFT -> ANALYZING -> GENERATING -> EDITING
    """

    _, story = fake_session

    transitions = [
        ("ANALYZING", "analyzing"),
        ("GENERATING", "generating"),
        ("EDITING", "editing"),
    ]

    for target_state, expected_status in transitions:
        response = client.post(
            f"/stories/{story.id}/transition",
            json={"target_state": target_state},
        )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == str(story.id)
        assert body["status"] == expected_status
        assert body["original_idea"] == story.original_idea


def test_invalid_transition_returns_400(client, fake_session):
    """
    EDITING -> DRAFT is not allowed.
    """

    _, story = fake_session

    story.status = StoryStatus.EDITING

    response = client.post(
        f"/stories/{story.id}/transition",
        json={"target_state": "DRAFT"},
    )

    assert response.status_code == 400

    body = response.json()

    assert "not allowed" in body["detail"]


def test_unknown_state_returns_400(client, fake_session):
    """
    An unknown StoryStatus must be rejected by the API.
    """

    _, story = fake_session

    response = client.post(
        f"/stories/{story.id}/transition",
        json={"target_state": "UNKNOWN"},
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail": "Invalid story state: 'UNKNOWN'."
    }


def test_story_not_found_returns_404(client):
    """
    A valid UUID that does not exist must return 404.
    """

    missing_story_id = uuid.uuid4()

    response = client.post(
        f"/stories/{missing_story_id}/transition",
        json={"target_state": "ANALYZING"},
    )

    assert response.status_code == 404

    assert response.json() == {
        "detail": "Story not found"
    }


def test_workflow_accepts_lowercase_state(client, fake_session):
    """
    API should normalize target_state through .upper().
    """

    _, story = fake_session

    response = client.post(
        f"/stories/{story.id}/transition",
        json={"target_state": "analyzing"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "analyzing"


def test_workflow_response_shape(client, fake_session):
    """
    Protect the API response contract.
    """

    _, story = fake_session

    response = client.post(
        f"/stories/{story.id}/transition",
        json={"target_state": "ANALYZING"},
    )

    assert response.status_code == 200

    body = response.json()

    assert set(body.keys()) == {
        "id",
        "status",
        "original_idea",
        "title",
    }

    assert body["id"] == str(story.id)
    assert body["status"] == "analyzing"
