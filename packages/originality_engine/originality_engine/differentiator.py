"""
StoryDifferentiator

When a candidate fails originality (REWRITE or HARD_REJECT):
  1. Identify the conflicting DNA dimensions.
  2. Ask the LLM to mutate exactly those dimensions (never a blind full
     regeneration - everything else about the story stays intact).
  3. Generate several alternative candidates.
  4. Re-run OriginalityEngine.check on each.
  5. Return the best passing candidate, or the closest-to-passing one if
     none pass within the attempt budget (caller decides what to do next).
"""
from dataclasses import dataclass

from pydantic import BaseModel

from provider_abstractions.interfaces import LLMProvider
from shared_types.story_dna import StoryDNA
from shared_types.originality import OriginalityDecision, OriginalityVerdict

from originality_engine.engine import OriginalityEngine


class _MutatedDimensions(BaseModel):
    """Schema the LLM must fill in - ONLY the requested dimensions."""

    values: dict[str, str]


@dataclass
class DifferentiationAttempt:
    dna: StoryDNA
    decision: OriginalityDecision


@dataclass
class DifferentiationResult:
    success: bool
    best: DifferentiationAttempt
    attempts: list[DifferentiationAttempt]


MUTATION_PROMPT_TEMPLATE = """You are revising a single horror story concept to make it structurally
distinct from an existing story it too closely resembles, WITHOUT discarding the parts of the
concept that already work.

Original concept dimensions:
{original_dna}

These specific dimensions were flagged as too similar to an existing story and MUST be changed
to something structurally different (not just reworded):
{conflicting_dimensions}

Keep every other dimension conceptually consistent with the original premise. Return ONLY the
new values for the flagged dimensions.
"""


class StoryDifferentiator:
    def __init__(self, llm: LLMProvider, originality_engine: OriginalityEngine, max_attempts: int = 3):
        self._llm = llm
        self._engine = originality_engine
        self._max_attempts = max_attempts

    async def differentiate(self, candidate: StoryDNA, decision: OriginalityDecision) -> DifferentiationResult:
        if decision.verdict == OriginalityVerdict.APPROVED:
            return DifferentiationResult(
                success=True,
                best=DifferentiationAttempt(dna=candidate, decision=decision),
                attempts=[DifferentiationAttempt(dna=candidate, decision=decision)],
            )

        conflicting_dims = sorted({c.dimension for c in decision.conflicts}) or ["premise", "unique_story_hook"]

        attempts: list[DifferentiationAttempt] = []
        current = candidate

        for _ in range(self._max_attempts):
            mutated = await self._mutate(current, conflicting_dims)
            new_decision = await self._engine.check(mutated)
            attempts.append(DifferentiationAttempt(dna=mutated, decision=new_decision))

            if new_decision.verdict == OriginalityVerdict.APPROVED:
                return DifferentiationResult(success=True, best=attempts[-1], attempts=attempts)

            # Feed forward: next mutation attempt targets whatever still conflicts.
            conflicting_dims = sorted({c.dimension for c in new_decision.conflicts}) or conflicting_dims
            current = mutated

        best = min(attempts, key=lambda a: a.decision.overall_similarity)
        return DifferentiationResult(success=False, best=best, attempts=attempts)

    async def _mutate(self, dna: StoryDNA, dimensions: list[str]) -> StoryDNA:
        prompt = MUTATION_PROMPT_TEMPLATE.format(
            original_dna=dna.model_dump_json(indent=2, exclude={"embedding", "id", "story_id"}),
            conflicting_dimensions=", ".join(dimensions),
        )
        result = await self._llm.generate(
            prompt=prompt,
            system="You output only the requested structured JSON. No commentary.",
            schema=_MutatedDimensions,
            temperature=1.0,
        )
        updates = {k: v for k, v in result.values.items() if hasattr(dna, k)}
        return dna.model_copy(update={**updates, "embedding": None})
