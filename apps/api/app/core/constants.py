"""
Embedding dimension: single source of truth.

SQLAlchemy Column/Vector(N) types need a concrete int at class-definition
time (import time), before any request-scoped Settings object exists. To
avoid hardcoding that number in multiple files, it is read ONCE here from
the same environment variable / .env file that app.core.config.Settings
reads, using the same default (256).

Every other part of the app (provider composition root, tests) reads the
dimension from app.core.config.Settings.embedding_dimensions - which uses
the identical env var - so there is exactly one place a human sets this
number: EMBEDDING_DIMENSIONS in the environment/.env file.
"""
import os

EMBEDDING_DIMENSIONS: int = int(os.environ.get("EMBEDDING_DIMENSIONS", 256))
