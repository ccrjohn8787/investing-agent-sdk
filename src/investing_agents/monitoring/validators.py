"""Validation gates for each analysis phase.

These validators run after each phase to ensure quality before proceeding.
They implement early error detection to fail fast and save time.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger()


class ValidationLevel(str, Enum):
    """Validation severity levels."""

    CRITICAL = "critical"  # Must fix - blocks progress
    ERROR = "error"  # Should fix - may cause downstream issues
    WARNING = "warning"  # Consider fixing - may reduce quality
    INFO = "info"  # Informational - no action needed


@dataclass
class ValidationResult:
    """Result from a validation check."""

    passed: bool
    level: ValidationLevel
    message: str
    details: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        """String representation."""
        prefix = "✓" if self.passed else "✗"
        return f"{prefix} [{self.level.value.upper()}] {self.message}"


class ValidationError(Exception):
    """Raised when critical validation fails."""

    def __init__(self, results: List[ValidationResult]):
        """Initialize validation error.

        Args:
            results: List of failed validation results
        """
        self.results = results
        failures = "\n".join(str(r) for r in results if not r.passed)
        super().__init__(f"Validation failed:\n{failures}")


class HypothesisValidator:
    """Validates hypothesis generation output."""

    def __init__(self, min_hypotheses: int = 3, min_quality: float = 3.0):
        """Initialize validator.

        Args:
            min_hypotheses: Minimum number of hypotheses required
            min_quality: Minimum average quality score (1-5 scale)
        """
        self.min_hypotheses = min_hypotheses
        self.min_quality = min_quality
        self.log = logger.bind(validator="hypothesis")

    def validate(self, hypotheses: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate hypothesis generation output.

        Args:
            hypotheses: List of generated hypotheses

        Returns:
            List of validation results
        """
        results = []

        # Check: Minimum number of hypotheses
        if len(hypotheses) < self.min_hypotheses:
            results.append(
                ValidationResult(
                    passed=False,
                    level=ValidationLevel.CRITICAL,
                    message=f"Only {len(hypotheses)} hypotheses generated, need {self.min_hypotheses}",
                    details={"count": len(hypotheses), "min_required": self.min_hypotheses},
                )
            )
        else:
            results.append(
                ValidationResult(
                    passed=True,
                    level=ValidationLevel.INFO,
                    message=f"Generated {len(hypotheses)} hypotheses (≥ {self.min_hypotheses})",
                    details={"count": len(hypotheses)},
                )
            )

        # Check: Hypothesis quality scores
        qualities = []
        for h in hypotheses:
            if "confidence" in h:
                qualities.append(h["confidence"])
            elif "quality" in h:
                qualities.append(h["quality"])

        if qualities:
            avg_quality = sum(qualities) / len(qualities)
            if avg_quality < self.min_quality:
                results.append(
                    ValidationResult(
                        passed=False,
                        level=ValidationLevel.WARNING,
                        message=f"Average hypothesis quality {avg_quality:.2f} below threshold {self.min_quality}",
                        details={"avg_quality": avg_quality, "min_quality": self.min_quality},
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        passed=True,
                        level=ValidationLevel.INFO,
                        message=f"Average hypothesis quality: {avg_quality:.2f}",
                        details={"avg_quality": avg_quality},
                    )
                )

        # Check: Diversity (no duplicate hypotheses)
        thesis_texts = [h.get("thesis", "").lower() for h in hypotheses]
        unique_count = len(set(thesis_texts))
        if unique_count < len(hypotheses):
            duplicates = len(hypotheses) - unique_count
            results.append(
                ValidationResult(
                    passed=False,
                    level=ValidationLevel.WARNING,
                    message=f"Found {duplicates} duplicate hypotheses",
                    details={"total": len(hypotheses), "unique": unique_count},
                )
            )

        self.log.info(
            "validation.hypotheses.complete",
            passed=sum(1 for r in results if r.passed),
            failed=sum(1 for r in results if not r.passed),
            critical=sum(1 for r in results if r.level == ValidationLevel.CRITICAL and not r.passed),
        )

        return results


class EvidenceValidator:
    """Validates research evidence collection."""

    def __init__(self, min_evidence_per_hypothesis: int = 5, min_web_sources: int = 3):
        """Initialize validator.

        Args:
            min_evidence_per_hypothesis: Minimum evidence items per hypothesis
            min_web_sources: Minimum web sources (not just SEC filings)
        """
        self.min_evidence = min_evidence_per_hypothesis
        self.min_web_sources = min_web_sources
        self.log = logger.bind(validator="evidence")

    def validate(self, evidence_results: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate research evidence.

        Args:
            evidence_results: List of evidence dicts per hypothesis

        Returns:
            List of validation results
        """
        results = []

        # Check each hypothesis's evidence
        low_evidence_count = 0
        low_web_count = 0

        for i, evidence in enumerate(evidence_results):
            evidence_items = evidence.get("evidence_items", [])
            web_sources = evidence.get("web_sources_count", 0)
            hyp_id = evidence.get("hypothesis_id", f"hypothesis_{i}")

            # Check: Minimum evidence items
            if len(evidence_items) < self.min_evidence:
                low_evidence_count += 1
                results.append(
                    ValidationResult(
                        passed=False,
                        level=ValidationLevel.ERROR,
                        message=f"{hyp_id}: Only {len(evidence_items)} evidence items (need {self.min_evidence})",
                        details={
                            "hypothesis_id": hyp_id,
                            "evidence_count": len(evidence_items),
                            "min_required": self.min_evidence,
                        },
                    )
                )

            # Check: Minimum web sources
            if web_sources < self.min_web_sources:
                low_web_count += 1
                results.append(
                    ValidationResult(
                        passed=False,
                        level=ValidationLevel.WARNING,
                        message=f"{hyp_id}: Only {web_sources} web sources (need {self.min_web_sources})",
                        details={
                            "hypothesis_id": hyp_id,
                            "web_sources": web_sources,
                            "min_required": self.min_web_sources,
                        },
                    )
                )

        # Summary check
        if low_evidence_count == 0:
            results.append(
                ValidationResult(
                    passed=True,
                    level=ValidationLevel.INFO,
                    message=f"All {len(evidence_results)} hypotheses have sufficient evidence",
                    details={"hypothesis_count": len(evidence_results)},
                )
            )
        else:
            results.append(
                ValidationResult(
                    passed=False,
                    level=ValidationLevel.CRITICAL,
                    message=f"{low_evidence_count}/{len(evidence_results)} hypotheses have insufficient evidence",
                    details={"low_evidence_count": low_evidence_count, "total": len(evidence_results)},
                )
            )

        self.log.info(
            "validation.evidence.complete",
            passed=sum(1 for r in results if r.passed),
            failed=sum(1 for r in results if not r.passed),
            low_evidence_count=low_evidence_count,
            low_web_count=low_web_count,
        )

        return results


class SynthesisValidator:
    """Validates synthesis output quality."""

    def __init__(self, min_confidence: float = 0.6, require_valuation_inputs: bool = True):
        """Initialize validator.

        Args:
            min_confidence: Minimum confidence score for synthesis
            require_valuation_inputs: Whether valuation inputs are required
        """
        self.min_confidence = min_confidence
        self.require_valuation_inputs = require_valuation_inputs
        self.log = logger.bind(validator="synthesis")

    def validate(self, synthesis_results: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Validate synthesis output.

        Args:
            synthesis_results: List of synthesis results per hypothesis

        Returns:
            List of validation results
        """
        results = []

        low_confidence_count = 0
        missing_valuation_count = 0

        for i, synthesis in enumerate(synthesis_results):
            hyp_id = synthesis.get("hypothesis_id", f"synthesis_{i}")
            confidence = synthesis.get("confidence", 0.0)
            valuation_inputs = synthesis.get("valuation_inputs", {})

            # Check: Confidence threshold
            if confidence < self.min_confidence:
                low_confidence_count += 1
                results.append(
                    ValidationResult(
                        passed=False,
                        level=ValidationLevel.WARNING,
                        message=f"{hyp_id}: Low confidence {confidence:.2f} (threshold {self.min_confidence})",
                        details={"hypothesis_id": hyp_id, "confidence": confidence, "threshold": self.min_confidence},
                    )
                )

            # Check: Valuation inputs present
            if self.require_valuation_inputs:
                if not valuation_inputs or len(valuation_inputs) == 0:
                    missing_valuation_count += 1
                    results.append(
                        ValidationResult(
                            passed=False,
                            level=ValidationLevel.ERROR,
                            message=f"{hyp_id}: Missing valuation inputs",
                            details={"hypothesis_id": hyp_id},
                        )
                    )

        # Summary
        if low_confidence_count == 0 and missing_valuation_count == 0:
            results.append(
                ValidationResult(
                    passed=True,
                    level=ValidationLevel.INFO,
                    message=f"All {len(synthesis_results)} syntheses passed quality checks",
                    details={"synthesis_count": len(synthesis_results)},
                )
            )

        self.log.info(
            "validation.synthesis.complete",
            passed=sum(1 for r in results if r.passed),
            failed=sum(1 for r in results if not r.passed),
            low_confidence_count=low_confidence_count,
            missing_valuation_count=missing_valuation_count,
        )

        return results


class ValuationValidator:
    """Validates valuation output."""

    def __init__(self, require_fair_value: bool = True, require_sensitivity: bool = True):
        """Initialize validator.

        Args:
            require_fair_value: Whether fair value calculation is required
            require_sensitivity: Whether sensitivity analysis is required
        """
        self.require_fair_value = require_fair_value
        self.require_sensitivity = require_sensitivity
        self.log = logger.bind(validator="valuation")

    def validate(self, valuation: Dict[str, Any]) -> List[ValidationResult]:
        """Validate valuation output.

        Args:
            valuation: Valuation result dictionary

        Returns:
            List of validation results
        """
        results = []

        # Check: Fair value present
        fair_value = valuation.get("fair_value")
        if self.require_fair_value:
            if fair_value is None or fair_value <= 0:
                results.append(
                    ValidationResult(
                        passed=False,
                        level=ValidationLevel.CRITICAL,
                        message=f"Invalid fair value: {fair_value}",
                        details={"fair_value": fair_value},
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        passed=True,
                        level=ValidationLevel.INFO,
                        message=f"Fair value calculated: ${fair_value:.2f}",
                        details={"fair_value": fair_value},
                    )
                )

        # Check: Sensitivity analysis present
        sensitivity = valuation.get("sensitivity")
        if self.require_sensitivity:
            if not sensitivity or len(sensitivity) == 0:
                results.append(
                    ValidationResult(
                        passed=False,
                        level=ValidationLevel.WARNING,
                        message="Sensitivity analysis missing",
                        details={},
                    )
                )
            else:
                results.append(
                    ValidationResult(
                        passed=True,
                        level=ValidationLevel.INFO,
                        message=f"Sensitivity analysis complete ({len(sensitivity)} scenarios)",
                        details={"scenario_count": len(sensitivity)},
                    )
                )

        # Check: Reasonable value range (sanity check)
        if fair_value and fair_value > 0:
            if fair_value < 1 or fair_value > 100000:
                results.append(
                    ValidationResult(
                        passed=False,
                        level=ValidationLevel.WARNING,
                        message=f"Fair value ${fair_value:.2f} outside typical range ($1-$100,000)",
                        details={"fair_value": fair_value},
                    )
                )

        self.log.info(
            "validation.valuation.complete",
            passed=sum(1 for r in results if r.passed),
            failed=sum(1 for r in results if not r.passed),
            fair_value=fair_value,
        )

        return results
