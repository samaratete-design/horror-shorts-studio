"""
*** DEVELOPMENT-ONLY EMBEDDING PROVIDER ***

This is NOT production-ready. It produces a deterministic pseudo-embedding
using hashed n-gram bag-of-words + a fixed random projection, so that:

  - identical text -> identical vector (reproducible tests)
  - similar text -> loosely similar vector (cosine similarity is meaningful
    enough to exercise the Originality Engine's logic in tests/dev)

It has none of the semantic quality of a real embedding model. Before
production use, swap this for a real provider, e.g. VoyageEmbeddingProvider
or OpenAIEmbeddingProvider, by implementing EmbeddingProvider against that
API. Nothing else in the codebase needs to change - that's the point of the
provider abstraction.
"""
import hashlib
import math
import re

from provider_abstractions.interfaces import EmbeddingProvider

_TOKEN_RE = re.compile(r"[a-z0-9]+")


class DevStubEmbeddingProvider(EmbeddingProvider):
    """DEVELOPMENT-ONLY. Do not use in production.

    `dims` has no default here on purpose: the caller (composition root, or
    a test) must pass it explicitly from the single configured value
    (app.core.config.settings.embedding_dimensions) so it's impossible to
    silently drift from the DB column width.
    """

    def __init__(self, dims: int):
        self._dims = dims

    @property
    def dimensions(self) -> int:
        return self._dims

    async def embed(self, text: str) -> list[float]:
        return self._embed_sync(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_sync(t) for t in texts]

    def _embed_sync(self, text: str) -> list[float]:
        tokens = _TOKEN_RE.findall(text.lower())
        vec = [0.0] * self._dims
        if not tokens:
            return vec

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for i in range(self._dims):
                byte = digest[i % len(digest)]
                # Signed pseudo-random contribution per dimension per token.
                sign = 1.0 if (byte & 1) == 0 else -1.0
                vec[i] += sign * ((byte % 31) + 1)

        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]
