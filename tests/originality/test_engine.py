import pytest

from shared_types.originality import OriginalityVerdict
from originality_engine.engine import OriginalityEngine, EmbeddingDimensionMismatchError
from originality_engine.vector_store import InMemoryVectorStore
from tests.originality.conftest import make_dna, seed

pytestmark = pytest.mark.asyncio


async def test_no_existing_stories_approves_by_default(engine):
    candidate = make_dna()
    decision = await engine.check(candidate)
    assert decision.verdict == OriginalityVerdict.APPROVED


async def test_exact_duplicate_is_hard_rejected(engine, vector_store):
    original = make_dna()
    await seed(engine, vector_store, "story-1", original)

    candidate = make_dna()  # identical DNA
    decision = await engine.check(candidate)

    assert decision.verdict == OriginalityVerdict.HARD_REJECT
    assert decision.most_similar_story_id == "story-1"
    assert decision.overall_similarity > 0.70


async def test_renamed_character_duplicate_is_rejected(engine, vector_store):
    """Same structural DNA, different surface wording - should still be caught."""
    original = make_dna(
        premise="A woman discovers her reflection is delayed by a few seconds.",
        unique_story_hook="the delay increases by exactly one second every night",
    )
    await seed(engine, vector_store, "story-1", original)

    candidate = make_dna(
        premise="A man notices his mirror image lags behind him by a couple seconds.",
        unique_story_hook="the lag grows by one more second each night, always",
    )
    decision = await engine.check(candidate)

    assert decision.verdict in (OriginalityVerdict.REWRITE, OriginalityVerdict.HARD_REJECT)


async def test_changed_setting_alone_is_not_enough_to_pass(engine, vector_store):
    """Changing only the setting while keeping threat/twist/ending/pov/core_fear
    identical should still trigger the structural conflict guard."""
    original = make_dna(setting="a small apartment bathroom")
    await seed(engine, vector_store, "story-1", original)

    candidate = make_dna(setting="an abandoned lighthouse bathroom")
    decision = await engine.check(candidate)

    assert decision.verdict == OriginalityVerdict.HARD_REJECT
    assert decision.structural_conflict_triggered is True


async def test_changed_threat_and_setting_reduces_conflict(engine, vector_store):
    original = make_dna()
    await seed(engine, vector_store, "story-1", original)

    candidate = make_dna(
        setting="a crowded subway car at midnight",
        threat="a stranger who mimics your movements exactly one step later",
        narrative_device="security camera footage",
        fear_mechanism="loss_of_anonymity",
    )
    decision = await engine.check(candidate)

    # Should be meaningfully less similar than the exact-duplicate case.
    duplicate_decision_similarity = 1.0  # exact duplicate case asserted separately
    assert decision.overall_similarity < duplicate_decision_similarity


async def test_sufficiently_different_story_is_approved(engine, vector_store):
    original = make_dna()
    await seed(engine, vector_store, "story-1", original)

    candidate = make_dna(
        premise="A lighthouse keeper's radio picks up his own future distress call.",
        setting="an isolated coastal lighthouse",
        threat="a radio broadcast from his own future",
        fear_mechanism="inevitability",
        narrative_device="shortwave radio transmissions",
        twist_type="time_loop",
        ending_type="full_circle",
        pov="third_person_limited",
        conflict="he must decide whether trying to change the future causes it",
        emotional_theme="fatalism",
        core_fear="being unable to escape your own fate",
        unique_story_hook="the transmission timestamp is always exactly 40 years ahead",
    )
    decision = await engine.check(candidate)

    assert decision.verdict == OriginalityVerdict.APPROVED


async def test_false_positive_guard_different_unrelated_stories(engine, vector_store):
    """Two genuinely different horror premises should not falsely conflict."""
    story_a = make_dna(
        premise="A babysitter keeps receiving calls from inside the house.",
        setting="a suburban house",
        threat="an intruder already inside",
        fear_mechanism="violation_of_safe_space",
        narrative_device="phone calls",
        twist_type="identity_reveal",
        ending_type="cliffhanger",
        core_fear="the home not being safe",
        unique_story_hook="the caller ID shows the babysitter's own number",
    )
    await seed(engine, vector_store, "story-1", story_a)

    story_b = make_dna(
        premise="An archaeologist translates a warning that predates the language itself.",
        setting="a desert excavation site",
        threat="an ancient inscription that changes each time it is read",
        fear_mechanism="forbidden_knowledge",
        narrative_device="ancient text/inscriptions",
        twist_type="nested_reality",
        ending_type="open_loop",
        core_fear="knowledge that cannot be unlearned",
        unique_story_hook="the translation is different for every person who reads it",
    )
    decision = await engine.check(story_b)

    assert decision.verdict == OriginalityVerdict.APPROVED


async def test_configurable_thresholds_are_respected():
    from provider_abstractions.impl.dev_embedding import DevStubEmbeddingProvider
    from originality_engine.vector_store import InMemoryVectorStore
    from originality_engine.engine import OriginalityEngine, OriginalityThresholds
    from app.core.constants import EMBEDDING_DIMENSIONS

    embedding_provider = DevStubEmbeddingProvider(dims=EMBEDDING_DIMENSIONS)
    vector_store = InMemoryVectorStore()
    strict_engine = OriginalityEngine(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        thresholds=OriginalityThresholds(approve_below=0.10, hard_reject_above=0.20),
    )

    original = make_dna()
    await seed(strict_engine, vector_store, "story-1", original)

    # Even a moderately different candidate should fail under very strict thresholds.
    candidate = make_dna(setting="a different apartment bathroom entirely")
    decision = await strict_engine.check(candidate)

    assert decision.verdict != OriginalityVerdict.APPROVED


async def test_embedding_provider_dimension_self_mismatch_is_detected(vector_store):
    """A provider whose .dimensions property lies about its actual output length
    must be caught immediately, not silently produce garbage similarity scores."""

    class LyingEmbeddingProvider:
        """DEV-ONLY test double: claims 256 dims but returns 10."""

        @property
        def dimensions(self) -> int:
            return 256

        async def embed(self, text: str) -> list[float]:
            return [0.1] * 10

        async def embed_batch(self, texts: list[str]) -> list[list[float]]:
            return [await self.embed(t) for t in texts]

    engine = OriginalityEngine(embedding_provider=LyingEmbeddingProvider(), vector_store=vector_store)

    with pytest.raises(EmbeddingDimensionMismatchError):
        await engine.check(make_dna())


async def test_stored_embedding_dimension_mismatch_is_detected(embedding_provider):
    """Simulates stale/misconfigured stored vectors (e.g. DB column resized without
    re-embedding existing rows) - must raise rather than silently return distorted
    cosine-similarity scores."""
    store = InMemoryVectorStore()
    engine = OriginalityEngine(embedding_provider=embedding_provider, vector_store=store)

    stale_dna = make_dna()
    # Simulate a row embedded under a different EMBEDDING_DIMENSIONS configuration.
    stale_dna = stale_dna.model_copy(update={"embedding": [0.1] * 8})
    await store.upsert("story-stale", stale_dna)

    with pytest.raises(EmbeddingDimensionMismatchError):
        await engine.check(make_dna())
