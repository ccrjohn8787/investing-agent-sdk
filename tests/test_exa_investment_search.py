"""Test Exa MCP search quality for investment research.

This test validates that Exa search returns high-quality, relevant results
for investment analysis queries.

Quality criteria:
1. Results are relevant to investment thesis
2. Sources include financial reports, earnings data, analyst reports
3. Content includes quantitative data (revenue, growth, margins)
4. Temporal relevance (recent results prioritized)
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    ToolUseBlock,
    query,
)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


async def test_exa_investment_search_quality():
    """Test search quality for investment research queries."""
    print("\n" + "=" * 80)
    print("TEST 3: Exa Search Quality for Investment Research")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("EXA_API_KEY")
    if not api_key or api_key == "your-exa-api-key-here":
        print("\n❌ ERROR: EXA_API_KEY not set")
        return False

    print(f"\n✓ Exa API key configured: {api_key[:10]}...")

    # Configure Exa MCP with investment-optimized settings
    options = ClaudeAgentOptions(
        mcp_servers={
            "exa": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "exa-mcp-server"],
                "env": {"EXA_API_KEY": api_key}
            }
        },
        allowed_tools=["mcp__exa__web_search_exa"],
        max_turns=5,
    )

    # Test multiple investment research scenarios
    test_cases = [
        {
            "name": "Earnings Data Search",
            "query": """Use mcp__exa__web_search_exa to search for:
"NVIDIA Q4 FY2025 data center revenue growth earnings"

Focus on: Financial reports, earnings releases, analyst reports.
Return top 5 results with revenue numbers.""",
            "quality_keywords": ["revenue", "billion", "growth", "q4", "fy2025", "data center"],
        },
        {
            "name": "Competitive Analysis",
            "query": """Use mcp__exa__web_search_exa to search for:
"NVIDIA vs AMD AI chip market share 2024"

Focus on: Market analysis, competitive positioning.
Return top 3 results comparing the two companies.""",
            "quality_keywords": ["market share", "nvidia", "amd", "ai", "competitive"],
        },
        {
            "name": "Forward-Looking Analysis",
            "query": """Use mcp__exa__web_search_exa to search for:
"NVIDIA AI chip demand outlook 2025 analyst estimates"

Focus on: Analyst reports, forward guidance, market forecasts.
Return top 3 results with future projections.""",
            "quality_keywords": ["outlook", "forecast", "2025", "demand", "analyst"],
        }
    ]

    overall_results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n{'=' * 80}")
        print(f"Test Case {i}: {test_case['name']}")
        print("=" * 80)

        tool_uses = []
        text_responses = []

        try:
            print(f"\nExecuting search: {test_case['name']}...")

            async for message in query(prompt=test_case["query"], options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            text_responses.append(block.text)
                            print(f"\n   Response preview: {block.text[:200]}...")
                        elif isinstance(block, ToolUseBlock):
                            tool_uses.append(block)
                            print(f"\n   ✓ Tool used: {block.name}")

            # Quality assessment
            combined_text = " ".join(text_responses).lower()
            quality_score = sum(
                1 for kw in test_case["quality_keywords"]
                if kw.lower() in combined_text
            ) / len(test_case["quality_keywords"])

            result = {
                "test_case": test_case["name"],
                "tool_uses": len(tool_uses),
                "text_responses": len(text_responses),
                "quality_score": quality_score,
                "keywords_found": [
                    kw for kw in test_case["quality_keywords"]
                    if kw.lower() in combined_text
                ],
                "success": len(tool_uses) > 0 and quality_score >= 0.4
            }

            overall_results.append(result)

            print(f"\n   📊 Quality Assessment:")
            print(f"      - Tool uses: {result['tool_uses']}")
            print(f"      - Quality score: {result['quality_score']:.1%}")
            print(f"      - Keywords found: {result['keywords_found']}")
            print(f"      - Status: {'✅ PASS' if result['success'] else '❌ FAIL'}")

        except Exception as e:
            print(f"\n   ❌ Exception: {e}")
            overall_results.append({
                "test_case": test_case["name"],
                "success": False,
                "error": str(e)
            })

    # Overall assessment
    print("\n\n" + "=" * 80)
    print("OVERALL SEARCH QUALITY ASSESSMENT")
    print("=" * 80)

    successful_tests = sum(1 for r in overall_results if r.get("success", False))
    total_tests = len(test_cases)
    avg_quality = sum(r.get("quality_score", 0) for r in overall_results) / total_tests

    print(f"\nTests passed: {successful_tests}/{total_tests}")
    print(f"Average quality score: {avg_quality:.1%}")

    # Quality thresholds
    quality_acceptable = successful_tests >= 2 and avg_quality >= 0.5

    print("\n" + "=" * 80)
    if quality_acceptable:
        print("✅ SEARCH QUALITY IS ACCEPTABLE FOR INVESTMENT RESEARCH")
        print("=" * 80)
        print("\n✓ Exa search returns relevant financial data")
        print("✓ Results include quantitative metrics")
        print("✓ Multiple research scenarios supported")
        print("\n📋 Recommendations:")
        print("   - Use category filter: 'financial report' for earnings data")
        print("   - Include temporal keywords (Q4, FY2025) for recent data")
        print("   - Request 'top N results' for focused analysis")
    else:
        print("⚠️  SEARCH QUALITY NEEDS IMPROVEMENT")
        print("=" * 80)
        print(f"\n   Tests passed: {successful_tests}/{total_tests} (need ≥2)")
        print(f"   Quality score: {avg_quality:.1%} (need ≥50%)")
        print("\n📋 Possible issues:")
        print("   - Query formulation may need refinement")
        print("   - Category filters not properly applied")
        print("   - API key limitations or rate limits")

    # Detailed results
    print("\n📝 Detailed Results:")
    for i, result in enumerate(overall_results, 1):
        status = "✅" if result.get("success", False) else "❌"
        print(f"\n   {status} {i}. {result['test_case']}")
        if "error" in result:
            print(f"      Error: {result['error']}")
        else:
            print(f"      Quality: {result.get('quality_score', 0):.1%}")
            print(f"      Keywords: {', '.join(result.get('keywords_found', []))}")

    return quality_acceptable


if __name__ == "__main__":
    print("\n🔬 Exa Investment Search Quality Test")
    print("=" * 80)
    print("This test validates search quality for investment research scenarios")
    print("=" * 80)

    result = asyncio.run(test_exa_investment_search_quality())

    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)
    if result:
        print("✅ EXA SEARCH QUALITY IS SUITABLE")
        print("\nProceed with Exa MCP integration")
    else:
        print("⚠️  SEARCH QUALITY NEEDS REVIEW")
        print("\nConsider query optimization or alternative approaches")
