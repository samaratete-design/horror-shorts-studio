"""
Vector store abstraction used by the Originality Engine to find candidate
"nearest neighbor" stories before running full structural/semantic
comparison. Decoupled from Postgres/pgvector so the engine is testable
without a database.

Production implementation: apps/api/app/db/pgvector_store.py (uses pgvector's
<-> operator against the story_dna.embedding column).
Dev/test implementation: InMemoryVectorStore below.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

from shared_types.story_dna import StoryDNA
from originality_engine.similarity import cosine_similarity


@dataclass
class VectorMatch:
    story_id: str
    dna: StoryDNA
    similarity: float


class VectorStore(ABC):
    @abstractmethod
    async def upsert(self, story_id: str, dna: StoryDNA) -> None:
        raise NotImplementedError

    @abstractmethod
    async def nearest(self, embedding: list[float], top_k: int = 10) -> list[VectorMatch]:
        raise NotImplementedError


class InMemoryVectorStore(VectorStore):
    """Dev/test implementation. Not for production (no persistence, O(n) scan)."""

    def __init__(self):
        self._entries: dict[str, StoryDNA] = {}

    async def upsert(self, story_id: str, dna: StoryDNA) -> None:
        self._entries[story_id] = dna

    async def nearest(self, embedding: list[float], top_k: int = 10) -> list[VectorMatch]:
        scored = [
            VectorMatch(story_id=sid, dna=dna, similarity=cosine_similarity(embedding, dna.embedding or []))
            for sid, dna in self._entries.items()
            if dna.embedding is not None
        ]
        scored.sort(key=lambda m: m.similarity, reverse=True)
        return scored[:top_k]

    async def all(self) -> list[tuple[str, StoryDNA]]:
        return list(self._entries.items())
