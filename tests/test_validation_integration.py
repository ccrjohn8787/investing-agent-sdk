"""Integration tests for validation pipeline (Phase 2E).

Tests the complete validation workflow:
1. Schema validation on LLM output
2. Report structure validation
3. Fast PM evaluation pre-check
4. Scenario generation and preservation
5. Valuation merge operations

Usage:
    pytest tests/test_validation_integration.py -v
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

from investing_agents.evaluation.fast_evaluator import fast_evaluate
from investing_agents.evaluation.structure_validator import validate_report_structure
from investing_agents.schemas.report import validate_llm_output


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def minimal_valid_report() -> Dict[str, Any]:
    """Minimal report that passes all validation layers."""
    return {
        "executive_summary": "META presents strong fundamentals with AI-driven growth potential across all segments in 2025.",
        "investment_thesis": {
            "core_thesis": "AI monetization will drive 20%+ revenue growth and margin expansion to 45% by 2026",
        },
        "financial_analysis": {
            "revenue": "Strong 20% YoY growth in Q3 2024",
            "profitability": "Operating margin expanded to 42%",
        },
        "valuation": {
            "fair_value_per_share": 650.0,
            "methodology": "DCF with WACC 8.5%, terminal growth 3.0%, terminal margin 35%",
            "scenarios": {
                "bull": {
                    "price_target": 850.0,
                    "probability": 0.35,
                    "key_conditions": [
                        "Revenue growth >20%",
                        "Operating margin to 45%",
                        "AI monetization exceeds expectations",
                    ],
                },
                "base": {
                    "price_target": 650.0,
                    "probability": 0.45,
                    "key_conditions": [
                        "Revenue growth 15-18%",
                        "Operating margin 40%",
                        "Steady AI adoption",
                    ],
                },
                "bear": {
                    "price_target": 450.0,
                    "probability": 0.20,
                    "key_conditions": [
                        "Revenue growth <10%",
                        "Margin compression to 35%",
                        "Regulatory headwinds",
                    ],
                },
            },
        },
        "bull_bear_analysis": {
            "bull_case": {
                "summary": "AI monetization accelerates with 45% operating margins by 2026 driven by Llama adoption",
            },
            "bear_case": {
                "summary": "CapEx overruns and regulatory pressure compress margins to 35% with slower growth",
            },
        },
        "risks": {
            "key_risks": [
                "Regulatory headwinds in EU and US",
                "Competition from TikTok and emerging platforms",
            ],
        },
        "recommendation": {
            "action": "BUY",
            "recommendation": "HOLD",  # Structure validator expects this field
            "conviction": "HIGH",
            "timeframe": "12 months",
            "entry_conditions": [
                "Price < $640",
                "Q1 2025 revenue beat >5%",
                "No major regulatory actions",
            ],
            "exit_conditions": [
                "Price > $800",
                "Operating margin compression",
                "Loss of advertiser base",
            ],
        },
    }


@pytest.fixture
def incomplete_report() -> Dict[str, Any]:
    """Report missing critical sections (should fail validation)."""
    return {
        "executive_summary": "Short summary text here that meets minimum length requirements for validation.",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {},  # Empty
        "valuation": {
            "fair_value_per_share": 650.0,
            # Missing scenarios
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "bull case summary text"},
            "bear_case": {"summary": "bear case summary text"},
        },
        "risks": {},  # Empty
        "recommendation": {"action": "BUY"},
    }


@pytest.fixture
def invalid_scenarios_report(minimal_valid_report: Dict[str, Any]) -> Dict[str, Any]:
    """Report with invalid scenario structure (wrong price ordering)."""
    report = minimal_valid_report.copy()
    report["valuation"]["scenarios"] = {
        "bull": {
            "price_target": 450.0,  # Wrong - bull should be highest
            "probability": 0.35,
            "key_conditions": ["x"],
        },
        "base": {
            "price_target": 650.0,
            "probability": 0.45,
            "key_conditions": ["y"],
        },
        "bear": {
            "price_target": 850.0,  # Wrong - bear should be lowest
            "probability": 0.20,
            "key_conditions": ["z"],
        },
    }
    return report


# ============================================================================
# Test 1: Complete Validation Pipeline
# ============================================================================


def test_complete_validation_pipeline_success(minimal_valid_report: Dict[str, Any]):
    """Test that a valid report passes all validation layers."""

    # Layer 1: Schema validation
    schema_result = validate_llm_output(minimal_valid_report)
    assert schema_result.is_valid, f"Schema validation failed: {schema_result.get_error_summary()}"
    assert len(schema_result.errors) == 0

    # Layer 2: Report structure validation
    struct_result = validate_report_structure(minimal_valid_report)
    assert struct_result.is_valid, f"Structure validation failed: {struct_result.missing_sections}"
    assert len(struct_result.missing_sections) == 0

    # Layer 3: Fast PM evaluation
    fast_result = fast_evaluate(minimal_valid_report)
    assert fast_result.score >= 90, f"Fast evaluation scored {fast_result.score}, expected >=90"
    assert fast_result.grade in ["A-", "A"], f"Grade {fast_result.grade} below A-"
    assert len(fast_result.issues) == 0, f"Unexpected issues: {fast_result.issues}"

    # Verify key metrics
    assert fast_result.checks_passed >= 8, f"Only {fast_result.checks_passed} checks passed"
    assert fast_result.checks_total >= 8


def test_complete_validation_pipeline_failure(incomplete_report: Dict[str, Any]):
    """Test that an incomplete report fails at appropriate validation layers."""

    # Layer 1: Schema validation - should catch missing fields
    schema_result = validate_llm_output(incomplete_report)
    assert not schema_result.is_valid, "Schema validation should fail for incomplete report"
    assert len(schema_result.errors) > 0

    # Layer 2: Report structure validation - should catch missing sections
    struct_result = validate_report_structure(incomplete_report)
    assert not struct_result.is_valid, "Structure validation should fail"
    assert "valuation.scenarios" in str(struct_result.missing_sections)

    # Layer 3: Fast PM evaluation - should identify critical issues
    fast_result = fast_evaluate(incomplete_report)
    assert fast_result.score < 90, f"Score {fast_result.score} too high for incomplete report"
    assert len(fast_result.issues) > 0, "Should have critical issues"


# ============================================================================
# Test 2: Scenario Validation
# ============================================================================


def test_scenario_price_ordering_validation(invalid_scenarios_report: Dict[str, Any]):
    """Test that invalid scenario price ordering is caught by schema validation."""
    schema_result = validate_llm_output(invalid_scenarios_report)
    assert not schema_result.is_valid, "Should fail on invalid price ordering"

    # Should have error about bull/base/bear ordering
    error_messages = [err["msg"] for err in schema_result.errors]
    assert any("should be >=" in msg for msg in error_messages)


def test_scenario_probability_sum_validation():
    """Test that scenario probabilities must sum to 1.0."""
    report = {
        "executive_summary": "META presents strong fundamentals with AI-driven growth potential across all key business segments.",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {
            "fair_value_per_share": 650.0,
            "scenarios": {
                "bull": {"price_target": 850, "probability": 0.40, "key_conditions": ["x"]},
                "base": {"price_target": 650, "probability": 0.40, "key_conditions": ["y"]},
                "bear": {"price_target": 450, "probability": 0.10, "key_conditions": ["z"]},
                # Sum = 0.90, not 1.0
            },
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization drives revenue growth above 20% annually with margin expansion"},
            "bear_case": {"summary": "CapEx overruns compress margins below 35% with regulatory headwinds slowing growth"},
        },
        "risks": {"risk": "x"},
        "recommendation": {"action": "BUY"},
    }

    schema_result = validate_llm_output(report)
    assert not schema_result.is_valid, "Should fail on probability sum"
    error_messages = [err["msg"] for err in schema_result.errors]
    assert any("sum to 1.0" in msg for msg in error_messages)


def test_scenario_preservation_through_pipeline(minimal_valid_report: Dict[str, Any]):
    """Test that scenarios are preserved through all validation layers."""

    # Extract original scenarios
    original_scenarios = minimal_valid_report["valuation"]["scenarios"]
    original_bull_price = original_scenarios["bull"]["price_target"]
    original_base_price = original_scenarios["base"]["price_target"]
    original_bear_price = original_scenarios["bear"]["price_target"]

    # Pass through schema validation
    schema_result = validate_llm_output(minimal_valid_report)
    assert schema_result.is_valid

    # Pass through structure validation
    struct_result = validate_report_structure(minimal_valid_report)
    assert struct_result.is_valid

    # Pass through fast evaluation
    fast_result = fast_evaluate(minimal_valid_report)

    # Verify scenarios are still intact in original report
    assert minimal_valid_report["valuation"]["scenarios"]["bull"]["price_target"] == original_bull_price
    assert minimal_valid_report["valuation"]["scenarios"]["base"]["price_target"] == original_base_price
    assert minimal_valid_report["valuation"]["scenarios"]["bear"]["price_target"] == original_bear_price

    # Verify fast evaluation detected the scenarios
    assert fast_result.score >= 90, "Should pass with valid scenarios"


# ============================================================================
# Test 3: Fast Evaluator Pre-Check Workflow
# ============================================================================


def test_fast_evaluator_as_precheck(minimal_valid_report: Dict[str, Any]):
    """Test that fast evaluator correctly positions itself as pre-check."""

    fast_result = fast_evaluate(minimal_valid_report)
    summary = fast_result.get_summary()

    # Verify messaging emphasizes pre-check nature
    assert "PRE-CHECK" in summary, "Summary should mention PRE-CHECK"
    assert "full pm eval" in summary.lower(), "Should reference full PM evaluation"
    assert "MANDATORY" in summary or "required" in summary.lower(), "Should emphasize PM eval is required"


def test_fast_evaluator_never_replaces_pm_eval(incomplete_report: Dict[str, Any]):
    """Test that fast evaluator messages emphasize PM eval even on failure."""

    fast_result = fast_evaluate(incomplete_report)
    summary = fast_result.get_summary()

    # Even when fast check fails, should still say to run full PM eval
    assert "FULL PM EVALUATION" in summary, "Should mention full PM eval even on failure"
    assert "PRE-CHECK" in summary, "Should clarify this is just pre-check"


def test_fast_evaluator_warnings_dont_block_pm_eval(minimal_valid_report: Dict[str, Any]):
    """Test that warnings in fast evaluator don't prevent PM evaluation."""

    # Create report with warnings (short methodology)
    report = minimal_valid_report.copy()
    report["valuation"]["methodology"] = "DCF valuation model used"  # Short but valid

    fast_result = fast_evaluate(report)

    # Should have warnings but still pass
    assert fast_result.score >= 83, "Should pass despite warnings"
    assert len(fast_result.warnings) > 0, "Should have warnings about methodology"

    # Summary should still recommend PM eval
    summary = fast_result.get_summary()
    assert "FULL PM EVAL" in summary or "full pm eval" in summary.lower()


# ============================================================================
# Test 4: Multi-Layer Error Detection
# ============================================================================


def test_error_propagation_through_layers():
    """Test that errors are caught at the appropriate layer."""

    # Error 1: Missing required field (caught by schema)
    report_missing_field = {
        "executive_summary": "Summary text that is long enough to pass minimum validation requirements",
        # Missing investment_thesis
        "financial_analysis": {"x": "y"},
        "valuation": {"fair_value_per_share": 650},
        "bull_bear_analysis": {
            "bull_case": {"summary": "bull case text"},
            "bear_case": {"summary": "bear case text"},
        },
        "risks": {"x": "y"},
        "recommendation": {"action": "BUY"},
    }

    schema_result = validate_llm_output(report_missing_field)
    assert not schema_result.is_valid, "Schema should catch missing field"
    assert any("investment_thesis" in str(err["loc"]) for err in schema_result.errors)

    # Error 2: Invalid scenario structure (caught by schema)
    report_bad_scenarios = {
        "executive_summary": "META shows strong fundamentals with significant growth potential driven by AI adoption",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {
            "fair_value_per_share": 650,
            "scenarios": {
                "bull": {"price_target": 850, "probability": 1.5, "key_conditions": ["x"]},  # Invalid prob
                "base": {"price_target": 650, "probability": 0.45, "key_conditions": ["y"]},
                "bear": {"price_target": 450, "probability": 0.20, "key_conditions": ["z"]},
            },
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization drives revenue growth above expectations"},
            "bear_case": {"summary": "CapEx overruns compress margins below target levels"},
        },
        "risks": {"risk": "x"},
        "recommendation": {"action": "BUY"},
    }

    schema_result = validate_llm_output(report_bad_scenarios)
    assert not schema_result.is_valid, "Schema should catch invalid probability"

    # Error 3: Missing subsections (caught by structure validator)
    report_missing_subsections = {
        "executive_summary": "META demonstrates strong fundamentals with AI-driven growth across all business segments",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {
            "fair_value_per_share": 650,
            # Missing scenarios - valid per schema (optional) but caught by structure
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization drives 20%+ revenue growth with margin expansion"},
            "bear_case": {"summary": "CapEx overruns and regulatory pressure compress margins below 35%"},
        },
        "risks": {"risk": "x"},
        "recommendation": {"action": "BUY"},
    }

    struct_result = validate_report_structure(report_missing_subsections)
    assert not struct_result.is_valid, "Structure validator should catch missing scenarios"
    assert any("scenarios" in section for section in struct_result.missing_sections)

    # Error 4: Quality issues (caught by fast evaluator)
    report_quality_issues = {
        "executive_summary": "x" * 100,  # Meets length but low quality
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {
            "fair_value_per_share": 650,
            "methodology": "x" * 30,  # Short
            "scenarios": {
                "bull": {"price_target": 660, "probability": 0.35, "key_conditions": ["x"]},
                "base": {"price_target": 650, "probability": 0.45, "key_conditions": ["y"]},
                "bear": {"price_target": 640, "probability": 0.20, "key_conditions": ["z"]},
                # Narrow spread - quality issue
            },
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "x" * 50},
            "bear_case": {"summary": "y" * 50},
        },
        "risks": {"risk": "x"},
        "recommendation": {
            "action": "BUY",
            # Missing entry/exit conditions - quality issue
        },
    }

    fast_result = fast_evaluate(report_quality_issues)
    assert fast_result.score < 90, "Fast evaluator should catch quality issues"
    assert len(fast_result.warnings) > 0, "Should have warnings about quality"


# ============================================================================
# Test 5: Real-World Workflow Simulation
# ============================================================================


def test_typical_development_workflow():
    """Simulate typical developer workflow with validation layers."""

    # Step 1: Developer creates report structure
    draft_report = {
        "executive_summary": "Initial draft summary that needs to be long enough for validation",
        "investment_thesis": {"core_thesis": "Draft thesis"},
        "financial_analysis": {"revenue": "Draft analysis"},
        "valuation": {"fair_value_per_share": 650.0},
        "bull_bear_analysis": {
            "bull_case": {"summary": "draft bull case text goes here"},
            "bear_case": {"summary": "draft bear case text goes here"},
        },
        "risks": {"key_risks": ["risk1"]},
        "recommendation": {"action": "BUY"},
    }

    # Step 2: Run schema validation (immediate feedback)
    schema_result = validate_llm_output(draft_report)
    # Should pass basic schema but have warnings
    assert schema_result.is_valid, "Basic structure should be valid"
    assert len(schema_result.warnings) > 0, "Should have warnings about missing scenarios"

    # Step 3: Run structure validation (catches missing subsections)
    struct_result = validate_report_structure(draft_report)
    assert not struct_result.is_valid, "Structure check should fail"
    assert "valuation.scenarios" in str(struct_result.missing_sections)

    # Step 4: Developer adds scenarios
    draft_report["valuation"]["scenarios"] = {
        "bull": {"price_target": 850, "probability": 0.35, "key_conditions": ["Revenue >20%"]},
        "base": {"price_target": 650, "probability": 0.45, "key_conditions": ["Revenue 15%"]},
        "bear": {"price_target": 450, "probability": 0.20, "key_conditions": ["Revenue <10%"]},
    }
    draft_report["valuation"]["methodology"] = "DCF with WACC 8.5%, terminal growth 3%, terminal margin 35%"
    draft_report["recommendation"]["recommendation"] = "HOLD"
    draft_report["recommendation"]["entry_conditions"] = ["Price < $640", "Q1 beat >5%", "CapEx <$45B"]
    draft_report["recommendation"]["exit_conditions"] = ["Price > $800", "CapEx >$50B", "Margin decline"]

    # Step 5: Re-run validations
    schema_result = validate_llm_output(draft_report)
    assert schema_result.is_valid

    struct_result = validate_report_structure(draft_report)
    assert struct_result.is_valid

    # Step 6: Run fast PM check (pre-check before full PM eval)
    fast_result = fast_evaluate(draft_report)
    # Should pass with some warnings
    assert fast_result.score >= 83, f"Score {fast_result.score} too low"

    # Step 7: Verify summary recommends full PM eval
    summary = fast_result.get_summary()
    assert "FULL PM EVALUATION" in summary or "full PM eval" in summary.lower()


# ============================================================================
# Test 6: Regression Prevention
# ============================================================================


def test_schema_validation_doesnt_modify_report(minimal_valid_report: Dict[str, Any]):
    """Test that validation doesn't modify the original report."""
    original_json = json.dumps(minimal_valid_report, sort_keys=True)

    # Run all validation layers
    validate_llm_output(minimal_valid_report)
    validate_report_structure(minimal_valid_report)
    fast_evaluate(minimal_valid_report)

    # Verify report unchanged
    after_json = json.dumps(minimal_valid_report, sort_keys=True)
    assert original_json == after_json, "Validation should not modify report"


def test_validation_layers_are_independent():
    """Test that each validation layer can run independently."""

    report = {
        "executive_summary": "META demonstrates strong fundamentals with AI-driven growth potential across all key business segments in 2025.",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {"fair_value_per_share": 650},
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization drives revenue growth above 20% annually with margin expansion to 45%"},
            "bear_case": {"summary": "CapEx overruns compress margins below 35% with regulatory headwinds slowing user growth"},
        },
        "risks": {"risk": "x"},
        "recommendation": {"action": "BUY"},
    }

    # Should be able to run in any order
    fast_result = fast_evaluate(report)
    struct_result = validate_report_structure(report)
    schema_result = validate_llm_output(report)

    # Each should work independently
    assert isinstance(fast_result.score, int)
    assert isinstance(struct_result.is_valid, bool)
    assert isinstance(schema_result.is_valid, bool)


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
