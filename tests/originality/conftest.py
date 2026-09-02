import pytest

from provider_abstractions.impl.dev_embedding import DevStubEmbeddingProvider
from originality_engine.vector_store import InMemoryVectorStore
from originality_engine.engine import OriginalityEngine, OriginalityThresholds
from shared_types.story_dna import StoryDNA, POV, TwistType, EndingType

# Single source of truth for embedding dimensionality in tests, matching the
# same EMBEDDING_DIMENSIONS the DB column / composition root use (see
# app/core/constants.py). Importing it here - rather than hardcoding a
# number like 128 or 256 - means tests can never drift from production
# configuration.
from app.core.constants import EMBEDDING_DIMENSIONS


@pytest.fixture
def embedding_provider():
    return DevStubEmbeddingProvider(dims=EMBEDDING_DIMENSIONS)


@pytest.fixture
def vector_store():
    return InMemoryVectorStore()


@pytest.fixture
def engine(embedding_provider, vector_store):
    return OriginalityEngine(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        thresholds=OriginalityThresholds(approve_below=0.50, hard_reject_above=0.70),
    )


def make_dna(**overrides) -> StoryDNA:
    base = dict(
        premise="A woman discovers her reflection is delayed by a few seconds.",
        setting="a small apartment bathroom",
        threat="a delayed, autonomous reflection",
        fear_mechanism="uncanny_valley",
        narrative_device="mirror",
        twist_type=TwistType.RECONTEXTUALIZATION,
        ending_type=EndingType.AMBIGUOUS,
        pov=POV.FIRST_PERSON,
        conflict="she must figure out if the reflection is warning her or replacing her",
        emotional_theme="loss of identity",
        core_fear="losing control of your own body/identity",
        unique_story_hook="the delay increases by exactly one second every night",
    )
    base.update(overrides)
    return StoryDNA(**base)


async def seed(engine: OriginalityEngine, vector_store: InMemoryVectorStore, story_id: str, dna: StoryDNA):
    """Embed + store a DNA so future originality checks can match against it."""
    embedding = await engine._embeddings.embed(engine._dna_to_text(dna))
    dna_with_embedding = dna.model_copy(update={"embedding": embedding})
    await vector_store.upsert(story_id, dna_with_embedding)
    return dna_with_embedding
