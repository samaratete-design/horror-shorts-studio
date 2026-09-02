from shared_types.originality import OriginalityDecision, OriginalityVerdict
from story_engine.quality_gate import ContentQualityGate, ViralScores, QualityGateVerdict


def _viral(**overrides) -> ViralScores:
    defaults = dict(
        hook_strength=90,
        curiosity_gap=90,
        emotional_intensity=90,
        horror_intensity=90,
        tension_curve=90,
        novelty=90,
        payoff_strength=90,
        rewatch_potential=90,
        comment_potential=90,
        share_potential=90,
        production_feasibility=90,
    )
    defaults.update(overrides)
    return ViralScores(**defaults)


def _originality(verdict: OriginalityVerdict, similarity: float = 0.3) -> OriginalityDecision:
    return OriginalityDecision(
        verdict=verdict,
        overall_similarity=similarity,
        explanation="test",
    )


def test_low_originality_high_viral_is_rejected():
    gate = ContentQualityGate()
    result = gate.evaluate(
        originality=_originality(OriginalityVerdict.HARD_REJECT, similarity=0.85),
        viral=_viral(),  # near-perfect viral scores
    )
    assert result.verdict == QualityGateVerdict.REJECT


def test_high_originality_low_viral_is_rewrite():
    gate = ContentQualityGate()
    result = gate.evaluate(
        originality=_originality(OriginalityVerdict.APPROVED, similarity=0.1),
        viral=_viral(
            hook_strength=20, curiosity_gap=20, emotional_intensity=20, horror_intensity=20,
            tension_curve=20, novelty=20, payoff_strength=20, rewatch_potential=20,
            comment_potential=20, share_potential=20,
        ),
    )
    assert result.verdict == QualityGateVerdict.REWRITE


def test_high_originality_high_viral_is_approved():
    gate = ContentQualityGate()
    result = gate.evaluate(
        originality=_originality(OriginalityVerdict.APPROVED, similarity=0.1),
        viral=_viral(),
    )
    assert result.verdict == QualityGateVerdict.APPROVED


def test_originality_rewrite_caps_result_even_with_perfect_viral():
    gate = ContentQualityGate()
    result = gate.evaluate(
        originality=_originality(OriginalityVerdict.REWRITE, similarity=0.6),
        viral=_viral(),
    )
    assert result.verdict == QualityGateVerdict.REWRITE


def test_low_production_feasibility_rejects_even_with_approved_originality():
    gate = ContentQualityGate()
    result = gate.evaluate(
        originality=_originality(OriginalityVerdict.APPROVED, similarity=0.05),
        viral=_viral(production_feasibility=10),
    )
    assert result.verdict == QualityGateVerdict.REJECT
