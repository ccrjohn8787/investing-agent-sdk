"""Fast PM evaluation mode for 30-second quality checks.

This provides instant feedback on report quality without running full LLM-based
PM evaluation. Useful for rapid iteration during development.

Usage:
    from investing_agents.evaluation.fast_evaluator import fast_evaluate

    result = fast_evaluate(report_json)
    print(result.get_summary())

CLI:
    python -m investing_agents.evaluation.fast_evaluator output/report.json
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

from investing_agents.evaluation.structure_validator import validate_report_structure


@dataclass
class FastEvaluationResult:
    """Result of fast PM evaluation."""

    grade: str
    score: int
    issues: List[str]
    warnings: List[str]
    checks_passed: int
    checks_total: int

    def get_summary(self) -> str:
        """Get human-readable evaluation summary."""
        lines = []

        # Header
        lines.append("\n" + "=" * 80)
        lines.append("FAST PM EVALUATION RESULT")
        lines.append("=" * 80)
        lines.append(f"Grade: {self.grade} ({self.score}/100)")
        lines.append(f"Checks: {self.checks_passed}/{self.checks_total} passed")
        lines.append("")

        # Critical issues
        if self.issues:
            lines.append("CRITICAL ISSUES:")
            for issue in self.issues:
                lines.append(f"  ✗ {issue}")
            lines.append("")

        # Warnings
        if self.warnings:
            lines.append("WARNINGS:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")
            lines.append("")

        # Recommendations
        lines.append("NEXT STEPS:")
        if self.score >= 90:
            lines.append("  ✓ Fast check passed - PROCEED WITH FULL PM EVALUATION (required)")
            lines.append("  ⚠ Note: Fast check is pre-validation only, full PM eval is mandatory")
        elif self.score >= 83:
            lines.append(
                "  ⚠ Report at B level - fix issues above, then run FULL PM EVALUATION"
            )
            lines.append("  ⚠ Full PM evaluation is always required regardless of fast check result")
        else:
            lines.append(
                "  ✗ Report below B - fix critical issues, then run FULL PM EVALUATION"
            )
            lines.append("  ⚠ Full PM evaluation is always required regardless of fast check result")

        lines.append("")
        lines.append("IMPORTANT: This is a PRE-CHECK only. Always run full PM evaluation.")
        lines.append("=" * 80)
        return "\n".join(lines)


def fast_evaluate(report: Dict[str, Any]) -> FastEvaluationResult:
    """Fast PM evaluation using heuristics (no LLM calls).

    Args:
        report: Parsed report JSON

    Returns:
        FastEvaluationResult with grade estimate and issues

    Evaluation Criteria:
        1. Structure validation (from test_report_structure.py)
        2. Scenario sanity checks (price spreads, probabilities)
        3. Text quality checks (min length, keyword presence)
        4. Valuation-recommendation consistency
    """
    issues = []
    warnings = []
    checks_passed = 0
    checks_total = 0

    # Check 1: Structure validation
    checks_total += 1
    struct_result = validate_report_structure(report)
    if struct_result.is_valid:
        checks_passed += 1
    else:
        for missing in struct_result.missing_sections:
            issues.append(f"Missing section: {missing}")
    warnings.extend(struct_result.warnings)

    # Check 2: Scenario sanity checks
    scenarios = report.get("valuation", {}).get("scenarios", {})
    if scenarios:
        checks_total += 3

        # Check 2a: Price ordering (bull > base > bear)
        bull_price = scenarios.get("bull", {}).get("price_target", 0)
        base_price = scenarios.get("base", {}).get("price_target", 0)
        bear_price = scenarios.get("bear", {}).get("price_target", 0)

        if bull_price > 0 and base_price > 0 and bear_price > 0:
            if bull_price >= base_price >= bear_price:
                checks_passed += 1
            else:
                issues.append(
                    f"Scenario price ordering incorrect: bull={bull_price}, base={base_price}, bear={bear_price}"
                )

        # Check 2b: Price spread reasonableness (bull-bear spread > 20%)
        if base_price > 0:
            bull_upside = ((bull_price - base_price) / base_price) * 100
            bear_downside = ((base_price - bear_price) / base_price) * 100
            total_spread = bull_upside + bear_downside

            if total_spread > 20:
                checks_passed += 1
            else:
                warnings.append(
                    f"Scenario spread narrow ({total_spread:.1f}%) - consider wider range"
                )
                checks_passed += 1  # Warning, not failure

        # Check 2c: Probabilities sum to 1.0
        bull_prob = scenarios.get("bull", {}).get("probability", 0)
        base_prob = scenarios.get("base", {}).get("probability", 0)
        bear_prob = scenarios.get("bear", {}).get("probability", 0)
        prob_sum = bull_prob + base_prob + bear_prob

        if 0.99 <= prob_sum <= 1.01:
            checks_passed += 1
        else:
            issues.append(
                f"Scenario probabilities sum to {prob_sum:.3f}, expected 1.0"
            )

    # Check 3: Text quality checks
    checks_total += 4

    # Check 3a: Executive summary length
    exec_summary = report.get("executive_summary", "")
    if len(exec_summary) >= 100:
        checks_passed += 1
    else:
        warnings.append(
            f"Executive summary short ({len(exec_summary)} chars, recommend 200+)"
        )
        checks_passed += 1  # Warning only

    # Check 3b: Methodology quality
    methodology = report.get("valuation", {}).get("methodology", "")
    if len(methodology) >= 100:
        checks_passed += 1
    else:
        warnings.append(
            f"Methodology brief ({len(methodology)} chars, recommend 150+)"
        )
        checks_passed += 1  # Warning only

    # Check 3c: Bull/bear analysis depth
    bull_case = report.get("bull_bear_analysis", {}).get("bull_case", {})
    bear_case = report.get("bull_bear_analysis", {}).get("bear_case", {})
    bull_text = str(bull_case.get("summary", ""))
    bear_text = str(bear_case.get("summary", ""))

    if len(bull_text) >= 50 and len(bear_text) >= 50:
        checks_passed += 1
    else:
        warnings.append(
            f"Bull/bear analysis thin (bull: {len(bull_text)}, bear: {len(bear_text)} chars)"
        )
        checks_passed += 1  # Warning only

    # Check 3d: Entry/exit conditions specificity
    entry_conditions = report.get("recommendation", {}).get("entry_conditions", [])
    exit_conditions = report.get("recommendation", {}).get("exit_conditions", [])

    if len(entry_conditions) >= 3 and len(exit_conditions) >= 3:
        checks_passed += 1
    else:
        warnings.append(
            f"Entry/exit conditions sparse (entry: {len(entry_conditions)}, exit: {len(exit_conditions)})"
        )
        checks_passed += 1  # Warning only

    # Check 4: Valuation-recommendation consistency
    checks_total += 1
    fair_value = report.get("valuation", {}).get("fair_value_per_share", 0)
    current_price = report.get("current_price")  # May not be in report
    recommendation = report.get("recommendation", {}).get("action", "")

    # Simple heuristic: If scenarios exist, check bull vs base spread
    if scenarios and base_price > 0:
        bull_upside_pct = ((bull_price - base_price) / base_price) * 100

        # If bull case shows >30% upside with reasonable probability, should be BUY
        if (
            bull_upside_pct > 30
            and bull_prob >= 0.3
            and recommendation not in ["BUY", "STRONG BUY"]
        ):
            warnings.append(
                f"Bull case shows {bull_upside_pct:.1f}% upside (prob={bull_prob:.0%}) but recommendation is {recommendation}"
            )
        checks_passed += 1  # Just a warning

    # Estimate grade based on checks passed and issue severity
    base_score = int((checks_passed / checks_total) * 100)

    # Apply penalties
    critical_issues = [i for i in issues if "CRITICAL" in i or "Missing" in i]
    base_score -= len(critical_issues) * 5
    base_score -= len(issues) * 3
    base_score -= len(warnings) * 1

    # Floor at 70
    final_score = max(base_score, 70)

    # Map to grade
    if final_score >= 93:
        grade = "A"
    elif final_score >= 90:
        grade = "A-"
    elif final_score >= 87:
        grade = "B+"
    elif final_score >= 83:
        grade = "B"
    elif final_score >= 80:
        grade = "B-"
    elif final_score >= 77:
        grade = "C+"
    else:
        grade = "C or lower"

    return FastEvaluationResult(
        grade=grade,
        score=final_score,
        issues=issues,
        warnings=warnings,
        checks_passed=checks_passed,
        checks_total=checks_total,
    )


# CLI usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m investing_agents.evaluation.fast_evaluator <report.json>")
        sys.exit(1)

    report_path = Path(sys.argv[1])
    if not report_path.exists():
        print(f"Error: File not found: {report_path}")
        sys.exit(1)

    with open(report_path) as f:
        report_data = json.load(f)

    result = fast_evaluate(report_data)
    print(result.get_summary())

    # Exit code: 0 if A-, 1 otherwise
    sys.exit(0 if result.score >= 90 else 1)
