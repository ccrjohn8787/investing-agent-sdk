"""Comprehensive mathematical verification tests for valuation kernel.

This test suite includes:
1. Legacy tests ported from the original codebase (mathematical properties)
2. Hand-calculated reference values for full verification
3. Step-by-step formula verification
"""

import pytest
import numpy as np
from investing_agents.schemas.inputs import InputsI, Drivers, Macro, Discounting
from investing_agents.valuation.ginzu import value, series


# ============================================================================
# PART 1: LEGACY TESTS (Ported from original codebase)
# These verify mathematical properties and constraints
# ============================================================================

def base_inputs(T: int = 10, mode: str = "end") -> InputsI:
    """Standard test inputs used by legacy tests."""
    return InputsI(
        company="SyntheticCo",
        ticker="SYN",
        currency="USD",
        shares_out=1_000.0,
        tax_rate=0.25,
        revenue_t0=1000.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.04] * T,
            oper_margin=[0.12] * T,
            stable_growth=0.02,
            stable_margin=0.12,
        ),
        sales_to_capital=[2.0] * T,
        wacc=[0.04] * T,
        macro=Macro(risk_free_curve=[0.04] * T, erp=0.05, country_risk=0.0),
        discounting=Discounting(mode=mode),
    )


def test_pv_bridge_exact():
    """Verify PV bridge: PV_explicit + PV_terminal = PV_oper_assets (identity)."""
    I = base_inputs(T=8, mode="end")
    V = value(I)

    bridge_check = abs((V.pv_explicit + V.pv_terminal) - V.pv_oper_assets)
    assert bridge_check < 1e-8, f"PV bridge violated by {bridge_check}"

    print(f"✓ PV Bridge Test: {V.pv_explicit:.2f} + {V.pv_terminal:.2f} = {V.pv_oper_assets:.2f}")


def test_midyear_uplift_band():
    """Verify midyear discounting produces 1.5-3.5% uplift vs end-year."""
    I_end = base_inputs(T=12, mode="end")
    I_mid = base_inputs(T=12, mode="midyear")
    V_end = value(I_end)
    V_mid = value(I_mid)

    uplift = (V_mid.pv_oper_assets / V_end.pv_oper_assets) - 1.0
    assert 0.015 <= uplift <= 0.035, f"Midyear uplift {uplift:.1%} outside expected 1.5-3.5%"

    print(f"✓ Midyear Uplift Test: {uplift:.1%} (within 1.5-3.5% band)")


def test_gradient_signs():
    """Verify value increases with margin, decreases with WACC."""
    I = base_inputs(T=10, mode="end")
    V0 = value(I).equity_value

    # Higher margin → higher value
    I_up_margin = I.model_copy(deep=True)
    I_up_margin.drivers.oper_margin = [m + 0.01 for m in I.drivers.oper_margin]
    V_up_margin = value(I_up_margin).equity_value
    assert V_up_margin > V0, f"Higher margin should increase value: {V_up_margin} <= {V0}"

    # Higher WACC → lower value
    I_up_wacc = I.model_copy(deep=True)
    I_up_wacc.wacc = [w + 0.01 for w in I.wacc]
    V_up_wacc = value(I_up_wacc).equity_value
    assert V_up_wacc < V0, f"Higher WACC should decrease value: {V_up_wacc} >= {V0}"

    margin_sensitivity = (V_up_margin - V0) / V0
    wacc_sensitivity = (V_up_wacc - V0) / V0
    print(f"✓ Gradient Signs Test: +1% margin → +{margin_sensitivity:.1%}, +1% WACC → {wacc_sensitivity:.1%}")


def test_terminal_constraint_raises():
    """Verify constraint: stable_growth < wacc - 50bps."""
    I = base_inputs(T=5)
    I.drivers.stable_growth = I.wacc[-1] - 0.003  # Violates constraint (< 50bps)

    with pytest.raises(ValueError, match="Terminal growth constraint violated"):
        _ = value(I)

    print(f"✓ Terminal Constraint Test: Correctly rejects g_inf >= r_inf - 50bps")


# ============================================================================
# PART 2: HAND-CALCULATED REFERENCE VALUES
# Simple example worked out by hand for full verification
# ============================================================================

def test_hand_calculated_simple_case():
    """
    Hand-calculated DCF example for full verification.

    Setup:
    - Revenue Year 0: $100
    - Growth: 10% Y1, 5% Y2, 0% Y3
    - Operating Margin: 20% (constant)
    - Tax Rate: 25%
    - Sales-to-Capital: 2.0
    - WACC: 10% (constant)
    - Terminal: g=2%, m=20%
    - Discounting: End-year

    Hand Calculations:

    Year 1:
      Revenue: 100 * 1.10 = 110
      EBIT: 110 * 0.20 = 22
      NOPAT: 22 * 0.75 = 16.50
      Reinvestment: (110-100)/2.0 = 5.00
      FCFF: 16.50 - 5.00 = 11.50
      Discount Factor: 1/(1.10) = 0.9091
      PV: 11.50 * 0.9091 = 10.45

    Year 2:
      Revenue: 110 * 1.05 = 115.50
      EBIT: 115.50 * 0.20 = 23.10
      NOPAT: 23.10 * 0.75 = 17.325
      Reinvestment: (115.50-110)/2.0 = 2.75
      FCFF: 17.325 - 2.75 = 14.575
      Discount Factor: 1/(1.10)^2 = 0.8264
      PV: 14.575 * 0.8264 = 12.05

    Year 3:
      Revenue: 115.50 * 1.00 = 115.50
      EBIT: 115.50 * 0.20 = 23.10
      NOPAT: 23.10 * 0.75 = 17.325
      Reinvestment: 0
      FCFF: 17.325
      Discount Factor: 1/(1.10)^3 = 0.7513
      PV: 17.325 * 0.7513 = 13.02

    PV Explicit: 10.45 + 12.05 + 13.02 = 35.52

    Terminal Value (at T=3):
      Revenue T+1: 115.50 * 1.02 = 117.81
      EBIT T+1: 117.81 * 0.20 = 23.562
      NOPAT T+1: 23.562 * 0.75 = 17.6715
      Reinvestment T+1: (117.81-115.50)/2.0 = 1.155
      FCFF T+1: 17.6715 - 1.155 = 16.5165
      TV: 16.5165 / (0.10 - 0.02) = 206.456
      PV Terminal: 206.456 * 0.7513 = 155.11

    PV Operating Assets: 35.52 + 155.11 = 190.63
    """
    inputs = InputsI(
        company="HandCalc",
        ticker="TEST",
        shares_out=100.0,
        tax_rate=0.25,
        revenue_t0=100.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.10, 0.05, 0.00],
            oper_margin=[0.20, 0.20, 0.20],
            stable_growth=0.02,
            stable_margin=0.20,
        ),
        sales_to_capital=[2.0, 2.0, 2.0],
        wacc=[0.10, 0.10, 0.10],
    )

    # Get detailed series for step-by-step verification
    s = series(inputs)

    # Verify revenues
    expected_revenues = np.array([110.0, 115.5, 115.5])
    np.testing.assert_allclose(s.revenue, expected_revenues, rtol=1e-10,
                               err_msg="Revenue calculation mismatch")

    # Verify FCFF Year 1
    expected_fcff_1 = 11.50
    assert abs(s.fcff[0] - expected_fcff_1) < 0.01, f"FCFF Year 1: {s.fcff[0]:.2f} != {expected_fcff_1:.2f}"

    # Verify FCFF Year 2
    expected_fcff_2 = 14.575
    assert abs(s.fcff[1] - expected_fcff_2) < 0.01, f"FCFF Year 2: {s.fcff[1]:.3f} != {expected_fcff_2:.3f}"

    # Verify FCFF Year 3
    expected_fcff_3 = 17.325
    assert abs(s.fcff[2] - expected_fcff_3) < 0.01, f"FCFF Year 3: {s.fcff[2]:.3f} != {expected_fcff_3:.3f}"

    # Verify discount factors
    expected_df = np.array([1/1.10, 1/1.10**2, 1/1.10**3])
    np.testing.assert_allclose(s.discount_factors, expected_df, rtol=1e-10,
                               err_msg="Discount factor calculation mismatch")

    # Verify terminal FCFF
    expected_fcff_T1 = 16.5165
    assert abs(s.fcff_T1 - expected_fcff_T1) < 0.01, f"Terminal FCFF: {s.fcff_T1:.4f} != {expected_fcff_T1:.4f}"

    # Verify terminal value
    expected_tv = 206.456
    assert abs(s.terminal_value_T - expected_tv) < 0.5, f"Terminal Value: {s.terminal_value_T:.2f} != {expected_tv:.2f}"

    # Verify final valuation
    V = value(inputs)

    expected_pv_explicit = 35.52
    assert abs(V.pv_explicit - expected_pv_explicit) < 0.5, f"PV Explicit: {V.pv_explicit:.2f} != {expected_pv_explicit:.2f}"

    expected_pv_terminal = 155.11
    assert abs(V.pv_terminal - expected_pv_terminal) < 0.5, f"PV Terminal: {V.pv_terminal:.2f} != {expected_pv_terminal:.2f}"

    expected_pv_oper = 190.63
    assert abs(V.pv_oper_assets - expected_pv_oper) < 1.0, f"PV Operating: {V.pv_oper_assets:.2f} != {expected_pv_oper:.2f}"

    print(f"✓ Hand-Calculated Test: All intermediate steps verified")
    print(f"  Revenues: {[f'{r:.2f}' for r in s.revenue]}")
    print(f"  FCFFs: {[f'{f:.2f}' for f in s.fcff]}")
    print(f"  PV Explicit: ${V.pv_explicit:.2f} (expected ${expected_pv_explicit:.2f})")
    print(f"  PV Terminal: ${V.pv_terminal:.2f} (expected ${expected_pv_terminal:.2f})")
    print(f"  PV Operating: ${V.pv_oper_assets:.2f} (expected ${expected_pv_oper:.2f})")


def test_zero_growth_perpetuity():
    """
    Test zero-growth case (perpetuity).

    With zero growth:
    - No reinvestment needed
    - FCFF = NOPAT = EBIT * (1-tax)
    - Value = FCFF / WACC (perpetuity formula)

    Example:
    - Revenue: $100 (constant)
    - Margin: 20%
    - Tax: 25%
    - WACC: 10%

    EBIT = 100 * 0.20 = 20
    NOPAT = 20 * 0.75 = 15
    Reinvestment = 0
    FCFF = 15

    Value = 15 / 0.10 = 150
    """
    inputs = InputsI(
        company="ZeroGrowth",
        ticker="ZG",
        shares_out=100.0,
        tax_rate=0.25,
        revenue_t0=100.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.0] * 5,
            oper_margin=[0.20] * 5,
            stable_growth=0.0,
            stable_margin=0.20,
        ),
        sales_to_capital=[2.0] * 5,
        wacc=[0.10] * 5,
    )

    s = series(inputs)

    # All revenues should be 100
    assert all(abs(r - 100.0) < 0.01 for r in s.revenue), "Zero growth: revenues should be constant"

    # All FCFF should be 15 (no reinvestment)
    expected_fcff = 15.0
    for i, fcff in enumerate(s.fcff):
        assert abs(fcff - expected_fcff) < 0.01, f"Year {i+1} FCFF: {fcff:.2f} != {expected_fcff:.2f}"

    print(f"✓ Zero Growth Test: Constant FCFF = ${expected_fcff:.2f}")


def test_negative_net_debt():
    """Test that negative net debt (net cash) increases equity value."""
    base = InputsI(
        company="Test",
        ticker="TST",
        shares_out=100.0,
        tax_rate=0.25,
        revenue_t0=100.0,
        net_debt=10.0,  # $10 debt
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.05] * 3,
            oper_margin=[0.20] * 3,
            stable_growth=0.02,
            stable_margin=0.20,
        ),
        sales_to_capital=[2.0] * 3,
        wacc=[0.10] * 3,
    )

    with_debt = value(base)

    # Now with net cash
    with_cash = base.model_copy(deep=True)
    with_cash.net_debt = -10.0  # $10 net cash

    with_cash_val = value(with_cash)

    # Equity value should increase by exactly $20 (debt to cash swing)
    diff = with_cash_val.equity_value - with_debt.equity_value
    assert abs(diff - 20.0) < 0.01, f"Net debt swing should be $20, got ${diff:.2f}"

    print(f"✓ Net Debt Test: Debt→Cash swing correctly adds ${diff:.2f}")


# ============================================================================
# PART 3: EDGE CASES & FORMULA VERIFICATION
# ============================================================================

def test_discount_factor_formula():
    """Verify discount factor calculation matches formula: 1/prod(1+r)."""
    inputs = base_inputs(T=5, mode="end")
    s = series(inputs)

    # Manual calculation
    wacc = s.wacc
    expected_df = np.zeros(5)
    for t in range(5):
        expected_df[t] = 1.0 / np.prod(1.0 + wacc[:t+1])

    np.testing.assert_allclose(s.discount_factors, expected_df, rtol=1e-10,
                               err_msg="Discount factor formula mismatch")

    print(f"✓ Discount Factor Formula: Verified against 1/prod(1+r)")


def test_midyear_discount_adjustment():
    """Verify midyear adjustment: df_mid = df_end * sqrt(1+r)."""
    inputs_end = base_inputs(T=5, mode="end")
    inputs_mid = base_inputs(T=5, mode="midyear")

    s_end = series(inputs_end)
    s_mid = series(inputs_mid)

    # Midyear should be: df_end * sqrt(1 + wacc)
    expected_mid = s_end.discount_factors * np.sqrt(1.0 + s_end.wacc)

    np.testing.assert_allclose(s_mid.discount_factors, expected_mid, rtol=1e-10,
                               err_msg="Midyear discount adjustment mismatch")

    print(f"✓ Midyear Adjustment: Verified df_mid = df_end * sqrt(1+r)")


def test_high_growth_high_reinvestment():
    """Test case with high growth requiring high reinvestment."""
    inputs = InputsI(
        company="HighGrowth",
        ticker="HG",
        shares_out=100.0,
        tax_rate=0.25,
        revenue_t0=100.0,
        net_debt=0.0,
        cash_nonop=0.0,
        drivers=Drivers(
            sales_growth=[0.50, 0.40, 0.30],  # High growth
            oper_margin=[0.20, 0.20, 0.20],
            stable_growth=0.02,
            stable_margin=0.20,
        ),
        sales_to_capital=[1.5] * 3,  # Low capital efficiency
        wacc=[0.15] * 3,  # High WACC
    )

    s = series(inputs)

    # High growth should lead to high reinvestment
    # Year 1: Delta revenue = 50, reinvestment = 50/1.5 = 33.33
    # EBIT = 150 * 0.20 = 30, NOPAT = 22.5
    # FCFF = 22.5 - 33.33 = -10.83 (negative!)

    assert s.fcff[0] < 0, "Year 1 FCFF should be negative due to high reinvestment"

    print(f"✓ High Growth Test: Correctly handles negative FCFF = ${s.fcff[0]:.2f}")


# ============================================================================
# SUMMARY RUNNER
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("COMPREHENSIVE VALUATION KERNEL VERIFICATION")
    print("=" * 70)

    print("\n[PART 1: Legacy Mathematical Property Tests]")
    test_pv_bridge_exact()
    test_midyear_uplift_band()
    test_gradient_signs()
    test_terminal_constraint_raises()

    print("\n[PART 2: Hand-Calculated Reference Values]")
    test_hand_calculated_simple_case()
    test_zero_growth_perpetuity()
    test_negative_net_debt()

    print("\n[PART 3: Formula & Edge Case Verification]")
    test_discount_factor_formula()
    test_midyear_discount_adjustment()
    test_high_growth_high_reinvestment()

    print("\n" + "=" * 70)
    print("✅ ALL COMPREHENSIVE TESTS PASSED!")
    print("=" * 70)
    print("\nMathematical correctness verified through:")
    print("  ✓ Legacy property tests (PV bridge, gradients, constraints)")
    print("  ✓ Hand-calculated reference values (step-by-step)")
    print("  ✓ Formula verification (discount factors, adjustments)")
    print("  ✓ Edge cases (zero growth, negative debt, high reinvestment)")
