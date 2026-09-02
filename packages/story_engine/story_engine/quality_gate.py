"""
ContentQualityGate

Final content must pass Originality + Story Quality + Viral Potential +
Retention Potential + Production Feasibility.

Originality is a HARD GATE: a HARD_REJECT or REWRITE originality verdict
caps the final decision, no matter how high the viral score is. This is
enforced structurally (not via a weighted average) so a high viral score
can never mathematically compensate for a low originality verdict.
"""
from dataclasses import dataclass
from enum import Enum

from shared_types.originality import OriginalityDecision, OriginalityVerdict


class QualityGateVerdict(str, Enum):
    APPROVED = "approved"
    REWRITE = "rewrite"
    REJECT = "reject"


@dataclass
class ViralScores:
    hook_strength: float
    curiosity_gap: float
    emotional_intensity: float
    horror_intensity: float
    tension_curve: float
    novelty: float
    payoff_strength: float
    rewatch_potential: float
    comment_potential: float
    share_potential: float
    production_feasibility: float

    @property
    def overall_viral_score(self) -> float:
        values = [
            self.hook_strength,
            self.curiosity_gap,
            self.emotional_intensity,
            self.horror_intensity,
            self.tension_curve,
            self.novelty,
            self.payoff_strength,
            self.rewatch_potential,
            self.comment_potential,
            self.share_potential,
        ]
        return sum(values) / len(values)


@dataclass
class QualityGateResult:
    verdict: QualityGateVerdict
    originality_verdict: OriginalityVerdict
    overall_viral_score: float
    reason: str


MIN_VIRAL_SCORE_FOR_APPROVAL = 60.0
MIN_PRODUCTION_FEASIBILITY = 40.0


class ContentQualityGate:
    def evaluate(self, originality: OriginalityDecision, viral: ViralScores) -> QualityGateResult:
        # HARD GATE: originality failure short-circuits everything else.
        if originality.verdict == OriginalityVerdict.HARD_REJECT:
            return QualityGateResult(
                verdict=QualityGateVerdict.REJECT,
                originality_verdict=originality.verdict,
                overall_viral_score=viral.overall_viral_score,
                reason=(
                    f"Originality hard-rejected (similarity {originality.overall_similarity:.0%}). "
                    "Rejected regardless of viral score."
                ),
            )

        if originality.verdict == OriginalityVerdict.REWRITE:
            return QualityGateResult(
                verdict=QualityGateVerdict.REWRITE,
                originality_verdict=originality.verdict,
                overall_viral_score=viral.overall_viral_score,
                reason=(
                    f"Originality requires rewrite (similarity {originality.overall_similarity:.0%}) "
                    "before viral/quality scoring can approve this story."
                ),
            )

        # Originality approved - now viral/production quality can gate.
        if viral.production_feasibility < MIN_PRODUCTION_FEASIBILITY:
            return QualityGateResult(
                verdict=QualityGateVerdict.REJECT,
                originality_verdict=originality.verdict,
                overall_viral_score=viral.overall_viral_score,
                reason=f"Production feasibility too low ({viral.production_feasibility:.0f}/100).",
            )

        if viral.overall_viral_score < MIN_VIRAL_SCORE_FOR_APPROVAL:
            return QualityGateResult(
                verdict=QualityGateVerdict.REWRITE,
                originality_verdict=originality.verdict,
                overall_viral_score=viral.overall_viral_score,
                reason=f"Viral score below threshold ({viral.overall_viral_score:.0f}/100). Needs rework.",
            )

        return QualityGateResult(
            verdict=QualityGateVerdict.APPROVED,
            originality_verdict=originality.verdict,
            overall_viral_score=viral.overall_viral_score,
            reason="Passed originality, production feasibility, and viral thresholds.",
        )
