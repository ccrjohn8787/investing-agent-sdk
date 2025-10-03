"""Tests for LLM output schema validation (Phase 1C).

Validates that Pydantic schemas correctly catch structural issues in LLM outputs.

Usage:
    pytest tests/test_schema_validation.py -v
"""

import pytest

from investing_agents.schemas.report import (
    InvestmentReport,
    Valuation,
    ValuationScenarios,
    validate_llm_output,
)


def test_valid_complete_report():
    """Test that a complete valid report passes validation."""
    valid_report = {
        "executive_summary": "META is a strong buy with 35% upside potential based on AI monetization.",
        "investment_thesis": {
            "core_thesis": "AI-driven ad optimization will expand margins",
        },
        "financial_analysis": {
            "revenue": "Strong 20% YoY growth",
        },
        "valuation": {
            "fair_value_per_share": 650.0,
            "methodology": "DCF with WACC 8.5%, terminal growth 3%, terminal margin 35%",
            "scenarios": {
                "bull": {
                    "price_target": 850.0,
                    "probability": 0.35,
                    "key_conditions": ["Revenue >20%", "Margin to 45%"],
                },
                "base": {
                    "price_target": 650.0,
                    "probability": 0.45,
                    "key_conditions": ["Revenue 15-18%", "Margin 40%"],
                },
                "bear": {
                    "price_target": 450.0,
                    "probability": 0.20,
                    "key_conditions": ["Revenue <10%", "Margin 35%"],
                },
            },
        },
        "bull_bear_analysis": {
            "bull_case": {
                "summary": "AI monetization accelerates with 45% margins by 2026",
            },
            "bear_case": {
                "summary": "CapEx overruns compress margins to 35%",
            },
        },
        "risks": {
            "key_risks": ["Regulatory headwinds", "Competition from TikTok"],
        },
        "recommendation": {
            "action": "BUY",
            "conviction": "HIGH",
            "timeframe": "12 months",
            "entry_conditions": ["Price < $640", "Q1 revenue beat >5%"],
            "exit_conditions": ["Price > $800", "Margin compression"],
        },
    }

    result = validate_llm_output(valid_report)
    assert result.is_valid
    assert len(result.errors) == 0


def test_missing_required_sections():
    """Test that missing required sections fails validation."""
    incomplete_report = {
        "executive_summary": "Short summary",
        # Missing investment_thesis, financial_analysis, etc.
        "valuation": {},
        "bull_bear_analysis": {
            "bull_case": {"summary": "x"},
            "bear_case": {"summary": "y"},
        },
        "risks": {},
        "recommendation": {"action": "BUY"},
    }

    result = validate_llm_output(incomplete_report)
    assert not result.is_valid
    # Should have errors for missing sections
    error_locs = [str(err["loc"]) for err in result.errors]
    assert any("investment_thesis" in loc for loc in error_locs)


def test_invalid_recommendation_action():
    """Test that invalid recommendation action fails validation."""
    invalid_report = {
        "executive_summary": "Summary with sufficient length to pass validation",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {},
        "bull_bear_analysis": {
            "bull_case": {"summary": "bull case summary here"},
            "bear_case": {"summary": "bear case summary here"},
        },
        "risks": {"risk": "x"},
        "recommendation": {
            "action": "STRONG_BUY",  # Invalid - should be BUY/HOLD/SELL
        },
    }

    result = validate_llm_output(invalid_report)
    assert not result.is_valid
    # Check that error is about recommendation.action
    error_messages = [err["msg"] for err in result.errors]
    assert any("pattern" in msg.lower() or "action" in str(err["loc"])
               for err, msg in zip(result.errors, error_messages))


def test_scenario_probabilities_sum():
    """Test that scenario probabilities must sum to 1.0."""
    scenarios = {
        "bull": {
            "price_target": 850.0,
            "probability": 0.40,
            "key_conditions": ["x"],
        },
        "base": {
            "price_target": 650.0,
            "probability": 0.40,
            "key_conditions": ["y"],
        },
        "bear": {
            "price_target": 450.0,
            "probability": 0.10,  # Sum = 0.90, not 1.0
            "key_conditions": ["z"],
        },
    }

    with pytest.raises(ValueError, match="sum to 1.0"):
        ValuationScenarios.model_validate(scenarios)


def test_scenario_price_ordering():
    """Test that bull > base > bear price targets."""
    invalid_ordering = {
        "bull": {
            "price_target": 600.0,  # Bull should be highest
            "probability": 0.35,
            "key_conditions": ["x"],
        },
        "base": {
            "price_target": 650.0,  # Base higher than bull
            "probability": 0.45,
            "key_conditions": ["y"],
        },
        "bear": {
            "price_target": 450.0,
            "probability": 0.20,
            "key_conditions": ["z"],
        },
    }

    with pytest.raises(ValueError, match="should be >="):
        ValuationScenarios.model_validate(invalid_ordering)


def test_missing_scenarios_generates_warning():
    """Test that missing scenarios generates warning (not error)."""
    report_no_scenarios = {
        "executive_summary": "META shows strong fundamentals with AI-driven growth potential across all segments in 2025.",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {
            "fair_value_per_share": 650.0,
            # Missing scenarios
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization drives revenue growth above 20% annually"},
            "bear_case": {"summary": "CapEx overruns compress margins below 35% in base case"},
        },
        "risks": {"risk": "x"},
        "recommendation": {"action": "BUY"},
    }

    result = validate_llm_output(report_no_scenarios)
    # Should pass validation but have warnings
    assert result.is_valid
    assert len(result.warnings) > 0
    assert any("scenarios" in w.lower() for w in result.warnings)
    assert any("grade will be capped" in w for w in result.warnings)


def test_short_methodology_generates_warning():
    """Test that short methodology generates warning."""
    report_short_method = {
        "executive_summary": "META presents a strong investment opportunity with AI-driven growth potential across all key segments in 2025.",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {
            "fair_value_per_share": 650.0,
            "methodology": "DCF valuation model used",  # Meets 20 char min but too short for quality
            "scenarios": {
                "bull": {"price_target": 850, "probability": 0.35, "key_conditions": ["Revenue >20%"]},
                "base": {"price_target": 650, "probability": 0.45, "key_conditions": ["Revenue 15%"]},
                "bear": {"price_target": 450, "probability": 0.20, "key_conditions": ["Revenue <10%"]},
            },
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization drives revenue growth above target"},
            "bear_case": {"summary": "CapEx overruns compress margins below expectations"},
        },
        "risks": {"risk": "x"},
        "recommendation": {"action": "BUY"},
    }

    result = validate_llm_output(report_short_method)
    # Should pass but warn about short methodology
    assert result.is_valid
    assert any("methodology too short" in w.lower() for w in result.warnings)


def test_missing_entry_exit_conditions_warning():
    """Test that missing entry/exit conditions generates warnings."""
    report_no_conditions = {
        "executive_summary": "META presents a compelling investment case with AI-driven growth across all business segments in 2025.",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {
            "fair_value_per_share": 650.0,
            "scenarios": {
                "bull": {"price_target": 850, "probability": 0.35, "key_conditions": ["Revenue >20%"]},
                "base": {"price_target": 650, "probability": 0.45, "key_conditions": ["Revenue 15%"]},
                "bear": {"price_target": 450, "probability": 0.20, "key_conditions": ["Revenue <10%"]},
            },
        },
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization drives revenue growth above expectations"},
            "bear_case": {"summary": "CapEx overruns compress margins below target levels"},
        },
        "risks": {"risk": "x"},
        "recommendation": {
            "action": "BUY",
            # Missing entry_conditions and exit_conditions
        },
    }

    result = validate_llm_output(report_no_conditions)
    assert result.is_valid
    assert any("entry_conditions" in w.lower() for w in result.warnings)
    assert any("exit_conditions" in w.lower() for w in result.warnings)


def test_validation_result_error_summary():
    """Test that ValidationResult provides readable error summary."""
    invalid_report = {
        "executive_summary": "x",  # Too short
        "investment_thesis": {},  # Empty
        "financial_analysis": {},  # Empty
        "valuation": {},
        "bull_bear_analysis": {
            "bull_case": {"summary": "x"},  # Too short
            "bear_case": {"summary": "y"},  # Too short
        },
        "risks": {},
        "recommendation": {"action": "MAYBE"},  # Invalid
    }

    result = validate_llm_output(invalid_report)
    assert not result.is_valid

    summary = result.get_error_summary()
    assert "✗ Schema validation failed" in summary
    assert len(result.errors) > 0


def test_empty_conditions_list_fails():
    """Test that empty conditions lists fail validation."""
    scenarios_empty_conditions = {
        "bull": {
            "price_target": 850.0,
            "probability": 0.35,
            "key_conditions": [],  # Empty list
        },
        "base": {
            "price_target": 650.0,
            "probability": 0.45,
            "key_conditions": ["x"],
        },
        "bear": {
            "price_target": 450.0,
            "probability": 0.20,
            "key_conditions": ["y"],
        },
    }

    with pytest.raises(ValueError):
        ValuationScenarios.model_validate(scenarios_empty_conditions)


def test_negative_price_target_fails():
    """Test that negative price targets fail validation."""
    invalid_valuation = {
        "fair_value_per_share": -100.0,  # Negative price
    }

    with pytest.raises(ValueError):
        Valuation.model_validate(invalid_valuation)


def test_probability_out_of_range_fails():
    """Test that probabilities outside [0, 1] fail validation."""
    invalid_scenario = {
        "bull": {
            "price_target": 850.0,
            "probability": 1.5,  # > 1.0
            "key_conditions": ["x"],
        },
        "base": {
            "price_target": 650.0,
            "probability": 0.45,
            "key_conditions": ["y"],
        },
        "bear": {
            "price_target": 450.0,
            "probability": -0.05,  # < 0.0
            "key_conditions": ["z"],
        },
    }

    with pytest.raises(ValueError):
        ValuationScenarios.model_validate(invalid_scenario)


def test_validation_with_extra_fields_allowed():
    """Test that extra fields are allowed (LLM might add custom fields)."""
    report_with_extras = {
        "executive_summary": "META demonstrates strong fundamentals with AI-driven growth potential across all segments in 2025.",
        "investment_thesis": {"thesis": "x"},
        "financial_analysis": {"analysis": "x"},
        "valuation": {"fair_value_per_share": 650},
        "bull_bear_analysis": {
            "bull_case": {"summary": "Strong AI monetization drives revenue growth above 20% annually"},
            "bear_case": {"summary": "CapEx overruns compress margins below 35% in base case"},
        },
        "risks": {"risk": "x"},
        "recommendation": {"action": "BUY"},
        "custom_field": "This should be allowed",  # Extra field
        "another_extra": {"nested": "data"},
    }

    result = validate_llm_output(report_with_extras)
    # Should pass - we allow extra fields (might have warnings for missing scenarios)
    assert result.is_valid


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
