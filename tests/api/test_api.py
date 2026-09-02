"""
API tests for GET /health, POST /stories, GET /stories/{id}, POST /originality/check.

Uses FastAPI's dependency_overrides to replace get_db with fake in-memory
session doubles - no live Postgres required. Requires fastapi/httpx/sqlalchemy
to be importable; if they aren't (e.g. this sandbox had no network access to
install them), the whole module is skipped rather than failing, and that's
reported explicitly in the test run rather than silently.
"""
import uuid

import pytest

fastapi = pytest.importorskip("fastapi", reason="fastapi not installed in this environment")
httpx = pytest.importorskip("httpx", reason="httpx not installed in this environment")
sqlalchemy = pytest.importorskip("sqlalchemy", reason="sqlalchemy not installed in this environment")

from httpx import AsyncClient, ASGITransport  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.story import Story, StoryStatus  # noqa: E402
from app.db.pgvector_store import PgVectorStore  # noqa: E402
from app.core.container import build_originality_engine  # noqa: E402
from app.routers import originality as originality_router  # noqa: E402


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class FakeAsyncSession:
    """Minimal in-memory double for the pieces of AsyncSession the routers use."""

    def __init__(self):
        self._stories: dict[uuid.UUID, Story] = {}

    def add(self, obj):
        if isinstance(obj, Story):
            self._stories[obj.id] = obj

    async def commit(self):
        return None

    async def refresh(self, obj):
        return None

    async def get(self, model, id_):
        if model is Story:
            return self._stories.get(id_)
        return None

    async def execute(self, stmt):
        # Used by PgVectorStore.nearest() via select(...).where(...); this
        # fake has no stored DNA rows, so originality checks against it
        # always see zero neighbors (equivalent to "no existing stories").
        return FakeResult([])


@pytest.fixture
def fake_session():
    return FakeAsyncSession()


@pytest.fixture
def client(fake_session):
    async def _override_get_db():
        yield fake_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    yield AsyncClient(transport=transport, base_url="http://test")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health(client):
    async with client as c:
        resp = await c.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_create_story(client):
    async with client as c:
        resp = await c.post("/stories", json={"original_idea": "A man receives calls from himself."})
    assert resp.status_code == 201
    body = resp.json()
    assert body["original_idea"] == "A man receives calls from himself."
    assert body["status"] == StoryStatus.DRAFT.value
    # must be a valid UUID
    uuid.UUID(body["id"])


@pytest.mark.asyncio
async def test_get_story_found(client, fake_session):
    async with client as c:
        create_resp = await c.post("/stories", json={"original_idea": "A whispering attic."})
        story_id = create_resp.json()["id"]

        get_resp = await c.get(f"/stories/{story_id}")

    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == story_id


@pytest.mark.asyncio
async def test_get_story_not_found_returns_404(client):
    async with client as c:
        resp = await c.get(f"/stories/{uuid.uuid4()}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_story_invalid_uuid_returns_422_not_500(client):
    async with client as c:
        resp = await c.get("/stories/not-a-uuid")
    # Malformed UUID must be a controlled 4xx, never an uncaught 500.
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_originality_check_with_no_existing_stories_approves(client):
    dna_payload = {
        "premise": "A woman discovers her reflection is delayed by a few seconds.",
        "setting": "a small apartment bathroom",
        "threat": "a delayed, autonomous reflection",
        "fear_mechanism": "uncanny_valley",
        "narrative_device": "mirror",
        "twist_type": "recontextualization",
        "ending_type": "ambiguous",
        "pov": "first_person",
        "conflict": "she must figure out if the reflection is warning her or replacing her",
        "emotional_theme": "loss of identity",
        "core_fear": "losing control of your own body/identity",
        "unique_story_hook": "the delay increases by exactly one second every night",
    }
    async with client as c:
        resp = await c.post("/originality/check", json={"dna": dna_payload})

    assert resp.status_code == 200
    decision = resp.json()["decision"]
    assert decision["verdict"] == "approved"


@pytest.mark.asyncio
async def test_originality_check_rejects_malformed_dna_with_422(client):
    async with client as c:
        resp = await c.post("/originality/check", json={"dna": {"premise": "missing required fields"}})
    assert resp.status_code == 422
