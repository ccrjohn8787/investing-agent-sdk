"""Demo: Using the valuation MCP server with Claude Agent SDK.

This example shows how to use the valuation MCP server to provide
Claude with DCF valuation tools.
"""

import asyncio
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from investing_agents.mcp import get_valuation_server


async def demo_basic_valuation():
    """Demo: Basic DCF valuation through Claude."""

    # Get the valuation MCP server
    valuation_server = get_valuation_server()

    # Configure Claude with the valuation server
    options = ClaudeAgentOptions(
        mcp_servers={
            "valuation": valuation_server
        },
        allowed_tools=[
            "mcp__valuation__calculate_dcf",
            "mcp__valuation__get_series",
            "mcp__valuation__sensitivity_analysis",
        ],
        max_turns=5,
    )

    # Example query that would use the valuation tools
    query = """
    I need you to value a company with these characteristics:

    - Company: TechCorp
    - Ticker: TECH
    - Current revenue: $100M
    - Shares outstanding: 1000M
    - Net debt: $10M
    - Non-operating cash: $5M
    - Tax rate: 25%

    Growth assumptions:
    - Years 1-3: 10%, 8%, 6%
    - Stable growth: 2%

    Margin assumptions:
    - Years 1-3: 20%, 21%, 22%
    - Stable margin: 25%

    Other inputs:
    - Sales-to-capital ratio: 2.0 (all years)
    - WACC: 10% (all years)

    Please:
    1. Calculate the DCF valuation
    2. Show me the year-by-year projections
    3. Run sensitivity analysis on stable growth (1%, 2%, 3%) and WACC (8%, 10%, 12%)
    """

    async with ClaudeSDKClient(options=options) as client:
        # Send the query
        await client.query(query)

        # Receive and print responses
        print("\n" + "=" * 70)
        print("CLAUDE RESPONSE")
        print("=" * 70 + "\n")

        async for message in client.receive_response():
            print(message)

        print("\n" + "=" * 70)
        print("DEMO COMPLETE")
        print("=" * 70 + "\n")


async def demo_direct_tool_call():
    """Demo: Direct tool call without Claude (for testing)."""
    from investing_agents.mcp import calculate_dcf_handler

    print("\n" + "=" * 70)
    print("DIRECT TOOL CALL DEMO")
    print("=" * 70 + "\n")

    args = {
        "company": "TechCorp",
        "ticker": "TECH",
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

    if result.get("isError"):
        print("ERROR:", result["content"][0]["text"])
    else:
        print(result["content"][0]["text"])
        print("\nMetadata:", result["_meta"])

    print("\n" + "=" * 70)
    print("DIRECT CALL COMPLETE")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                 VALUATION MCP SERVER DEMO                            ║
║                                                                      ║
║  This demo shows how to integrate the valuation kernel with         ║
║  Claude Agent SDK using MCP (Model Context Protocol).               ║
╚══════════════════════════════════════════════════════════════════════╝
    """)

    # Run direct tool call demo (works without API key)
    asyncio.run(demo_direct_tool_call())

    # Uncomment to run full Claude integration (requires ANTHROPIC_API_KEY)
    # asyncio.run(demo_basic_valuation())
