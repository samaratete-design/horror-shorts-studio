"""
Verifies EMBEDDING_DIMENSIONS is a true single source of truth:
app.core.constants (used by the SQLAlchemy/pgvector column), app.core.config
(used by the composition root's DevStubEmbeddingProvider), and an actual
constructed embedding provider must all agree.

This does NOT require a live database - it only imports the constant/config
modules and constructs a provider, then checks dimensions line up.
"""
from app.core.constants import EMBEDDING_DIMENSIONS
from app.core.config import get_settings
from provider_abstractions.impl.dev_embedding import DevStubEmbeddingProvider


def test_constants_and_settings_agree_on_embedding_dimensions():
    settings = get_settings()
    assert settings.embedding_dimensions == EMBEDDING_DIMENSIONS, (
        "app.core.config.Settings.embedding_dimensions and app.core.constants.EMBEDDING_DIMENSIONS "
        "have drifted apart - they must read the same EMBEDDING_DIMENSIONS env var/default."
    )


def test_dev_stub_provider_built_from_settings_matches_declared_dimension():
    settings = get_settings()
    provider = DevStubEmbeddingProvider(dims=settings.embedding_dimensions)
    assert provider.dimensions == EMBEDDING_DIMENSIONS


async def test_dev_stub_provider_actual_output_matches_declared_dimension():
    settings = get_settings()
    provider = DevStubEmbeddingProvider(dims=settings.embedding_dimensions)
    vector = await provider.embed("a test story premise")
    assert len(vector) == provider.dimensions == EMBEDDING_DIMENSIONS


def test_story_dna_model_column_matches_configured_dimension():
    """
    Confirms the SQLAlchemy/pgvector column literally uses the same constant
    (not a separately hardcoded number) by inspecting the mapped column type.
    Requires sqlalchemy + pgvector to be importable; skipped otherwise since
    this sandbox may not have them installed (see README - no network access
    when this suite was authored).
    """
    import pytest

    sqlalchemy = pytest.importorskip("sqlalchemy")
    pytest.importorskip("pgvector")

    from app.models.story import StoryDNAModel

    column = StoryDNAModel.__table__.columns["embedding"]
    assert column.type.dim == EMBEDDING_DIMENSIONS
