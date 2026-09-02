"""
Similarity primitives for the Originality Engine.

Deliberately avoids relying on one global embedding score. Two layers:

1. Structural similarity - exact/near-exact matches on discrete DNA
   dimensions (setting, threat, twist_type, etc). Cheap, explainable.
2. Semantic similarity - cosine similarity between free-text field
   embeddings, for catching paraphrased/renamed duplicates that structural
   comparison would miss.
"""
import math
from difflib import SequenceMatcher

from shared_types.story_dna import StoryDNA, STRUCTURAL_DIMENSIONS


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def text_similarity(a: str, b: str) -> float:
    """Lightweight lexical similarity for a single dimension's text values."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def dimension_similarity(candidate: StoryDNA, existing: StoryDNA, dimension: str) -> float:
    cand_val = str(getattr(candidate, dimension))
    exist_val = str(getattr(existing, dimension))

    # Enum-like categorical fields: exact match only (they're already normalized).
    if dimension in ("twist_type", "ending_type", "pov"):
        return 1.0 if cand_val == exist_val else 0.0

    return text_similarity(cand_val, exist_val)


def structural_similarity(candidate: StoryDNA, existing: StoryDNA) -> dict[str, float]:
    """Per-dimension similarity scores, dimension -> [0, 1]."""
    return {dim: dimension_similarity(candidate, existing, dim) for dim in STRUCTURAL_DIMENSIONS}


def weighted_structural_score(dim_scores: dict[str, float]) -> float:
    """
    Collapse per-dimension scores into a single structural score.
    twist_type and ending_type are weighted higher: a shared twist is a
    much stronger originality signal than a shared time period would be.
    """
    weights = {
        "setting": 1.0,
        "threat": 1.2,
        "fear_mechanism": 1.0,
        "narrative_device": 1.1,
        "twist_type": 1.5,
        "ending_type": 1.3,
        "pov": 0.5,
        "core_fear": 1.2,
    }
    total_weight = sum(weights.get(d, 1.0) for d in dim_scores)
    weighted_sum = sum(score * weights.get(dim, 1.0) for dim, score in dim_scores.items())
    return weighted_sum / total_weight if total_weight else 0.0
