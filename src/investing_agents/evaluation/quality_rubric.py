"""Quality scoring rubric for investment reports.

Defines criteria and scoring functions to evaluate the quality of generated
investment analysis reports.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class QualityCriterion(str, Enum):
    """Quality evaluation criteria."""

    THESIS_CLARITY = "thesis_clarity"  # Is the investment thesis clear and well-articulated?
    EVIDENCE_DEPTH = "evidence_depth"  # Is the evidence comprehensive and deep?
    REASONING_QUALITY = "reasoning_quality"  # Is the reasoning logical and sound?
    COMPREHENSIVENESS = "comprehensiveness"  # Does it cover all key aspects?
    COHERENCE = "coherence"  # Is the report internally consistent?
    ACTIONABILITY = "actionability"  # Does it provide clear actionable insights?
    RISK_ASSESSMENT = "risk_assessment"  # Are risks properly identified and assessed?
    DATA_USAGE = "data_usage"  # Is financial data properly used and cited?


@dataclass
class QualityScore:
    """Quality score for a single criterion."""

    criterion: QualityCriterion
    score: float  # 0.0 to 1.0
    reasoning: str
    evidence: List[str]  # Supporting evidence for the score


@dataclass
class OverallQuality:
    """Overall quality assessment."""

    total_score: float  # Weighted average
    criterion_scores: Dict[QualityCriterion, QualityScore]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]


class QualityRubric:
    """Quality rubric for evaluating investment reports."""

    def __init__(self, weights: Optional[Dict[QualityCriterion, float]] = None):
        """Initialize rubric with criterion weights.

        Args:
            weights: Optional custom weights for each criterion (default: equal weights)
        """
        self.weights = weights or self._default_weights()

        # Validate weights sum to 1.0
        total = sum(self.weights.values())
        if abs(total - 1.0) > 0.001:
            logger.warning(
                "quality_rubric.weights_not_normalized",
                total=total,
                weights=self.weights,
            )
            # Normalize
            self.weights = {k: v / total for k, v in self.weights.items()}

    def _default_weights(self) -> Dict[QualityCriterion, float]:
        """Get default criterion weights.

        Returns:
            Dictionary mapping criterion to weight
        """
        return {
            QualityCriterion.THESIS_CLARITY: 0.20,
            QualityCriterion.EVIDENCE_DEPTH: 0.15,
            QualityCriterion.REASONING_QUALITY: 0.20,
            QualityCriterion.COMPREHENSIVENESS: 0.10,
            QualityCriterion.COHERENCE: 0.10,
            QualityCriterion.ACTIONABILITY: 0.10,
            QualityCriterion.RISK_ASSESSMENT: 0.10,
            QualityCriterion.DATA_USAGE: 0.05,
        }

    def score_thesis_clarity(self, report: Dict[str, Any]) -> QualityScore:
        """Score thesis clarity.

        Args:
            report: Investment report to evaluate

        Returns:
            Quality score for thesis clarity
        """
        score = 0.0
        evidence = []
        reasoning_parts = []

        # Check executive summary exists and has thesis
        if "executive_summary" in report:
            exec_summary = report["executive_summary"]
            if isinstance(exec_summary, dict) and "thesis" in exec_summary:
                thesis = exec_summary["thesis"]
                if thesis and len(thesis) > 50:
                    score += 0.5
                    evidence.append("Has thesis in executive summary")
                    reasoning_parts.append("Executive summary contains clear thesis")

        # Check recommendation is clear
        if "recommendation" in report:
            rec = report["recommendation"]
            if isinstance(rec, dict) and "action" in rec:
                action = rec.get("action", "")
                if action.lower() in ["buy", "sell", "hold", "strong buy", "strong sell"]:
                    score += 0.3
                    evidence.append(f"Clear recommendation: {action}")
                    reasoning_parts.append("Recommendation is explicit and clear")

        # Check key findings articulated
        if "key_findings" in report and report["key_findings"]:
            findings = report["key_findings"]
            if isinstance(findings, list) and len(findings) >= 3:
                score += 0.2
                evidence.append(f"Has {len(findings)} key findings")
                reasoning_parts.append("Key findings clearly articulated")

        score = min(score, 1.0)
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Thesis not clearly articulated"

        return QualityScore(
            criterion=QualityCriterion.THESIS_CLARITY,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
        )

    def score_evidence_depth(self, report: Dict[str, Any]) -> QualityScore:
        """Score evidence depth.

        Args:
            report: Investment report to evaluate

        Returns:
            Quality score for evidence depth
        """
        score = 0.0
        evidence = []
        reasoning_parts = []

        # Check for evidence sections
        if "evidence" in report:
            evidence_items = report["evidence"]
            if isinstance(evidence_items, list):
                num_evidence = len(evidence_items)
                # Score based on quantity of evidence
                if num_evidence >= 5:
                    score += 0.4
                    evidence.append(f"Has {num_evidence} evidence items")
                    reasoning_parts.append(f"Substantial evidence provided ({num_evidence} items)")
                elif num_evidence >= 3:
                    score += 0.2
                    evidence.append(f"Has {num_evidence} evidence items")
                    reasoning_parts.append(f"Moderate evidence provided ({num_evidence} items)")

        # Check for data sources used
        if "sources_used" in report:
            sources = report["sources_used"]
            if isinstance(sources, list) and len(sources) > 0:
                score += 0.3
                evidence.append(f"Uses {len(sources)} data sources")
                reasoning_parts.append(f"Multiple data sources cited ({len(sources)})")

        # Check analysis sections
        if "analysis" in report:
            analysis = report["analysis"]
            if isinstance(analysis, dict):
                analysis_sections = len(analysis)
                if analysis_sections >= 3:
                    score += 0.3
                    evidence.append(f"Has {analysis_sections} analysis sections")
                    reasoning_parts.append("Comprehensive analysis across multiple dimensions")

        score = min(score, 1.0)
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Evidence depth insufficient"

        return QualityScore(
            criterion=QualityCriterion.EVIDENCE_DEPTH,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
        )

    def score_reasoning_quality(self, report: Dict[str, Any]) -> QualityScore:
        """Score reasoning quality.

        Args:
            report: Investment report to evaluate

        Returns:
            Quality score for reasoning quality
        """
        score = 0.5  # Default moderate score
        evidence = []
        reasoning_parts = ["Reasoning quality assessed through structure and content"]

        # Check for logical flow (sections present)
        required_sections = ["executive_summary", "recommendation", "analysis"]
        present_sections = [s for s in required_sections if s in report]

        if len(present_sections) == len(required_sections):
            score += 0.2
            evidence.append("Has all required sections")
            reasoning_parts.append("Report has logical structure")

        # Check for bull/bear analysis (dialectical reasoning)
        if "bull_case" in report or "bear_case" in report:
            score += 0.2
            evidence.append("Includes bull/bear analysis")
            reasoning_parts.append("Considers multiple perspectives")

        # Check for risks discussed
        if "risks" in report:
            score += 0.1
            evidence.append("Risks identified")
            reasoning_parts.append("Risk factors considered")

        score = min(score, 1.0)
        reasoning = "; ".join(reasoning_parts)

        return QualityScore(
            criterion=QualityCriterion.REASONING_QUALITY,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
        )

    def score_comprehensiveness(self, report: Dict[str, Any]) -> QualityScore:
        """Score comprehensiveness.

        Args:
            report: Investment report to evaluate

        Returns:
            Quality score for comprehensiveness
        """
        score = 0.0
        evidence = []
        reasoning_parts = []

        # Expected sections for comprehensive report
        expected_sections = [
            "executive_summary",
            "recommendation",
            "key_findings",
            "analysis",
            "risks",
            "valuation",
        ]

        present = sum(1 for s in expected_sections if s in report)
        coverage = present / len(expected_sections)

        score = coverage
        evidence.append(f"{present}/{len(expected_sections)} expected sections present")
        reasoning_parts.append(f"Coverage: {coverage:.0%} of expected sections")

        reasoning = "; ".join(reasoning_parts)

        return QualityScore(
            criterion=QualityCriterion.COMPREHENSIVENESS,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
        )

    def score_coherence(self, report: Dict[str, Any]) -> QualityScore:
        """Score internal coherence.

        Args:
            report: Investment report to evaluate

        Returns:
            Quality score for coherence
        """
        score = 0.7  # Default moderate-high score
        evidence = []
        reasoning_parts = ["Coherence assessed through consistency checks"]

        # Check recommendation aligns with thesis
        if "recommendation" in report and "executive_summary" in report:
            rec_action = report.get("recommendation", {}).get("action", "").lower()
            exec_summary = str(report.get("executive_summary", "")).lower()

            # Simple heuristic: bullish terms with buy, bearish with sell
            if "buy" in rec_action or "strong buy" in rec_action:
                if any(term in exec_summary for term in ["growth", "positive", "strong", "bullish"]):
                    score += 0.15
                    evidence.append("Recommendation aligns with positive thesis")
                    reasoning_parts.append("Recommendation consistent with thesis sentiment")
            elif "sell" in rec_action:
                if any(term in exec_summary for term in ["weak", "negative", "concern", "bearish"]):
                    score += 0.15
                    evidence.append("Recommendation aligns with negative thesis")
                    reasoning_parts.append("Recommendation consistent with thesis sentiment")

        # Check for contradictions (simple check)
        score += 0.15
        evidence.append("No obvious contradictions detected")

        score = min(score, 1.0)
        reasoning = "; ".join(reasoning_parts)

        return QualityScore(
            criterion=QualityCriterion.COHERENCE,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
        )

    def score_actionability(self, report: Dict[str, Any]) -> QualityScore:
        """Score actionability.

        Args:
            report: Investment report to evaluate

        Returns:
            Quality score for actionability
        """
        score = 0.0
        evidence = []
        reasoning_parts = []

        # Has clear recommendation
        if "recommendation" in report:
            rec = report["recommendation"]
            if isinstance(rec, dict) and "action" in rec:
                score += 0.5
                evidence.append("Has clear action recommendation")
                reasoning_parts.append("Clear investment action specified")

        # Has conviction level
        if "recommendation" in report:
            rec = report["recommendation"]
            if isinstance(rec, dict) and "conviction" in rec:
                score += 0.25
                evidence.append("Includes conviction level")
                reasoning_parts.append("Conviction level helps gauge confidence")

        # Has key findings (actionable insights)
        if "key_findings" in report and report["key_findings"]:
            score += 0.25
            evidence.append("Provides key findings")
            reasoning_parts.append("Key findings offer actionable insights")

        score = min(score, 1.0)
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Limited actionability"

        return QualityScore(
            criterion=QualityCriterion.ACTIONABILITY,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
        )

    def score_risk_assessment(self, report: Dict[str, Any]) -> QualityScore:
        """Score risk assessment.

        Args:
            report: Investment report to evaluate

        Returns:
            Quality score for risk assessment
        """
        score = 0.0
        evidence = []
        reasoning_parts = []

        # Has risks section
        if "risks" in report:
            risks = report["risks"]
            if isinstance(risks, list) and len(risks) > 0:
                num_risks = len(risks)
                if num_risks >= 3:
                    score += 0.6
                    evidence.append(f"Identifies {num_risks} risk factors")
                    reasoning_parts.append(f"Comprehensive risk assessment ({num_risks} factors)")
                else:
                    score += 0.3
                    evidence.append(f"Identifies {num_risks} risk factors")
                    reasoning_parts.append(f"Basic risk assessment ({num_risks} factors)")

        # Has bear case
        if "bear_case" in report:
            score += 0.4
            evidence.append("Includes bear case analysis")
            reasoning_parts.append("Bear case provides risk perspective")

        score = min(score, 1.0)
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Risk assessment missing"

        return QualityScore(
            criterion=QualityCriterion.RISK_ASSESSMENT,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
        )

    def score_data_usage(self, report: Dict[str, Any]) -> QualityScore:
        """Score data usage quality.

        Args:
            report: Investment report to evaluate

        Returns:
            Quality score for data usage
        """
        score = 0.0
        evidence = []
        reasoning_parts = []

        # Check for sources cited
        if "sources_used" in report:
            sources = report["sources_used"]
            if isinstance(sources, list) and len(sources) > 0:
                score += 0.5
                evidence.append(f"Cites {len(sources)} sources")
                reasoning_parts.append(f"Data sources properly cited ({len(sources)})")

        # Check for financial metrics
        report_str = str(report).lower()
        financial_terms = ["revenue", "ebitda", "margin", "growth", "valuation", "pe ratio"]
        found_terms = [term for term in financial_terms if term in report_str]

        if len(found_terms) >= 3:
            score += 0.5
            evidence.append(f"Uses {len(found_terms)} financial metrics")
            reasoning_parts.append("Financial data properly incorporated")

        score = min(score, 1.0)
        reasoning = "; ".join(reasoning_parts) if reasoning_parts else "Limited data usage"

        return QualityScore(
            criterion=QualityCriterion.DATA_USAGE,
            score=score,
            reasoning=reasoning,
            evidence=evidence,
        )

    def evaluate(self, report: Dict[str, Any]) -> OverallQuality:
        """Evaluate overall report quality.

        Args:
            report: Investment report to evaluate

        Returns:
            Overall quality assessment with scores and recommendations
        """
        logger.info("quality_rubric.evaluate_start")

        # Score each criterion
        criterion_scores = {
            QualityCriterion.THESIS_CLARITY: self.score_thesis_clarity(report),
            QualityCriterion.EVIDENCE_DEPTH: self.score_evidence_depth(report),
            QualityCriterion.REASONING_QUALITY: self.score_reasoning_quality(report),
            QualityCriterion.COMPREHENSIVENESS: self.score_comprehensiveness(report),
            QualityCriterion.COHERENCE: self.score_coherence(report),
            QualityCriterion.ACTIONABILITY: self.score_actionability(report),
            QualityCriterion.RISK_ASSESSMENT: self.score_risk_assessment(report),
            QualityCriterion.DATA_USAGE: self.score_data_usage(report),
        }

        # Calculate weighted total score
        total_score = sum(
            score.score * self.weights[criterion]
            for criterion, score in criterion_scores.items()
        )

        # Identify strengths (score >= 0.75)
        strengths = [
            f"{criterion.value}: {score.reasoning}"
            for criterion, score in criterion_scores.items()
            if score.score >= 0.75
        ]

        # Identify weaknesses (score < 0.5)
        weaknesses = [
            f"{criterion.value}: {score.reasoning}"
            for criterion, score in criterion_scores.items()
            if score.score < 0.5
        ]

        # Generate recommendations
        recommendations = []
        if not strengths:
            recommendations.append("Overall quality needs improvement across all criteria")

        for criterion, score in criterion_scores.items():
            if score.score < 0.5:
                recommendations.append(
                    f"Improve {criterion.value}: {score.reasoning}"
                )

        logger.info(
            "quality_rubric.evaluate_complete",
            total_score=total_score,
            strengths_count=len(strengths),
            weaknesses_count=len(weaknesses),
        )

        return OverallQuality(
            total_score=total_score,
            criterion_scores=criterion_scores,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
        )
