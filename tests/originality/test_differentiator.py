import pytest

from provider_abstractions.interfaces import LLMProvider
from originality_engine.differentiator import StoryDifferentiator, _MutatedDimensions
from shared_types.originality import OriginalityVerdict
from tests.originality.conftest import make_dna, seed

pytestmark = pytest.mark.asyncio


class FakeMutatingLLM(LLMProvider):
    """Deterministically 'mutates' flagged dimensions by appending a unique suffix,
    simulating what a real LLM call would return - without any network access."""

    def __init__(self):
        self.call_count = 0

    async def generate(self, prompt, system=None, schema=None, max_tokens=2000, temperature=1.0):
        self.call_count += 1
        assert schema is _MutatedDimensions

        # crude parse of "MUST be changed" dimension list from the prompt for the test double
        values = {}
        for dim in ["setting", "threat", "fear_mechanism", "narrative_device",
                    "twist_type", "ending_type", "pov", "core_fear",
                    "premise", "unique_story_hook"]:
            if dim in prompt:
                values[dim] = f"mutated_{dim}_variant_{self.call_count}"
        return _MutatedDimensions(values=values)


async def test_differentiator_mutates_only_conflicting_dimensions(engine, vector_store):
    original = make_dna()
    await seed(engine, vector_store, "story-1", original)

    candidate = make_dna()  # exact duplicate -> hard reject
    decision = await engine.check(candidate)
    assert decision.verdict == OriginalityVerdict.HARD_REJECT

    fake_llm = FakeMutatingLLM()
    differentiator = StoryDifferentiator(llm=fake_llm, originality_engine=engine, max_attempts=3)

    result = await differentiator.differentiate(candidate, decision)

    assert fake_llm.call_count >= 1
    # premise (not flagged as a structural dimension) should be preserved on first attempt
    # unless it was also part of the conflict set.
    assert result.attempts[0].dna.protagonist_archetype == candidate.protagonist_archetype


async def test_differentiator_returns_immediately_if_already_approved(engine, vector_store):
    candidate = make_dna()
    decision = await engine.check(candidate)  # no existing stories -> approved
    assert decision.verdict == OriginalityVerdict.APPROVED

    fake_llm = FakeMutatingLLM()
    differentiator = StoryDifferentiator(llm=fake_llm, originality_engine=engine)

    result = await differentiator.differentiate(candidate, decision)

    assert result.success is True
    assert fake_llm.call_count == 0
