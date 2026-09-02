# Horror Shorts Studio — Phase 1 (hardened)

AI-powered horror-Shorts content factory. Phase 1 delivers: monorepo
skeleton, database schema, Story DNA model, the **Originality Engine**
(structural + semantic similarity, single-decisive-match logic, conflict
guard, differentiator), the **Content Quality Gate**, provider abstractions
(Anthropic LLM + dev-stub embeddings), a minimal FastAPI surface, centralized
configuration, controlled error handling, and a test suite.

## ⚠️ Run this yourself — this sandbox cannot execute it

This project (and this hardening pass) was built in a sandbox with **no
network access** and **none of pydantic / fastapi / sqlalchemy / pytest /
anthropic installed**, and no way to install them. That means:

- I can and did verify every `.py` file **parses** (`ast.parse`) — 51/51 pass.
- I **cannot** and did not run `pytest`. I have not seen it collect, pass,
  fail, or skip a single test. Any "test count" I state below is a **static
  count of `def test_*` functions in the source**, not an execution result.
- **You must run `pytest tests/ -v` yourself** and are the first person to
  see real pass/fail output for this codebase.

## Quick start

```bash
# 1. Start Postgres (with pgvector) + Redis
docker compose up -d postgres redis

# 2. Install everything (editable installs of the local packages, in dependency order)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. Run migrations
alembic upgrade head
# (DATABASE_URL / DATABASE_URL_SYNC are read from app.core.config.Settings —
#  see Environment variables below; alembic/env.py calls settings.resolved_sync_database_url())

# 4. Run the test suite
pytest tests/ -v
# Originality/quality-gate/conflict-guard/differentiator tests use in-memory
# fakes (InMemoryVectorStore, a fake deterministic LLM) and need NO live DB.
# API tests use FastAPI dependency_overrides with a FakeAsyncSession and NO
# live DB either. If fastapi/httpx/sqlalchemy aren't installed, tests/api/
# is skipped via pytest.importorskip rather than erroring — check the
# printed skip reason.

# 5. Run the API (requires ANTHROPIC_API_KEY for the LLM provider;
#    the embedding provider is a dev stub, no key needed)
export ANTHROPIC_API_KEY=sk-ant-...
export DATABASE_URL=postgresql+asyncpg://horror:horror@localhost:5432/horror_shorts_studio
uvicorn app.main:app --reload --app-dir apps/api
```

## Environment variables

All configuration is centralized in `apps/api/app/core/config.py`
(`Settings`, a `pydantic-settings` model) plus one special case,
`apps/api/app/core/constants.py` (`EMBEDDING_DIMENSIONS`) — see "Embedding
dimension consistency" below for why that one constant needed its own file.
No other file reads `os.environ` directly.

| Variable | Default | Used by |
|---|---|---|
| `ENVIRONMENT` | `dev` | `Settings.environment` |
| `DATABASE_URL` | `postgresql+asyncpg://horror:horror@localhost:5432/horror_shorts_studio` | API runtime (asyncpg) |
| `DATABASE_URL_SYNC` | derived from `DATABASE_URL` | Alembic (sync driver) |
| `REDIS_URL` | `redis://localhost:6379/0` | reserved for Phase 5/6 |
| `ANTHROPIC_API_KEY` | none (required to actually call the LLM) | `AnthropicLLMProvider` |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-6` | `AnthropicLLMProvider` |
| `EMBEDDING_DIMENSIONS` | `256` | DB column width, embedding provider, vector store, tests — **single source, see below** |
| `ORIGINALITY_APPROVE_BELOW` | `0.50` | `OriginalityThresholds.approve_below` |
| `ORIGINALITY_HARD_REJECT_ABOVE` | `0.70` | `OriginalityThresholds.hard_reject_above` |

## Docker

```bash
docker compose up -d postgres redis   # infra only, for local dev against the API run from your venv
docker compose up --build              # full stack, including the API container
docker compose down -v                 # tear down + wipe the Postgres volume
```

## Migrations

```bash
alembic upgrade head        # apply
alembic downgrade -1        # roll back one revision
alembic revision -m "..."   # new migration (autogenerate not yet wired to the async engine)
```

---

## Hardening pass — what changed and why

This section documents the fixes applied in response to a Phase 1 review.

### 1. Embedding dimension consistency

**Problem:** tests used `dims=128`, the DB column and container used `256`
— three independent hardcoded numbers that could silently drift.

**Fix:** `app/core/constants.py` defines `EMBEDDING_DIMENSIONS` once, read
from the `EMBEDDING_DIMENSIONS` env var (default `256`). It exists as a
separate module from `Settings` only because SQLAlchemy's `Vector(N)` column
type needs a concrete `int` at class-definition/import time, before a
request-scoped `Settings` object exists — both read the *same* env var and
default, so they cannot drift in practice, and `test_constants_and_settings_agree_on_embedding_dimensions`
asserts they agree at runtime. Every other file — the composition root's
`DevStubEmbeddingProvider`, the `story_dna.embedding` column, the Alembic
migration, and `tests/originality/conftest.py` — imports this one constant.
`OriginalityEngine.check()` also now defensively raises
`EmbeddingDimensionMismatchError` if a provider's declared `.dimensions`
doesn't match what `.embed()` actually returned, or if a stored embedding's
length doesn't match the current provider's output — turning a silent
correctness bug into a loud, named, catchable error.

### 2. Originality match consistency

**Problem:** the engine computed structural conflicts across *all* nearest
neighbors but built the explanation from whichever comparison had the
highest blended score — so a hard-reject could cite conflicts from one story
while `most_similar_story_id` pointed at a different one.

**Fix:** `OriginalityEngine.check()` now picks exactly one **decisive**
comparison: if any neighbor triggers the structural conflict guard, the
neighbor with the most conflicting dimensions (ties broken by blended score)
is decisive and forces `HARD_REJECT`; otherwise the highest-blended-score
neighbor is decisive. Every field on the returned `OriginalityDecision` —
`most_similar_story_id`, `overall_similarity`, `conflicts`, `explanation`,
`recommendation` — is derived from that single decisive comparison, never
merged across neighbors. Regression test:
`tests/originality/test_conflict_guard.py::test_decision_never_mixes_conflicts_from_different_matches`,
which seeds two neighbors (one structurally near-duplicate, one merely
semantically similar) and asserts the decision is fully attributable to one.

### 3. Test count and execution

**I did not run pytest — this sandbox has no network access and none of
pydantic/fastapi/sqlalchemy/pytest/anthropic installed, and no way to
install them.** See the exact commands to run yourself at the top of this
README. Do not trust a "N passed" claim from me for this project; trust your
own terminal output.

### 4. Database validation

Reviewed `alembic/versions/0001_initial_schema.py` against
`apps/api/app/models/story.py` field-by-field:
- `storystatus` enum: 9 values, identical order, in both places.
- `story_dna.story_id`: `ForeignKey("stories.id", ondelete="CASCADE")`,
  `unique=True` in both the model and the migration (1:1 relationship).
- `performance_metrics.story_id`: `CASCADE` FK, no unique constraint, in both.
- `story_dna.embedding`: `Vector(EMBEDDING_DIMENSIONS)` in both, plus an
  `hnsw (embedding vector_cosine_ops)` index, matching `PgVectorStore`'s use
  of `.cosine_distance()`.
- Timestamps (`created_at`, `updated_at`, `published_at`, `recorded_at`):
  Python-side defaults (`default=datetime.utcnow`) in the model, matched by
  `nullable=False` with no `server_default` in the migration — correct since
  every insert goes through the ORM, which always sets these before flush.

No schema drift found between the model and the migration; this was static
review only (no live Postgres available to actually apply the migration).

### 5. API validation

`tests/api/test_api.py` now covers `GET /health`, `POST /stories`,
`GET /stories/{id}` (found + 404 + malformed-UUID), and
`POST /originality/check` (approved + malformed-DNA-422), using FastAPI's
`dependency_overrides` with a `FakeAsyncSession` double — no live Postgres
required. The whole module uses `pytest.importorskip` for fastapi/httpx/
sqlalchemy so it reports an explicit skip reason rather than erroring if
those aren't installed (as they aren't, in this sandbox).

`apps/api/app/core/deps.py` adds a `get_vector_store` dependency so
`/originality/check` no longer hardcodes `PgVectorStore` in the router —
tests can override it with `InMemoryVectorStore` if they need to seed
existing stories without a DB (the current tests exercise the "no existing
stories" path through the fake session instead, which is sufficient for
what's being asserted).

### 6. Provider abstraction boundary

Verified: `anthropic` is imported in exactly two places —
`provider_abstractions/impl/anthropic_llm.py` (the concrete implementation)
and `apps/api/app/core/container.py` (the composition root). No engine,
router, or business-logic module imports it. `AnthropicLLMProvider.__init__`
no longer reads `os.environ` as a fallback — it requires `api_key` to be
passed explicitly, which only the composition root does (reading it from
`Settings`).

### 7. Error handling

- `POST/GET /stories`: malformed UUID → `400`, not an uncaught `ValueError`;
  DB errors (`SQLAlchemyError`) → `503`, not an uncaught exception.
- `POST /originality/check`: DB errors → `503`; missing `ANTHROPIC_API_KEY`
  (`ProviderConfigurationError`) → `503`; embedding dimension drift
  (`EmbeddingDimensionMismatchError`) → `500` with a diagnostic message;
  malformed DNA → `422` (both via explicit pydantic `ValidationError`
  handling and FastAPI's own request-body validation).
- Malformed LLM JSON output: `AnthropicLLMProvider.generate()` raises the
  named `LLMOutputParsingError` (a `RuntimeError` subclass) instead of
  letting a raw `json.JSONDecodeError`/`pydantic.ValidationError` propagate
  unlabeled.

### 8. Configuration

`apps/api/app/core/config.py` (`Settings`, `pydantic-settings`) is the
single source for `database_url`, `redis_url`, `anthropic_api_key`,
`anthropic_model`, `embedding_dimensions`, and the originality thresholds.
`apps/api/app/core/constants.py` holds the one necessarily-separate
`EMBEDDING_DIMENSIONS` constant (see item 1). Confirmed via `grep` that no
other file reads `os.environ` directly.

## What's real vs. stub

| Component | Status |
|---|---|
| Story DNA schema, Originality Engine (incl. decisive-match fix), Conflict Guard, Differentiator | **Real**, unit-tested (pending your `pytest` run) |
| Content Quality Gate | **Real**, unit-tested |
| DB models + Alembic migration | **Real** schema, statically cross-checked against the model, never applied to a live DB from this sandbox |
| `PgVectorStore` | **Real** implementation, untested against a live DB |
| `AnthropicLLMProvider` | **Real**, calls the actual Anthropic API — needs `ANTHROPIC_API_KEY` |
| `DevStubEmbeddingProvider` | **Explicitly dev-only**, labeled in its docstring — deterministic hash-based pseudo-embedding. Swap for a real embedding provider before production. |
| `GET /health`, `POST /stories`, `GET /stories/{id}`, `POST /originality/check` | **Real**, minimal, no auth yet (Phase 10) |
| Everything from Phase 2 onward | **Not built** |

## Repository layout

```
horror-shorts-studio/
├── apps/api/app/
│   ├── core/            # config.py (Settings), constants.py (EMBEDDING_DIMENSIONS),
│   │                     container.py (composition root), deps.py (FastAPI DI)
│   ├── routers/         # stories.py, originality.py
│   ├── models/          # SQLAlchemy: Story, StoryDNAModel, PerformanceMetric
│   ├── db/               # base.py, session.py, pgvector_store.py
│   └── schemas/         # pydantic request/response models
├── packages/
│   ├── shared_types/        # StoryDNA, OriginalityDecision
│   ├── provider_abstractions/  # interfaces + Anthropic/dev-stub impls
│   ├── originality_engine/  # similarity, conflict_guard, vector_store, engine, differentiator
│   └── story_engine/        # ContentQualityGate
├── alembic/versions/0001_initial_schema.py
├── tests/
│   ├── originality/      # engine, conflict guard, quality gate, differentiator
│   └── api/              # API tests + embedding-dimension-consistency tests
└── docker-compose.yml
```

## Roadmap (unchanged)

Phase 1 (hardened, this delivery) → Phase 2: Viral & Retention Engine →
Phase 3: Story Engine → Phase 4: Scene Engine → Phase 5: Provider
integrations → Phase 6: Video/FFmpeg rendering → Phase 7: Editor (Next.js) →
Phase 8: Analytics → Phase 9: Long-form expansion → Phase 10: Production
hardening (auth, rate limiting, secrets).

**Say "start Phase 2" once you've run `pytest tests/ -v` yourself and are
satisfied with the actual results.**
