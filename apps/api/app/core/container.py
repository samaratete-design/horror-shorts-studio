"""
Composition root.

This is the ONLY place in the application that imports concrete provider
implementations. Everything else (routers, engines) depends solely on the
abstract interfaces from provider_abstractions.interfaces.

Swapping LLM/embedding/image/voice providers means changing this file only.
All configuration values come from app.core.config.Settings - no direct
os.environ access here.
"""
from functools import lru_cache

from provider_abstractions.interfaces import LLMProvider, EmbeddingProvider
from provider_abstractions.impl.anthropic_llm import AnthropicLLMProvider
from provider_abstractions.impl.dev_embedding import DevStubEmbeddingProvider

from originality_engine.engine import OriginalityEngine, OriginalityThresholds
from originality_engine.vector_store import InMemoryVectorStore, VectorStore
from originality_engine.differentiator import StoryDifferentiator

from app.core.config import get_settings


class ProviderConfigurationError(RuntimeError):
    """Raised when a provider is requested but required configuration is missing."""


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if not settings.anthropic_api_key:
        raise ProviderConfigurationError(
            "ANTHROPIC_API_KEY is not configured. Set it in the environment or .env file."
        )
    return AnthropicLLMProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    # *** DEV STUB *** - swap for a real embedding provider before production.
    # See provider_abstractions/impl/dev_embedding.py for the swap-out note.
    # Dimensions come from the single configured source (Settings.embedding_dimensions),
    # matching the DB column and every vector store / test that consumes embeddings.
    settings = get_settings()
    return DevStubEmbeddingProvider(dims=settings.embedding_dimensions)


@lru_cache
def get_dev_vector_store() -> VectorStore:
    """In-memory store used only when ENVIRONMENT=dev/test. Production uses PgVectorStore per-request."""
    return InMemoryVectorStore()


def get_originality_thresholds() -> OriginalityThresholds:
    settings = get_settings()
    return OriginalityThresholds(
        approve_below=settings.originality_approve_below,
        hard_reject_above=settings.originality_hard_reject_above,
    )


def build_originality_engine(vector_store: VectorStore) -> OriginalityEngine:
    return OriginalityEngine(
        embedding_provider=get_embedding_provider(),
        vector_store=vector_store,
        thresholds=get_originality_thresholds(),
    )


def build_differentiator(originality_engine: OriginalityEngine) -> StoryDifferentiator:
    return StoryDifferentiator(llm=get_llm_provider(), originality_engine=originality_engine)
