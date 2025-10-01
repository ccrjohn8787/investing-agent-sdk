"""Test valuation kernel (ginzu.py) extraction."""

from investing_agents.schemas.inputs import InputsI, Drivers, Macro, Discounting
from investing_agents.valuation.ginzu import value, series


def test_basic_dcf():
    """Test basic DCF valuation calculation."""
    # Create a simple test case
    inputs = InputsI(
        company="Test Company",
        ticker="TEST",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=100.0,
        net_debt=10.0,
        cash_nonop=5.0,
        drivers=Drivers(
            sales_growth=[0.10, 0.08, 0.06, 0.04, 0.03],
            oper_margin=[0.20, 0.21, 0.22, 0.23, 0.24],
            stable_growth=0.02,
            stable_margin=0.25,
        ),
        sales_to_capital=[2.0, 2.0, 2.0, 2.0, 2.0],
        wacc=[0.10, 0.10, 0.10, 0.10, 0.10],
    )

    # Run valuation
    result = value(inputs)

    # Basic assertions
    assert result.equity_value > 0, "Equity value should be positive"
    assert result.value_per_share > 0, "Value per share should be positive"
    assert result.pv_explicit > 0, "PV explicit should be positive"
    assert result.pv_terminal > 0, "PV terminal should be positive"
    assert result.shares_out == 1000.0, "Shares outstanding should match input"

    print(f"✓ DCF Valuation Test Passed")
    print(f"  Equity Value: ${result.equity_value:.2f}")
    print(f"  Value per Share: ${result.value_per_share:.2f}")
    print(f"  PV Explicit: ${result.pv_explicit:.2f}")
    print(f"  PV Terminal: ${result.pv_terminal:.2f}")


def test_series_output():
    """Test series output for reporting."""
    inputs = InputsI(
        company="Test Company",
        ticker="TEST",
        shares_out=1000.0,
        tax_rate=0.25,
        revenue_t0=100.0,
        net_debt=10.0,
        cash_nonop=5.0,
        drivers=Drivers(
            sales_growth=[0.10, 0.08, 0.06],
            oper_margin=[0.20, 0.21, 0.22],
            stable_growth=0.02,
            stable_margin=0.25,
        ),
        sales_to_capital=[2.0, 2.0, 2.0],
        wacc=[0.10, 0.10, 0.10],
    )

    # Get series
    s = series(inputs)

    # Assertions
    assert len(s.revenue) == 3, "Should have 3 years of revenue"
    assert len(s.ebit) == 3, "Should have 3 years of EBIT"
    assert len(s.fcff) == 3, "Should have 3 years of FCFF"
    assert s.terminal_value_T > 0, "Terminal value should be positive"

    print(f"✓ Series Output Test Passed")
    print(f"  Revenue Years 1-3: {[f'${r:.2f}' for r in s.revenue]}")
    print(f"  FCFF Years 1-3: {[f'${f:.2f}' for f in s.fcff]}")
    print(f"  Terminal Value: ${s.terminal_value_T:.2f}")


if __name__ == "__main__":
    test_basic_dcf()
    test_series_output()
    print("\n✅ All valuation tests passed!")
