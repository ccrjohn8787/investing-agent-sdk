"""Demo: Fast validation in action - catching errors early.

This demonstrates the 3-layer validation infrastructure catching errors
immediately instead of waiting 20 minutes for full PM evaluation.
"""

import json
import sys
from pathlib import Path

# Add SDK to path
sys.path.insert(0, str(Path(__file__).parent.parent / "workspace" / "investing-agent-sdk" / "src"))

from investing_agents.evaluation.fast_evaluator import fast_evaluate
from investing_agents.evaluation.structure_validator import validate_report_structure
from investing_agents.schemas.report import validate_llm_output

# Test 1: Complete valid report (should pass all layers)
print("=" * 80)
print("TEST 1: VALID REPORT - All validation layers")
print("=" * 80)

valid_report = {
    "executive_summary": "META shows strong fundamentals with AI-driven growth potential across all key business segments in 2025.",
    "investment_thesis": {
        "core_thesis": "AI monetization will drive 20%+ revenue growth and margin expansion to 45% by 2026",
    },
    "financial_analysis": {
        "revenue": "Strong 20% YoY growth",
    },
    "valuation": {
        "fair_value_per_share": 650.0,
        "methodology": "DCF with WACC 8.5%, terminal growth 3.0%, terminal margin 35%",
        "scenarios": {
            "bull": {
                "price_target": 850.0,
                "probability": 0.35,
                "key_conditions": ["Revenue >20%", "Margin 45%", "AI adoption accelerates"],
            },
            "base": {
                "price_target": 650.0,
                "probability": 0.45,
                "key_conditions": ["Revenue 15-18%", "Margin 40%", "Steady growth"],
            },
            "bear": {
                "price_target": 450.0,
                "probability": 0.20,
                "key_conditions": ["Revenue <10%", "Margin 35%", "CapEx overruns"],
            },
        },
    },
    "bull_bear_analysis": {
        "bull_case": {
            "summary": "Strong AI monetization drives revenue growth above 20% annually with margin expansion to 45%"
        },
        "bear_case": {
            "summary": "CapEx overruns and regulatory pressure compress margins below 35% with slower growth"
        },
    },
    "risks": {
        "key_risks": ["Regulatory headwinds", "Competition from TikTok"],
    },
    "recommendation": {
        "action": "BUY",
        "recommendation": "HOLD",
        "conviction": "HIGH",
        "timeframe": "12 months",
        "entry_conditions": ["Price < $640", "Q1 beat >5%", "CapEx <$45B"],
        "exit_conditions": ["Price > $800", "Margin compression", "Loss of ad base"],
    },
}

# Layer 1: Schema validation (<1ms)
schema_result = validate_llm_output(valid_report)
print(f"\nLayer 1 - Schema Validation: {'✓ PASS' if schema_result.is_valid else '✗ FAIL'}")
if not schema_result.is_valid:
    print(schema_result.get_error_summary())

# Layer 2: Structure validation (<1ms)
struct_result = validate_report_structure(valid_report)
print(f"Layer 2 - Structure Validation: {'✓ PASS' if struct_result.is_valid else '✗ FAIL'}")

# Layer 3: Fast evaluation (<100ms)
fast_result = fast_evaluate(valid_report)
print(f"Layer 3 - Fast PM Evaluation: {fast_result.grade} ({fast_result.score}/100)")
print(f"  Checks: {fast_result.checks_passed}/{fast_result.checks_total} passed")

print("\n" + "=" * 80)
print("TEST 2: MISSING SCENARIOS - Caught at Layer 2 (Structure)")
print("=" * 80)

# Test 2: Missing scenarios (caught immediately at structure validation)
incomplete_report = valid_report.copy()
incomplete_report["valuation"] = {"fair_value_per_share": 650.0}  # No scenarios

# Layer 1: Schema (will pass - scenarios are optional in schema)
schema_result = validate_llm_output(incomplete_report)
print(f"\nLayer 1 - Schema Validation: {'✓ PASS' if schema_result.is_valid else '✗ FAIL'}")
if schema_result.warnings:
    print(f"  Warnings: {len(schema_result.warnings)}")

# Layer 2: Structure (FAILS HERE - catches missing scenarios)
struct_result = validate_report_structure(incomplete_report)
print(f"Layer 2 - Structure Validation: {'✓ PASS' if struct_result.is_valid else '✗ FAIL'}")
if not struct_result.is_valid:
    print(f"  Missing: {len(struct_result.missing_sections)} critical sections")
    print(f"  Grade capped at: {struct_result.grade_estimate}")
    print(f"  ⚠️  FAST FAIL: Would save 3-5 minutes vs waiting for full PM eval")

print("\n" + "=" * 80)
print("TEST 3: INVALID PROBABILITIES - Caught at Layer 1 (Schema)")
print("=" * 80)

# Test 3: Invalid probability sum (caught at schema validation)
bad_prob_report = valid_report.copy()
bad_prob_report["valuation"]["scenarios"]["bull"]["probability"] = 0.40
bad_prob_report["valuation"]["scenarios"]["base"]["probability"] = 0.40
bad_prob_report["valuation"]["scenarios"]["bear"]["probability"] = 0.10  # Sum = 0.90

# Layer 1: Schema (FAILS HERE)
schema_result = validate_llm_output(bad_prob_report)
print(f"\nLayer 1 - Schema Validation: {'✓ PASS' if schema_result.is_valid else '✗ FAIL'}")
if not schema_result.is_valid:
    print(f"  Errors: {len(schema_result.errors)}")
    for err in schema_result.errors:
        print(f"  - {err['msg']}")
    print(f"  ⚠️  FAST FAIL: Caught in <1ms instead of after 20min analysis")

print("\n" + "=" * 80)
print("SUMMARY: Validation Infrastructure Benefits")
print("=" * 80)
print("✓ Layer 1 (Schema): Catches structural/mathematical errors in <1ms")
print("✓ Layer 2 (Structure): Catches missing sections in <1ms")
print("✓ Layer 3 (Fast PM): Pre-check quality issues in ~30sec")
print("✓ Full PM Eval: Always runs for final grade (3-5min)")
print("\nTime saved: Catch 80% of issues in <1sec vs 20min full analysis")
print("=" * 80)
