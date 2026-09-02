"""
Centralized configuration.

This is the ONLY place that reads os.environ. Every other module receives
configuration values as arguments or via this Settings object - no scattered
os.environ.get() calls anywhere else in the codebase.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "dev"  # dev | test | staging | production

    # Database
    database_url: str = "postgresql+asyncpg://horror:horror@localhost:5432/horror_shorts_studio"
    database_url_sync: str | None = None  # used by Alembic; derived from database_url if unset

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # LLM provider
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # Embedding provider - SINGLE SOURCE OF TRUTH for vector dimensionality.
    # The DB column (Vector(N)), the vector store, the embedding provider,
    # and tests must all read this value rather than hardcoding a number.
    embedding_dimensions: int = 256

    # Originality Engine thresholds
    originality_approve_below: float = 0.50
    originality_hard_reject_above: float = 0.70

    def resolved_sync_database_url(self) -> str:
        if self.database_url_sync:
            return self.database_url_sync
        return self.database_url.replace("+asyncpg", "")


@lru_cache
def get_settings() -> Settings:
    return Settings()
