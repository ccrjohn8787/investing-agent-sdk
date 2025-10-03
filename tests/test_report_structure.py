"""Report structure validation tests.

Validates that generated investment reports contain all required sections
for PM evaluation. This provides instant feedback (< 1 sec) vs 20-minute
full PM evaluation.

Usage:
    pytest tests/test_report_structure.py
    python -m tests.test_report_structure output/report.json
"""

import json
from pathlib import Path

import pytest

from investing_agents.evaluation.structure_validator import validate_report_structure


@dataclass
class ValidationResult:
    """Result of report structure validation."""

    is_valid: bool
    missing_sections: List[str]
    warnings: List[str]
    grade_estimate: str
    score_estimate: int

    def __str__(self) -> str:
        """Human-readable validation summary."""
        lines = []

        # Header
        status = "✓ PASS" if self.is_valid else "✗ FAIL"
        lines.append(f"\n{status}: Report Structure Validation")
        lines.append(f"Estimated Grade: {self.grade_estimate} ({self.score_estimate}/100)")
        lines.append("")

        # Missing sections
        if self.missing_sections:
            lines.append("CRITICAL MISSING SECTIONS:")
            for section in self.missing_sections:
                lines.append(f"  ✗ {section}")
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("WARNINGS:")
            for warning in self.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")

        # Summary
        if self.missing_sections:
            lines.append("Impact:")
            lines.append(
                "  - Missing scenarios caps grade at B (82-84) per PM evaluation criteria"
            )
            lines.append("  - Incomplete methodology reduces Data Quality score")
            lines.append("  - Vague conditions reduce Decision-Readiness score")

        return "\n".join(lines)


def has_nested_key(data: Dict[str, Any], path: str) -> bool:
    """Check if nested key exists in dictionary.

    Args:
        data: Dictionary to check
        path: Dot-separated path (e.g., "valuation.scenarios.bull.price_target")

    Returns:
        True if path exists, False otherwise

    Examples:
        >>> has_nested_key({"a": {"b": 1}}, "a.b")
        True
        >>> has_nested_key({"a": {"b": 1}}, "a.c")
        False
    """
    keys = path.split(".")
    current = data

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]

    return True


def get_nested_value(data: Dict[str, Any], path: str, default: Any = None) -> Any:
    """Get value at nested key path.

    Args:
        data: Dictionary to check
        path: Dot-separated path
        default: Default value if path doesn't exist

    Returns:
        Value at path or default
    """
    keys = path.split(".")
    current = data

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]

    return current


def validate_report_structure(report_json: Dict[str, Any]) -> ValidationResult:
    """Validate report has all required sections for PM evaluation.

    This provides instant feedback on structural completeness without
    running full LLM-based PM evaluation.

    Args:
        report_json: Parsed report JSON

    Returns:
        ValidationResult with missing sections, warnings, and grade estimate

    Grade Estimation Logic:
        - Missing scenarios: caps grade at B (82-84)
        - Missing methodology: -3 to -5 points
        - Missing entry/exit: -2 to -4 points
        - Each additional missing section: -2 to -3 points
    """
    missing = []
    warnings = []

    # CRITICAL: Valuation scenarios (without these, grade capped at B)
    required_scenarios = [
        ("valuation.scenarios.bull.price_target", "CRITICAL"),
        ("valuation.scenarios.base.price_target", "CRITICAL"),
        ("valuation.scenarios.bear.price_target", "CRITICAL"),
        ("valuation.scenarios.bull.probability", "CRITICAL"),
        ("valuation.scenarios.base.probability", "CRITICAL"),
        ("valuation.scenarios.bear.probability", "CRITICAL"),
        ("valuation.scenarios.bull.key_conditions", "CRITICAL"),
        ("valuation.scenarios.base.key_conditions", "CRITICAL"),
        ("valuation.scenarios.bear.key_conditions", "CRITICAL"),
    ]

    for path, severity in required_scenarios:
        if not has_nested_key(report_json, path):
            missing.append(f"{path} [{severity}]")

    # HIGH: Valuation methodology
    if not has_nested_key(report_json, "valuation.methodology"):
        missing.append("valuation.methodology [HIGH]")
    else:
        methodology = get_nested_value(report_json, "valuation.methodology", "")
        if len(methodology) < 50:
            warnings.append(
                f"Methodology too short ({len(methodology)} chars, need 50+). "
                "Should explain WACC, terminal growth, margin assumptions."
            )
        # Check for key terms
        methodology_lower = methodology.lower()
        if "wacc" not in methodology_lower and "discount" not in methodology_lower:
            warnings.append("Methodology missing WACC or discount rate explanation")
        if "terminal" not in methodology_lower and "perpetuity" not in methodology_lower:
            warnings.append("Methodology missing terminal growth explanation")

    # HIGH: DCF valuation outputs
    if not has_nested_key(report_json, "valuation.fair_value_per_share"):
        missing.append("valuation.fair_value_per_share [HIGH]")

    # HIGH: Entry/Exit conditions
    if not has_nested_key(report_json, "recommendation.entry_conditions"):
        missing.append("recommendation.entry_conditions [HIGH]")
    else:
        entry_conditions = get_nested_value(report_json, "recommendation.entry_conditions", [])
        if not isinstance(entry_conditions, list) or len(entry_conditions) < 3:
            warnings.append(
                f"Entry conditions has {len(entry_conditions)} items, expected 3+"
            )
        # Check for specificity
        vague_keywords = ["improve", "better", "favorable", "conditions"]
        for i, condition in enumerate(entry_conditions):
            if isinstance(condition, str):
                cond_lower = condition.lower()
                if any(vague in cond_lower for vague in vague_keywords):
                    if "$" not in condition and "%" not in condition:
                        warnings.append(
                            f"Entry condition {i+1} is vague: '{condition}'. "
                            "Should include specific price/metric."
                        )

    if not has_nested_key(report_json, "recommendation.exit_conditions"):
        missing.append("recommendation.exit_conditions [HIGH]")
    else:
        exit_conditions = get_nested_value(report_json, "recommendation.exit_conditions", [])
        if not isinstance(exit_conditions, list) or len(exit_conditions) < 3:
            warnings.append(
                f"Exit conditions has {len(exit_conditions)} items, expected 3+"
            )

    # MEDIUM: Bull/Bear analysis
    if not has_nested_key(report_json, "bull_bear_analysis.bull_case"):
        missing.append("bull_bear_analysis.bull_case [MEDIUM]")
    if not has_nested_key(report_json, "bull_bear_analysis.bear_case"):
        missing.append("bull_bear_analysis.bear_case [MEDIUM]")

    # MEDIUM: Recommendation
    if not has_nested_key(report_json, "recommendation.recommendation"):
        missing.append("recommendation.recommendation [MEDIUM]")

    # Estimate grade based on missing sections
    base_score = 100

    # Count CRITICAL missing
    critical_missing = [m for m in missing if "[CRITICAL]" in m]
    if critical_missing:
        # Missing scenarios caps at B (82-84)
        base_score = 84
        missing_scenarios_count = len([m for m in critical_missing if "scenarios" in m])
        if missing_scenarios_count >= 6:  # Most scenarios missing
            base_score = 82

    # Deduct for other missing sections
    high_missing = [m for m in missing if "[HIGH]" in m]
    medium_missing = [m for m in missing if "[MEDIUM]" in m]

    base_score -= len(high_missing) * 3
    base_score -= len(medium_missing) * 2
    base_score -= len(warnings) * 1  # Small penalty for warnings

    # Grade mapping
    if base_score >= 93:
        grade = "A"
    elif base_score >= 90:
        grade = "A-"
    elif base_score >= 87:
        grade = "B+"
    elif base_score >= 83:
        grade = "B"
    elif base_score >= 80:
        grade = "B-"
    else:
        grade = "C+ or lower"

    is_valid = len(missing) == 0 and len(warnings) == 0

    return ValidationResult(
        is_valid=is_valid,
        missing_sections=missing,
        warnings=warnings,
        grade_estimate=grade,
        score_estimate=max(base_score, 70),  # Floor at 70
    )


# Test functions for pytest


def test_valid_report_passes():
    """Test that a complete report passes validation."""
    complete_report = {
        "valuation": {
            "fair_value_per_share": 606.54,
            "methodology": "DCF with WACC of 8.5%, terminal growth of 3.0%, and terminal margin of 35%. Five-year explicit forecast period.",
            "scenarios": {
                "bull": {
                    "price_target": 850,
                    "probability": 0.35,
                    "key_conditions": ["Revenue growth >20%", "Margin expansion to 45%"],
                },
                "base": {
                    "price_target": 607,
                    "probability": 0.45,
                    "key_conditions": ["Revenue growth 15-18%", "Margins stable at 40%"],
                },
                "bear": {
                    "price_target": 455,
                    "probability": 0.20,
                    "key_conditions": ["Revenue growth <10%", "Margin compression to 35%"],
                },
            },
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization"},
            "bear_case": {"summary": "CapEx overrun"},
        },
        "recommendation": {
            "recommendation": "HOLD",
            "entry_conditions": [
                "Stock price < $600",
                "Q1 2025 revenue beat >5%",
                "Management confirms CapEx <$45B",
            ],
            "exit_conditions": [
                "Stock price > $750",
                "CapEx guidance >$50B",
                "Ad monetization declining",
            ],
        },
    }

    result = validate_report_structure(complete_report)
    assert result.is_valid
    assert len(result.missing_sections) == 0
    assert result.grade_estimate in ["A-", "A"]


def test_missing_scenarios_caps_at_b():
    """Test that missing scenarios caps grade at B."""
    report_no_scenarios = {
        "valuation": {
            "fair_value_per_share": 606.54,
            "methodology": "DCF with WACC 8.5%, terminal growth 3%, margin 35%",
            # Missing scenarios!
        },
        "bull_bear_analysis": {"bull_case": {}, "bear_case": {}},
        "recommendation": {
            "recommendation": "HOLD",
            "entry_conditions": ["Price < $600"],
            "exit_conditions": ["Price > $750"],
        },
    }

    result = validate_report_structure(report_no_scenarios)
    assert not result.is_valid
    assert any("scenarios" in m for m in result.missing_sections)
    assert result.score_estimate <= 84
    assert result.grade_estimate in ["B", "B-"]


def test_short_methodology_warning():
    """Test that short methodology generates warning."""
    report = {
        "valuation": {
            "fair_value_per_share": 606.54,
            "methodology": "DCF",  # Too short!
            "scenarios": {
                "bull": {"price_target": 850, "probability": 0.35, "key_conditions": ["x"]},
                "base": {"price_target": 607, "probability": 0.45, "key_conditions": ["y"]},
                "bear": {"price_target": 455, "probability": 0.20, "key_conditions": ["z"]},
            },
        },
        "bull_bear_analysis": {"bull_case": {}, "bear_case": {}},
        "recommendation": {
            "recommendation": "HOLD",
            "entry_conditions": ["x"],
            "exit_conditions": ["y"],
        },
    }

    result = validate_report_structure(report)
    assert any("too short" in w.lower() for w in result.warnings)
    assert any("wacc" in w.lower() or "discount" in w.lower() for w in result.warnings)


def test_vague_entry_condition_warning():
    """Test that vague entry conditions generate warnings."""
    report = {
        "valuation": {
            "fair_value_per_share": 606.54,
            "methodology": "DCF with WACC 8.5%, terminal growth 3%, terminal margin 35%",
            "scenarios": {
                "bull": {"price_target": 850, "probability": 0.35, "key_conditions": ["x"]},
                "base": {"price_target": 607, "probability": 0.45, "key_conditions": ["y"]},
                "bear": {"price_target": 455, "probability": 0.20, "key_conditions": ["z"]},
            },
        },
        "bull_bear_analysis": {"bull_case": {}, "bear_case": {}},
        "recommendation": {
            "recommendation": "HOLD",
            "entry_conditions": [
                "Market conditions improve",  # Vague!
                "Stock price < $600",  # Specific
            ],
            "exit_conditions": ["Price > $750"],
        },
    }

    result = validate_report_structure(report)
    assert any("vague" in w.lower() for w in result.warnings)


# CLI usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m tests.test_report_structure <report.json>")
        sys.exit(1)

    report_path = Path(sys.argv[1])
    if not report_path.exists():
        print(f"Error: File not found: {report_path}")
        sys.exit(1)

    with open(report_path) as f:
        report_data = json.load(f)

    result = validate_report_structure(report_data)
    print(result)

    sys.exit(0 if result.is_valid else 1)
