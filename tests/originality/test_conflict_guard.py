import pytest

from originality_engine.similarity import structural_similarity
from originality_engine.conflict_guard import find_conflicts, STRUCTURAL_CONFLICT_COUNT
from shared_types.originality import OriginalityVerdict
from tests.originality.conftest import make_dna, seed


def test_identical_dna_triggers_structural_conflict():
    candidate = make_dna()
    existing = make_dna()

    dim_scores = structural_similarity(candidate, existing)
    result = find_conflicts(candidate, existing, "story-1", dim_scores)

    assert result.triggered is True
    assert result.important_conflict_count >= STRUCTURAL_CONFLICT_COUNT


def test_single_shared_dimension_does_not_trigger():
    candidate = make_dna(pov="first_person")
    existing = make_dna(
        pov="first_person",
        setting="a completely different location, an office building",
        threat="a coworker who never blinks",
        narrative_device="security badge logs",
        twist_type="unreliable_narrator",
        ending_type="tragic",
        core_fear="not being believed",
        fear_mechanism="social_isolation",
    )

    dim_scores = structural_similarity(candidate, existing)
    result = find_conflicts(candidate, existing, "story-1", dim_scores)

    assert result.triggered is False


def test_conflict_list_includes_matched_story_id():
    candidate = make_dna()
    existing = make_dna()
    dim_scores = structural_similarity(candidate, existing)
    result = find_conflicts(candidate, existing, "story-42", dim_scores)

    assert all(c.matched_story_id == "story-42" for c in result.conflicts)


@pytest.mark.asyncio
async def test_decision_never_mixes_conflicts_from_different_matches(engine, vector_store):
    """
    Regression test for the match-consistency bug: with two nearest
    neighbors in the store - one that is a near-exact structural duplicate
    (low blended score because of a very different unrelated field) and one
    that has a higher raw blended similarity but does NOT structurally
    conflict - the final decision must be entirely attributable to a single
    decisive match. most_similar_story_id must be the story that actually
    produced the conflicts, and every conflict's matched_story_id must equal
    most_similar_story_id.
    """
    # story-dup: shares setting/threat/fear_mechanism/narrative_device (4 important
    # dims) with the candidate -> triggers the structural conflict guard,
    # even though its "premise"/"unique_story_hook" text differs a lot (pulling
    # its semantic/blended score down).
    story_dup = make_dna(
        setting="a small apartment bathroom",
        threat="a delayed, autonomous reflection",
        fear_mechanism="uncanny_valley",
        narrative_device="mirror",
        premise="An entirely unrelated-sounding premise about something else for text noise padding purposes.",
        unique_story_hook="a completely different surface-level hook text that reads nothing alike",
    )
    await seed(engine, vector_store, "story-dup", story_dup)

    # story-close: broadly similar wording/premise (raises semantic similarity)
    # but does NOT share the important structural dimensions -> should not
    # trigger the conflict guard.
    story_close = make_dna(
        setting="a rundown motel room",
        threat="a stranger who claims to be a future version of you",
        fear_mechanism="identity_dissolution",
        narrative_device="voicemail messages",
        twist_type="already_dead",
        ending_type="tragic",
        core_fear="not being sure who you are anymore",
        premise="A woman discovers her reflection is delayed by a few seconds.",
        unique_story_hook="the delay increases by exactly one second every night",
    )
    await seed(engine, vector_store, "story-close", story_close)

    candidate = make_dna()  # matches story_dup's structural dims via make_dna() defaults
    decision = await engine.check(candidate)

    assert decision.verdict == OriginalityVerdict.HARD_REJECT
    assert decision.structural_conflict_triggered is True
    assert decision.most_similar_story_id == "story-dup"
    # Every conflict returned must be attributable to the SAME decisive match.
    assert all(c.matched_story_id == "story-dup" for c in decision.conflicts)
    assert len(decision.conflicts) > 0
