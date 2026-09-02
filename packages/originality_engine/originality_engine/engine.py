"""
OriginalityEngine

Pipeline (per spec):
  Idea -> Story DNA Candidate -> Embedding -> Vector Search
       -> Structural Similarity -> Semantic Similarity -> Originality Decision

Thresholds (configurable, defaults per spec):
  < 0.50            APPROVED
  0.50 - 0.70       REWRITE
  > 0.70            HARD_REJECT
  (independently) 4+ important structural-dimension conflicts -> HARD_REJECT
  regardless of the blended score.
"""
from dataclasses import dataclass, field

from provider_abstractions.interfaces import EmbeddingProvider
from shared_types.story_dna import StoryDNA
from shared_types.originality import OriginalityDecision, OriginalityVerdict, DimensionConflict

from originality_engine.similarity import structural_similarity, weighted_structural_score, cosine_similarity
from originality_engine.conflict_guard import find_conflicts
from originality_engine.vector_store import VectorStore


@dataclass
class OriginalityThresholds:
    approve_below: float = 0.50
    hard_reject_above: float = 0.70


@dataclass
class _CandidateComparison:
    story_id: str
    structural_score: float
    semantic_score: float
    blended_score: float
    conflicts: list[DimensionConflict] = field(default_factory=list)
    structural_conflict_triggered: bool = False


class EmbeddingDimensionMismatchError(ValueError):
    """
    Raised when a vector produced by the configured EmbeddingProvider does
    not match the dimensionality of a vector already stored (e.g. the DB
    column, or another provider's output). This should never happen if
    EMBEDDING_DIMENSIONS is configured consistently everywhere - see
    app/core/constants.py - so hitting this is a real configuration bug,
    not something to silently coerce or ignore.
    """


class OriginalityEngine:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        thresholds: OriginalityThresholds | None = None,
        top_k: int = 15,
        semantic_weight: float = 0.5,
    ):
        self._embeddings = embedding_provider
        self._store = vector_store
        self._thresholds = thresholds or OriginalityThresholds()
        self._top_k = top_k
        # blended_score = semantic_weight * semantic + (1 - semantic_weight) * structural
        self._semantic_weight = semantic_weight

    async def check(self, candidate: StoryDNA) -> OriginalityDecision:
        text_repr = self._dna_to_text(candidate)
        embedding = await self._embeddings.embed(text_repr)

        if len(embedding) != self._embeddings.dimensions:
            raise EmbeddingDimensionMismatchError(
                f"EmbeddingProvider.embed() returned a {len(embedding)}-dim vector but "
                f"EmbeddingProvider.dimensions reports {self._embeddings.dimensions}. "
                "This provider is misconfigured."
            )

        candidate = candidate.model_copy(update={"embedding": embedding})

        matches = await self._store.nearest(embedding, top_k=self._top_k)

        for m in matches:
            if m.dna.embedding is not None and len(m.dna.embedding) != len(embedding):
                raise EmbeddingDimensionMismatchError(
                    f"Stored embedding for story '{m.story_id}' has {len(m.dna.embedding)} dimensions "
                    f"but the current EmbeddingProvider produces {len(embedding)}-dim vectors. "
                    "EMBEDDING_DIMENSIONS must be identical across the DB schema, provider configuration, "
                    "and vector store - check app/core/constants.py and app/core/config.py."
                )

        if not matches:
            return OriginalityDecision(
                verdict=OriginalityVerdict.APPROVED,
                overall_similarity=0.0,
                explanation="No existing stories to compare against. Approved by default.",
            )

        comparisons = [self._compare(candidate, m.story_id, m.dna, m.similarity) for m in matches]

        # Pick ONE decisive comparison and base the entire decision on it, so
        # most_similar_story_id / conflicts / explanation / recommendation
        # never mix signals from different candidate stories.
        #
        # Priority: a comparison that independently triggers the structural
        # conflict guard always wins (it forces HARD_REJECT regardless of
        # blended score), because a hard-reject reason must be explainable
        # by a single concrete match. Among multiple structurally-triggered
        # comparisons, the one with the most conflicting dimensions wins;
        # ties broken by blended score. If none trigger structurally, the
        # highest blended-score comparison is decisive.
        structurally_triggered = [c for c in comparisons if c.structural_conflict_triggered]
        if structurally_triggered:
            decisive = max(
                structurally_triggered,
                key=lambda c: (len(c.conflicts), c.blended_score),
            )
        else:
            decisive = max(comparisons, key=lambda c: c.blended_score)

        if decisive.structural_conflict_triggered or decisive.blended_score > self._thresholds.hard_reject_above:
            verdict = OriginalityVerdict.HARD_REJECT
        elif decisive.blended_score >= self._thresholds.approve_below:
            verdict = OriginalityVerdict.REWRITE
        else:
            verdict = OriginalityVerdict.APPROVED

        explanation = self._explain(verdict, decisive, decisive.structural_conflict_triggered)
        recommendation = self._recommend(verdict, decisive) if verdict != OriginalityVerdict.APPROVED else None

        return OriginalityDecision(
            verdict=verdict,
            overall_similarity=round(decisive.blended_score, 3),
            most_similar_story_id=decisive.story_id,
            # Conflicts are scoped ONLY to the decisive match - never merged
            # across unrelated nearest-neighbor stories.
            conflicts=sorted(decisive.conflicts, key=lambda c: c.similarity, reverse=True)[:10],
            structural_conflict_triggered=decisive.structural_conflict_triggered,
            explanation=explanation,
            recommendation=recommendation,
        )

    def _compare(
        self, candidate: StoryDNA, story_id: str, existing: StoryDNA, vector_similarity: float
    ) -> _CandidateComparison:
        dim_scores = structural_similarity(candidate, existing)
        structural_score = weighted_structural_score(dim_scores)

        semantic_score = vector_similarity
        if candidate.embedding and existing.embedding:
            semantic_score = cosine_similarity(candidate.embedding, existing.embedding)

        blended = self._semantic_weight * semantic_score + (1 - self._semantic_weight) * structural_score

        conflict_result = find_conflicts(candidate, existing, story_id, dim_scores)

        return _CandidateComparison(
            story_id=story_id,
            structural_score=structural_score,
            semantic_score=semantic_score,
            blended_score=blended,
            conflicts=conflict_result.conflicts,
            structural_conflict_triggered=conflict_result.triggered,
        )

    @staticmethod
    def _dna_to_text(dna: StoryDNA) -> str:
        return (
            f"{dna.premise}. Setting: {dna.setting}. Threat: {dna.threat}. "
            f"Fear mechanism: {dna.fear_mechanism}. Narrative device: {dna.narrative_device}. "
            f"Twist: {dna.twist_type}. Ending: {dna.ending_type}. POV: {dna.pov}. "
            f"Core fear: {dna.core_fear}. Conflict: {dna.conflict}. Hook: {dna.unique_story_hook}."
        )

    @staticmethod
    def _explain(verdict: OriginalityVerdict, top: _CandidateComparison, structural_triggered: bool) -> str:
        pct = round(top.blended_score * 100)
        if verdict == OriginalityVerdict.APPROVED:
            return f"Similarity to closest existing story: {pct}%. No significant overlap detected."

        lines = [f"Similarity: {pct}%"]
        if structural_triggered:
            lines.append(
                f"Structural conflict triggered: {len(top.conflicts)} dimensions match story {top.story_id} "
                "closely enough to be considered a near-duplicate, independent of the overall score."
            )
        if top.conflicts:
            lines.append("Conflicts:")
            for c in top.conflicts:
                lines.append(f"- Same {c.dimension.replace('_', ' ')} ({c.candidate_value})")
        return "\n".join(lines)

    @staticmethod
    def _recommend(verdict: OriginalityVerdict, top: _CandidateComparison) -> str:
        conflicting_dims = sorted({c.dimension for c in top.conflicts})
        if not conflicting_dims:
            return "Increase distinctiveness of the premise, hook, and conflict."
        readable = ", ".join(d.replace("_", " ") for d in conflicting_dims)
        severity = "Change" if verdict == OriginalityVerdict.HARD_REJECT else "Consider changing"
        return f"{severity} the following dimensions: {readable}. Do not simply reword existing text."
