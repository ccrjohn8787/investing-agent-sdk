"""Test MCP valuation server."""

import pytest
from investing_agents.mcp.valuation_server import (
    calculate_dcf_handler,
    get_series_handler,
    sensitivity_analysis_handler,
)


@pytest.mark.asyncio
async def test_calculate_dcf_tool():
    """Test calculate_dcf tool."""
    args = {
        "company": "Test Company",
        "ticker": "TEST",
        "shares_out": 1000.0,
        "tax_rate": 0.25,
        "revenue_t0": 100.0,
        "net_debt": 10.0,
        "cash_nonop": 5.0,
        "sales_growth": [0.10, 0.08, 0.06],
        "oper_margin": [0.20, 0.21, 0.22],
        "stable_growth": 0.02,
        "stable_margin": 0.25,
        "sales_to_capital": [2.0, 2.0, 2.0],
        "wacc": [0.10, 0.10, 0.10],
    }

    result = await calculate_dcf_handler(args)

    # Check structure
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    assert not result.get("isError", False)

    # Check metadata
    assert "_meta" in result
    meta = result["_meta"]
    assert "equity_value" in meta
    assert "value_per_share" in meta
    assert "pv_explicit" in meta
    assert "pv_terminal" in meta

    # Check values are positive
    assert meta["equity_value"] > 0
    assert meta["value_per_share"] > 0
    assert meta["pv_explicit"] > 0
    assert meta["pv_terminal"] > 0

    print("✓ calculate_dcf tool test passed")
    print(f"  Equity Value: ${meta['equity_value']:.2f}")
    print(f"  Value per Share: ${meta['value_per_share']:.2f}")


@pytest.mark.asyncio
async def test_get_series_tool():
    """Test get_series tool."""
    args = {
        "company": "Test Company",
        "ticker": "TEST",
        "shares_out": 1000.0,
        "tax_rate": 0.25,
        "revenue_t0": 100.0,
        "net_debt": 10.0,
        "cash_nonop": 5.0,
        "sales_growth": [0.10, 0.08, 0.06],
        "oper_margin": [0.20, 0.21, 0.22],
        "stable_growth": 0.02,
        "stable_margin": 0.25,
        "sales_to_capital": [2.0, 2.0, 2.0],
        "wacc": [0.10, 0.10, 0.10],
    }

    result = await get_series_handler(args)

    # Check structure
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    assert not result.get("isError", False)

    # Check metadata
    assert "_meta" in result
    meta = result["_meta"]
    assert "revenue" in meta
    assert "ebit" in meta
    assert "fcff" in meta
    assert "pv" in meta
    assert "terminal_value_T" in meta
    assert "pv_terminal" in meta
    assert "pv_oper_assets" in meta

    # Check arrays have correct length
    assert len(meta["revenue"]) == 3
    assert len(meta["ebit"]) == 3
    assert len(meta["fcff"]) == 3
    assert len(meta["pv"]) == 3

    # Check values are positive
    assert meta["terminal_value_T"] > 0
    assert meta["pv_terminal"] > 0
    assert meta["pv_oper_assets"] > 0

    print("✓ get_series tool test passed")
    print(f"  Revenues: {meta['revenue']}")
    print(f"  FCFFs: {meta['fcff']}")
    print(f"  PV Operating: ${meta['pv_oper_assets']:.2f}")


@pytest.mark.asyncio
async def test_sensitivity_analysis_tool():
    """Test sensitivity_analysis tool."""
    args = {
        "company": "Test Company",
        "ticker": "TEST",
        "shares_out": 1000.0,
        "tax_rate": 0.25,
        "revenue_t0": 100.0,
        "net_debt": 10.0,
        "cash_nonop": 5.0,
        "sales_growth": [0.10, 0.08, 0.06],
        "oper_margin": [0.20, 0.21, 0.22],
        "stable_growth": 0.02,
        "stable_margin": 0.25,
        "sales_to_capital": [2.0, 2.0, 2.0],
        "wacc": [0.10, 0.10, 0.10],
        "sensitivity_vars": ["stable_growth", "wacc"],
        "sensitivity_ranges": [[0.01, 0.02, 0.03], [0.08, 0.10, 0.12]],
    }

    result = await sensitivity_analysis_handler(args)

    # Check structure
    assert "content" in result
    assert len(result["content"]) > 0
    assert result["content"][0]["type"] == "text"
    assert not result.get("isError", False)

    # Check metadata
    assert "_meta" in result
    meta = result["_meta"]
    assert "base_vps" in meta
    assert "results" in meta

    # Check we have results for both variables
    assert len(meta["results"]) == 2

    # Check first variable (stable_growth)
    sg_results = meta["results"][0]
    assert sg_results["variable"] == "stable_growth"
    assert len(sg_results["scenarios"]) == 3

    # Check second variable (wacc)
    wacc_results = meta["results"][1]
    assert wacc_results["variable"] == "wacc"
    assert len(wacc_results["scenarios"]) == 3

    # Check economic sensibility:
    # Higher growth should increase value
    sg_vps = [s["vps"] for s in sg_results["scenarios"]]
    assert sg_vps[2] > sg_vps[0], "Higher growth should increase value"

    # Higher WACC should decrease value
    wacc_vps = [s["vps"] for s in wacc_results["scenarios"]]
    assert wacc_vps[0] > wacc_vps[2], "Higher WACC should decrease value"

    print("✓ sensitivity_analysis tool test passed")
    print(f"  Base VPS: ${meta['base_vps']:.2f}")
    print(f"  Growth sensitivity: {[s['vps'] for s in sg_results['scenarios']]}")
    print(f"  WACC sensitivity: {[s['vps'] for s in wacc_results['scenarios']]}")


@pytest.mark.asyncio
async def test_error_handling():
    """Test error handling with invalid inputs."""
    # Invalid input: missing required field
    args = {
        "company": "Test Company",
        "ticker": "TEST",
        # Missing shares_out and other required fields
    }

    result = await calculate_dcf_handler(args)

    # Should return error
    assert result.get("isError", False) == True
    assert "content" in result
    assert "Error" in result["content"][0]["text"]

    print("✓ Error handling test passed")


if __name__ == "__main__":
    import asyncio

    async def run_tests():
        print("\n" + "=" * 70)
        print("MCP VALUATION SERVER TESTS")
        print("=" * 70 + "\n")

        await test_calculate_dcf_tool()
        print()
        await test_get_series_tool()
        print()
        await test_sensitivity_analysis_tool()
        print()
        await test_error_handling()

        print("\n" + "=" * 70)
        print("✅ ALL MCP SERVER TESTS PASSED!")
        print("=" * 70 + "\n")

    asyncio.run(run_tests())
