"""Brave Search vs Exa AI - Head-to-head comparison for investment research.

This test evaluates both search engines on identical queries to determine:
1. Which provides better quality results for investment research?
2. Is Exa's "LLM-first search" worth the cost vs Brave's free tier?
3. Which is better for hypothesis validation in our use case?

Evaluation criteria:
- Relevance: Do results match investment research intent?
- Quality: Financial reports, analyst reports, quantitative data
- Recency: Are results up-to-date?
- Depth: Do results provide actionable insights?
- Cost-effectiveness: Quality per dollar spent
"""

import asyncio
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from dotenv import load_dotenv
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    TextBlock,
    ToolUseBlock,
    query,
)

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)


# Test queries covering different investment research scenarios
TEST_QUERIES = [
    {
        "name": "Quantitative Earnings Data",
        "search_query": "NVIDIA Q3 2024 data center revenue growth rate",
        "evaluation_keywords": ["revenue", "billion", "growth", "data center", "q3", "2024"],
        "weight": 30,  # Critical for DCF valuation
        "ideal_sources": ["investor.nvidia.com", "sec.gov", "earnings transcript"],
    },
    {
        "name": "Competitive Dynamics",
        "search_query": "NVIDIA vs AMD AI accelerator market share competition 2024",
        "evaluation_keywords": ["market share", "nvidia", "amd", "ai", "accelerator", "competitive"],
        "weight": 25,
        "ideal_sources": ["analyst report", "gartner", "idc", "market research"],
    },
    {
        "name": "Forward-Looking Guidance",
        "search_query": "semiconductor industry capex spending forecast 2025",
        "evaluation_keywords": ["capex", "forecast", "2025", "spending", "semiconductor"],
        "weight": 25,
        "ideal_sources": ["analyst", "gartner", "idc", "industry report"],
    },
    {
        "name": "Strategic Analysis",
        "search_query": "NVIDIA AI chip supply chain constraints TSMC",
        "evaluation_keywords": ["supply chain", "constraints", "tsmc", "manufacturing", "capacity"],
        "weight": 20,
        "ideal_sources": ["reuters", "bloomberg", "wsj", "ft.com"],
    },
]


async def run_brave_search(search_query: str) -> Dict[str, Any]:
    """Run Brave Search MCP."""
    brave_api_key = os.getenv("BRAVE_API_KEY")
    if not brave_api_key or brave_api_key == "your-brave-api-key-here":
        return {
            "success": False,
            "error": "BRAVE_API_KEY not set",
            "results": [],
        }

    options = ClaudeAgentOptions(
        mcp_servers={
            "brave": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@brave/brave-search-mcp-server"],
                "env": {"BRAVE_API_KEY": brave_api_key}
            }
        },
        allowed_tools=["mcp__brave__brave_web_search"],
        max_turns=3,
    )

    prompt = f"""Use mcp__brave__brave_web_search to search for: "{search_query}"

Return the top 5 most relevant results. For each result, note:
- Source URL
- Key information found
- Relevance to the query"""

    tool_uses = []
    text_responses = []

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_responses.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append(block)

        return {
            "success": True,
            "tool_uses": len(tool_uses),
            "text_responses": text_responses,
            "combined_text": " ".join(text_responses),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }


async def run_exa_search(search_query: str) -> Dict[str, Any]:
    """Run Exa AI search."""
    exa_api_key = os.getenv("EXA_API_KEY")
    if not exa_api_key or exa_api_key == "your-exa-api-key-here":
        return {
            "success": False,
            "error": "EXA_API_KEY not set",
            "results": [],
        }

    options = ClaudeAgentOptions(
        mcp_servers={
            "exa": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "exa-mcp-server"],
                "env": {"EXA_API_KEY": exa_api_key}
            }
        },
        allowed_tools=["mcp__exa__web_search_exa"],
        max_turns=3,
    )

    prompt = f"""Use mcp__exa__web_search_exa to search for: "{search_query}"

Return the top 5 most relevant results. For each result, note:
- Source URL
- Key information found
- Relevance to the query"""

    tool_uses = []
    text_responses = []

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_responses.append(block.text)
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append(block)

        return {
            "success": True,
            "tool_uses": len(tool_uses),
            "text_responses": text_responses,
            "combined_text": " ".join(text_responses),
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }


def evaluate_result(result: Dict[str, Any], test_case: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate search result quality."""
    if not result.get("success"):
        return {
            "keyword_score": 0,
            "source_quality_score": 0,
            "overall_score": 0,
            "error": result.get("error"),
        }

    combined_text = result.get("combined_text", "").lower()

    # Keyword relevance (0-100)
    keywords_found = [
        kw for kw in test_case["evaluation_keywords"]
        if kw.lower() in combined_text
    ]
    keyword_score = (len(keywords_found) / len(test_case["evaluation_keywords"])) * 100

    # Source quality (0-100)
    ideal_sources_found = sum(
        1 for source in test_case.get("ideal_sources", [])
        if source.lower() in combined_text
    )
    max_sources = len(test_case.get("ideal_sources", [])) or 1
    source_quality_score = min((ideal_sources_found / max_sources) * 100, 100)

    # Overall weighted score
    overall_score = (keyword_score * 0.7) + (source_quality_score * 0.3)

    return {
        "keyword_score": round(keyword_score, 1),
        "keywords_found": keywords_found,
        "source_quality_score": round(source_quality_score, 1),
        "ideal_sources_found": ideal_sources_found,
        "overall_score": round(overall_score, 1),
        "text_length": len(combined_text),
    }


async def run_comparison_test():
    """Run head-to-head comparison."""
    print("\n" + "=" * 100)
    print("BRAVE SEARCH vs EXA AI - Investment Research Quality Comparison")
    print("=" * 100)
    print(f"\nTest Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Number of test queries: {len(TEST_QUERIES)}")
    print("\nEvaluation Criteria:")
    print("  1. Keyword Relevance (70%): Do results contain expected financial terms?")
    print("  2. Source Quality (30%): Are results from authoritative sources?")
    print("\n" + "=" * 100)

    # Check API keys
    brave_available = bool(os.getenv("BRAVE_API_KEY") and os.getenv("BRAVE_API_KEY") != "your-brave-api-key-here")
    exa_available = bool(os.getenv("EXA_API_KEY") and os.getenv("EXA_API_KEY") != "your-exa-api-key-here")

    print(f"\n🔑 API Key Status:")
    print(f"   Brave Search: {'✅ Available' if brave_available else '❌ Not configured'}")
    print(f"   Exa AI:       {'✅ Available' if exa_available else '❌ Not configured'}")

    if not brave_available and not exa_available:
        print("\n❌ ERROR: No search engines configured. Set BRAVE_API_KEY or EXA_API_KEY in .env")
        return False

    results_summary = []

    for i, test_case in enumerate(TEST_QUERIES, 1):
        print(f"\n\n{'=' * 100}")
        print(f"Test Case {i}/{len(TEST_QUERIES)}: {test_case['name']}")
        print(f"Query: \"{test_case['search_query']}\"")
        print(f"Weight: {test_case['weight']}%")
        print("=" * 100)

        # Run Brave Search
        brave_result = None
        brave_eval = None
        if brave_available:
            print(f"\n🔍 Running Brave Search...")
            brave_result = await run_brave_search(test_case['search_query'])
            brave_eval = evaluate_result(brave_result, test_case)

            print(f"   ✓ Completed")
            print(f"   📊 Keyword Score: {brave_eval['keyword_score']}/100")
            print(f"   📊 Source Quality: {brave_eval['source_quality_score']}/100")
            print(f"   📊 Overall Score: {brave_eval['overall_score']}/100")
            print(f"   Keywords found: {', '.join(brave_eval['keywords_found'][:5])}")
        else:
            print(f"\n⏭️  Brave Search skipped (no API key)")

        # Run Exa Search
        exa_result = None
        exa_eval = None
        if exa_available:
            print(f"\n🔍 Running Exa AI Search...")
            exa_result = await run_exa_search(test_case['search_query'])
            exa_eval = evaluate_result(exa_result, test_case)

            print(f"   ✓ Completed")
            print(f"   📊 Keyword Score: {exa_eval['keyword_score']}/100")
            print(f"   📊 Source Quality: {exa_eval['source_quality_score']}/100")
            print(f"   📊 Overall Score: {exa_eval['overall_score']}/100")
            print(f"   Keywords found: {', '.join(exa_eval['keywords_found'][:5])}")
        else:
            print(f"\n⏭️  Exa AI skipped (no API key)")

        # Comparison
        if brave_eval and exa_eval:
            print(f"\n🏆 Winner for this query:")
            if brave_eval['overall_score'] > exa_eval['overall_score']:
                diff = brave_eval['overall_score'] - exa_eval['overall_score']
                print(f"   ✅ Brave Search (+{diff:.1f} points)")
            elif exa_eval['overall_score'] > brave_eval['overall_score']:
                diff = exa_eval['overall_score'] - brave_eval['overall_score']
                print(f"   ✅ Exa AI (+{diff:.1f} points)")
            else:
                print(f"   🤝 Tie (both scored {brave_eval['overall_score']}/100)")

        results_summary.append({
            "test_case": test_case["name"],
            "weight": test_case["weight"],
            "brave": brave_eval,
            "exa": exa_eval,
        })

    # Overall Comparison
    print("\n\n" + "=" * 100)
    print("OVERALL COMPARISON SUMMARY")
    print("=" * 100)

    brave_weighted_score = 0
    exa_weighted_score = 0
    brave_wins = 0
    exa_wins = 0
    ties = 0

    for result in results_summary:
        weight = result["weight"] / 100

        if result["brave"]:
            brave_weighted_score += result["brave"]["overall_score"] * weight

        if result["exa"]:
            exa_weighted_score += result["exa"]["overall_score"] * weight

        # Count wins
        if result["brave"] and result["exa"]:
            if result["brave"]["overall_score"] > result["exa"]["overall_score"]:
                brave_wins += 1
            elif result["exa"]["overall_score"] > result["brave"]["overall_score"]:
                exa_wins += 1
            else:
                ties += 1

    print(f"\n📊 Weighted Overall Scores:")
    if brave_available:
        print(f"   Brave Search: {brave_weighted_score:.1f}/100")
    if exa_available:
        print(f"   Exa AI:       {exa_weighted_score:.1f}/100")

    if brave_available and exa_available:
        print(f"\n🏆 Head-to-Head Record:")
        print(f"   Brave wins: {brave_wins}")
        print(f"   Exa wins:   {exa_wins}")
        print(f"   Ties:       {ties}")

        # Determine winner
        print(f"\n" + "=" * 100)
        if brave_weighted_score > exa_weighted_score:
            diff = brave_weighted_score - exa_weighted_score
            print(f"🏆 WINNER: BRAVE SEARCH")
            print(f"   Margin: +{diff:.1f} points ({diff/exa_weighted_score*100:.1f}% better)")
        elif exa_weighted_score > brave_weighted_score:
            diff = exa_weighted_score - brave_weighted_score
            print(f"🏆 WINNER: EXA AI")
            print(f"   Margin: +{diff:.1f} points ({diff/brave_weighted_score*100:.1f}% better)")
        else:
            print(f"🤝 TIE - Both scored {brave_weighted_score:.1f}/100")
        print("=" * 100)

    # Detailed Results Table
    print(f"\n📋 Detailed Results by Test Case:")
    print(f"\n{'Test Case':<30} {'Brave':<15} {'Exa':<15} {'Winner':<15}")
    print("-" * 75)

    for result in results_summary:
        name = result["test_case"][:28]
        brave_score = f"{result['brave']['overall_score']:.1f}" if result['brave'] else "N/A"
        exa_score = f"{result['exa']['overall_score']:.1f}" if result['exa'] else "N/A"

        if result['brave'] and result['exa']:
            if result['brave']['overall_score'] > result['exa']['overall_score']:
                winner = "Brave"
            elif result['exa']['overall_score'] > result['brave']['overall_score']:
                winner = "Exa"
            else:
                winner = "Tie"
        else:
            winner = "-"

        print(f"{name:<30} {brave_score:<15} {exa_score:<15} {winner:<15}")

    # Cost Analysis
    print(f"\n\n" + "=" * 100)
    print("COST-EFFECTIVENESS ANALYSIS")
    print("=" * 100)

    print(f"\nBrave Search:")
    print(f"   • Free tier: 2,000 queries/month (~67/day)")
    print(f"   • Pro tier: $5/month for 20,000 queries")
    print(f"   • Cost per query (Pro): $0.00025")

    print(f"\nExa AI:")
    print(f"   • Free credits: $10 to start")
    print(f"   • Pricing: Pay-as-you-go (exact cost TBD)")
    print(f"   • Estimated: ~$0.001-0.005 per search")

    if brave_available and exa_available:
        print(f"\n💡 Cost-Effectiveness:")
        quality_diff = exa_weighted_score - brave_weighted_score

        if quality_diff > 10:
            print(f"   ✅ Exa provides significantly better quality (+{quality_diff:.1f} points)")
            print(f"   ✅ May be worth the cost for hypothesis validation")
        elif quality_diff > 0:
            print(f"   ⚠️  Exa provides marginally better quality (+{quality_diff:.1f} points)")
            print(f"   ⚠️  Evaluate if quality gain justifies cost difference")
        else:
            print(f"   ❌ Brave provides equal or better quality")
            print(f"   ❌ Stick with Brave's free tier")

    # Recommendation
    print(f"\n\n" + "=" * 100)
    print("RECOMMENDATION FOR INVESTING AGENT")
    print("=" * 100)

    if brave_available and exa_available:
        if exa_weighted_score > brave_weighted_score + 10:
            print(f"\n✅ RECOMMEND: Adopt Exa AI for Phase 1")
            print(f"\n   Reasons:")
            print(f"   1. Significantly better quality ({exa_weighted_score:.1f} vs {brave_weighted_score:.1f})")
            print(f"   2. LLM-first search provides more relevant financial data")
            print(f"   3. Quality gain justifies cost for institutional research")
            print(f"\n   Implementation:")
            print(f"   • Use Exa for hypothesis validation (high-value queries)")
            print(f"   • Keep Brave as backup for general web search")
        elif brave_weighted_score > exa_weighted_score + 5:
            print(f"\n✅ RECOMMEND: Keep Brave Search")
            print(f"\n   Reasons:")
            print(f"   1. Better or equal quality ({brave_weighted_score:.1f} vs {exa_weighted_score:.1f})")
            print(f"   2. FREE tier sufficient for our volume")
            print(f"   3. No cost impact on $3.35/analysis budget")
            print(f"\n   Implementation:")
            print(f"   • Use Brave for all web search needs")
            print(f"   • Re-evaluate Exa in Phase 2 if quality improves")
        else:
            print(f"\n🤝 RECOMMEND: Hybrid Approach")
            print(f"\n   Reasons:")
            print(f"   1. Quality is comparable ({brave_weighted_score:.1f} vs {exa_weighted_score:.1f})")
            print(f"   2. Different strengths for different query types")
            print(f"\n   Implementation:")
            print(f"   • Brave: General web search, news, high-volume queries")
            print(f"   • Exa: Hypothesis validation, research-focused queries")
            print(f"   • Monitor usage and cost, optimize over time")

    print(f"\n" + "=" * 100)

    return True


if __name__ == "__main__":
    print("\n🔬 Brave Search vs Exa AI - Investment Research Comparison")
    print("=" * 100)
    print("\nThis test compares search quality for investment analysis use cases.")
    print("Both engines will search identical queries and results will be scored.")
    print("\n" + "=" * 100)

    result = asyncio.run(run_comparison_test())

    print("\n✅ Comparison test complete")
    print("\nNext steps:")
    print("  1. Review detailed results above")
    print("  2. Decide: Brave, Exa, or hybrid approach")
    print("  3. Update DATA_SOURCE_EVALUATION.md with findings")
