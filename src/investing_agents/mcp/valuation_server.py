"""MCP server for valuation kernel.

Exposes ginzu.py DCF calculations as MCP tools for Claude Agent SDK.
"""

from typing import Any, Dict, List
from claude_agent_sdk import tool, create_sdk_mcp_server

from investing_agents.schemas.inputs import InputsI, Drivers
from investing_agents.valuation.ginzu import value, series


# Core handler functions (testable without MCP decorators)


async def calculate_dcf_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate DCF valuation using ginzu kernel.

    Args:
        args: Dictionary containing all valuation inputs

    Returns:
        Dictionary with valuation results
    """
    try:
        # Build InputsI from args
        inputs = InputsI(
            company=args["company"],
            ticker=args["ticker"],
            shares_out=args["shares_out"],
            tax_rate=args["tax_rate"],
            revenue_t0=args["revenue_t0"],
            net_debt=args["net_debt"],
            cash_nonop=args["cash_nonop"],
            drivers=Drivers(
                sales_growth=args["sales_growth"],
                oper_margin=args["oper_margin"],
                stable_growth=args["stable_growth"],
                stable_margin=args["stable_margin"],
            ),
            sales_to_capital=args["sales_to_capital"],
            wacc=args["wacc"],
        )

        # Run valuation
        result = value(inputs)

        # Format output
        output = {
            "equity_value": round(result.equity_value, 2),
            "value_per_share": round(result.value_per_share, 2),
            "pv_explicit": round(result.pv_explicit, 2),
            "pv_terminal": round(result.pv_terminal, 2),
            "pv_oper_assets": round(result.pv_oper_assets, 2),
            "shares_out": result.shares_out,
            "net_debt": result.net_debt,
            "cash_nonop": result.cash_nonop,
        }

        # Format as text response
        response_text = f"""
DCF Valuation Results for {args['company']} ({args['ticker']}):

Operating Assets:
  PV Explicit Period: ${output['pv_explicit']:,.2f}
  PV Terminal Value:  ${output['pv_terminal']:,.2f}
  Total PV Operating: ${output['pv_oper_assets']:,.2f}

Equity Bridge:
  PV Operating Assets: ${output['pv_oper_assets']:,.2f}
  Less: Net Debt:      ${output['net_debt']:,.2f}
  Plus: Cash (non-op): ${output['cash_nonop']:,.2f}
  Equity Value:        ${output['equity_value']:,.2f}

Per Share:
  Shares Outstanding:  {output['shares_out']:,.0f}
  Value per Share:     ${output['value_per_share']:.2f}
"""

        return {
            "content": [
                {"type": "text", "text": response_text.strip()}
            ],
            "isError": False,
            "_meta": output,  # Include raw data for programmatic access
        }

    except Exception as e:
        return {
            "content": [
                {"type": "text", "text": f"Error calculating DCF: {str(e)}"}
            ],
            "isError": True,
        }


async def get_series_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get detailed year-by-year projections.

    Args:
        args: Dictionary containing all valuation inputs

    Returns:
        Dictionary with time series data
    """
    try:
        # Build InputsI from args
        inputs = InputsI(
            company=args["company"],
            ticker=args["ticker"],
            shares_out=args["shares_out"],
            tax_rate=args["tax_rate"],
            revenue_t0=args["revenue_t0"],
            net_debt=args["net_debt"],
            cash_nonop=args["cash_nonop"],
            drivers=Drivers(
                sales_growth=args["sales_growth"],
                oper_margin=args["oper_margin"],
                stable_growth=args["stable_growth"],
                stable_margin=args["stable_margin"],
            ),
            sales_to_capital=args["sales_to_capital"],
            wacc=args["wacc"],
        )

        # Get series
        s = series(inputs)

        # Calculate derived values
        import numpy as np
        pv = s.fcff * s.discount_factors  # Present value of each year's FCFF
        pv_terminal = s.terminal_value_T * s.discount_factors[-1]
        pv_oper_assets = float(pv.sum()) + pv_terminal

        # Format output as table
        T = len(s.revenue)
        lines = [
            f"Projection Series for {args['company']} ({args['ticker']}):",
            "",
            "Year | Revenue | EBIT | FCFF | DF | PV",
            "-" * 55,
        ]

        for t in range(T):
            lines.append(
                f"{t+1:4d} | ${s.revenue[t]:7.2f} | ${s.ebit[t]:6.2f} | "
                f"${s.fcff[t]:6.2f} | {s.discount_factors[t]:.4f} | ${pv[t]:6.2f}"
            )

        lines.extend([
            "",
            f"Terminal Value at T={T}: ${s.terminal_value_T:,.2f}",
            f"PV Terminal: ${pv_terminal:,.2f}",
            f"Total PV Operating: ${pv_oper_assets:,.2f}",
        ])

        response_text = "\n".join(lines)

        # Prepare structured data
        series_data = {
            "revenue": [round(x, 2) for x in s.revenue.tolist()],
            "ebit": [round(x, 2) for x in s.ebit.tolist()],
            "fcff": [round(x, 2) for x in s.fcff.tolist()],
            "discount_factors": [round(x, 4) for x in s.discount_factors.tolist()],
            "pv": [round(x, 2) for x in pv.tolist()],
            "terminal_value_T": round(s.terminal_value_T, 2),
            "pv_terminal": round(pv_terminal, 2),
            "pv_oper_assets": round(pv_oper_assets, 2),
        }

        return {
            "content": [
                {"type": "text", "text": response_text}
            ],
            "isError": False,
            "_meta": series_data,
        }

    except Exception as e:
        return {
            "content": [
                {"type": "text", "text": f"Error getting series: {str(e)}"}
            ],
            "isError": True,
        }


async def sensitivity_analysis_handler(args: Dict[str, Any]) -> Dict[str, Any]:
    """Run sensitivity analysis by varying key drivers.

    Args:
        args: Dictionary containing base case inputs and sensitivity parameters

    Returns:
        Dictionary with sensitivity results
    """
    try:
        # Base case inputs
        base_inputs = InputsI(
            company=args["company"],
            ticker=args["ticker"],
            shares_out=args["shares_out"],
            tax_rate=args["tax_rate"],
            revenue_t0=args["revenue_t0"],
            net_debt=args["net_debt"],
            cash_nonop=args["cash_nonop"],
            drivers=Drivers(
                sales_growth=args["sales_growth"],
                oper_margin=args["oper_margin"],
                stable_growth=args["stable_growth"],
                stable_margin=args["stable_margin"],
            ),
            sales_to_capital=args["sales_to_capital"],
            wacc=args["wacc"],
        )

        # Get base case value
        base_result = value(base_inputs)
        base_vps = base_result.value_per_share

        # Run sensitivity scenarios
        sensitivity_vars = args["sensitivity_vars"]
        sensitivity_ranges = args["sensitivity_ranges"]

        results = []
        for var, values in zip(sensitivity_vars, sensitivity_ranges):
            var_results = {"variable": var, "base_value": base_vps, "scenarios": []}

            for val in values:
                # Create modified inputs
                modified_inputs = base_inputs.model_copy(deep=True)

                # Update the specific variable
                if var == "stable_growth":
                    modified_inputs.drivers.stable_growth = val
                elif var == "stable_margin":
                    modified_inputs.drivers.stable_margin = val
                elif var == "wacc":
                    # Update all WACC values
                    modified_inputs.wacc = [val] * len(modified_inputs.wacc)
                else:
                    raise ValueError(f"Unsupported sensitivity variable: {var}")

                # Calculate value with modified input
                result = value(modified_inputs)
                vps = result.value_per_share
                change_pct = ((vps - base_vps) / base_vps) * 100

                var_results["scenarios"].append({
                    "value": val,
                    "vps": round(vps, 2),
                    "change_pct": round(change_pct, 2),
                })

            results.append(var_results)

        # Format output
        lines = [
            f"Sensitivity Analysis for {args['company']} ({args['ticker']}):",
            f"Base Case Value per Share: ${base_vps:.2f}",
            "",
        ]

        for var_result in results:
            lines.append(f"Sensitivity to {var_result['variable']}:")
            lines.append("-" * 50)
            for scenario in var_result["scenarios"]:
                lines.append(
                    f"  {var_result['variable']} = {scenario['value']:.3f}: "
                    f"${scenario['vps']:.2f} ({scenario['change_pct']:+.1f}%)"
                )
            lines.append("")

        response_text = "\n".join(lines)

        return {
            "content": [
                {"type": "text", "text": response_text}
            ],
            "isError": False,
            "_meta": {"base_vps": round(base_vps, 2), "results": results},
        }

    except Exception as e:
        return {
            "content": [
                {"type": "text", "text": f"Error in sensitivity analysis: {str(e)}"}
            ],
            "isError": True,
        }


# MCP Tool Wrappers (decorated versions that call handlers)


@tool(
    "calculate_dcf",
    "Calculate DCF valuation for a company",
    {
        "company": str,
        "ticker": str,
        "shares_out": float,
        "tax_rate": float,
        "revenue_t0": float,
        "net_debt": float,
        "cash_nonop": float,
        "sales_growth": List[float],
        "oper_margin": List[float],
        "stable_growth": float,
        "stable_margin": float,
        "sales_to_capital": List[float],
        "wacc": List[float],
    },
)
async def calculate_dcf_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """MCP tool wrapper for calculate_dcf."""
    return await calculate_dcf_handler(args)


@tool(
    "get_series",
    "Get year-by-year projection series (revenue, EBIT, FCFF, etc.)",
    {
        "company": str,
        "ticker": str,
        "shares_out": float,
        "tax_rate": float,
        "revenue_t0": float,
        "net_debt": float,
        "cash_nonop": float,
        "sales_growth": List[float],
        "oper_margin": List[float],
        "stable_growth": float,
        "stable_margin": float,
        "sales_to_capital": List[float],
        "wacc": List[float],
    },
)
async def get_series_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """MCP tool wrapper for get_series."""
    return await get_series_handler(args)


@tool(
    "sensitivity_analysis",
    "Run sensitivity analysis on key valuation drivers",
    {
        "company": str,
        "ticker": str,
        "shares_out": float,
        "tax_rate": float,
        "revenue_t0": float,
        "net_debt": float,
        "cash_nonop": float,
        "sales_growth": List[float],
        "oper_margin": List[float],
        "stable_growth": float,
        "stable_margin": float,
        "sales_to_capital": List[float],
        "wacc": List[float],
        "sensitivity_vars": List[str],  # e.g., ["stable_growth", "wacc"]
        "sensitivity_ranges": List[List[float]],  # e.g., [[0.01, 0.02, 0.03], [0.08, 0.10, 0.12]]
    },
)
async def sensitivity_analysis_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """MCP tool wrapper for sensitivity_analysis."""
    return await sensitivity_analysis_handler(args)


# Create the MCP server
valuation_server = create_sdk_mcp_server(
    name="valuation",
    version="1.0.0",
    tools=[calculate_dcf_tool, get_series_tool, sensitivity_analysis_tool],
)


# Convenience function to get server
def get_valuation_server():
    """Get the valuation MCP server instance."""
    return valuation_server
