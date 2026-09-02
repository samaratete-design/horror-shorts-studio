"""
Structural conflict guard.

A candidate can have a merely-moderate blended similarity score while still
being an obvious near-duplicate, if it matches on the dimensions that most
define a story's identity (e.g. same setting + same threat + same twist +
same POV, but a different opening line). This guard catches that case
independently of the overall semantic similarity score.
"""
from dataclasses import dataclass

from shared_types.story_dna import StoryDNA
from shared_types.originality import DimensionConflict

# A dimension "conflicts" if its similarity is at/above this bar.
CONFLICT_THRESHOLD = 0.82

# If this many (or more) important dimensions conflict, force a hard reject
# regardless of the blended/global similarity score.
STRUCTURAL_CONFLICT_COUNT = 4

# Only these dimensions count toward the structural-conflict count; minor
# dimensions like POV alone shouldn't be able to trigger a hard reject.
IMPORTANT_DIMENSIONS = {
    "setting",
    "threat",
    "fear_mechanism",
    "narrative_device",
    "twist_type",
    "ending_type",
    "core_fear",
}


@dataclass
class ConflictCheckResult:
    conflicts: list[DimensionConflict]
    important_conflict_count: int
    triggered: bool


def find_conflicts(
    candidate: StoryDNA,
    existing: StoryDNA,
    existing_story_id: str,
    dim_scores: dict[str, float],
) -> ConflictCheckResult:
    conflicts: list[DimensionConflict] = []
    important_count = 0

    for dimension, score in dim_scores.items():
        if score >= CONFLICT_THRESHOLD:
            conflicts.append(
                DimensionConflict(
                    dimension=dimension,
                    candidate_value=str(getattr(candidate, dimension)),
                    matched_value=str(getattr(existing, dimension)),
                    matched_story_id=existing_story_id,
                    similarity=round(score, 3),
                )
            )
            if dimension in IMPORTANT_DIMENSIONS:
                important_count += 1

    return ConflictCheckResult(
        conflicts=conflicts,
        important_conflict_count=important_count,
        triggered=important_count >= STRUCTURAL_CONFLICT_COUNT,
    )
