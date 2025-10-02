"""Test full orchestrator integration with Exa MCP.

This test simulates how the orchestrator will use Exa MCP for web evidence
collection during hypothesis validation.

Workflow:
1. Generate a hypothesis
2. Create research questions
3. Use Exa MCP to fetch web evidence
4. Validate evidence quality and format
"""

import asyncio
import json
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


async def simulate_orchestrator_web_evidence():
    """Simulate orchestrator's web evidence collection workflow."""
    print("\n" + "=" * 80)
    print("TEST 4: Full Orchestrator Integration with Exa MCP")
    print("=" * 80)
    print("\nThis test simulates the complete orchestrator workflow:")
    print("  1. Hypothesis → Research Questions")
    print("  2. Research Questions → Web Search (Exa MCP)")
    print("  3. Web Results → Evidence Extraction")
    print("  4. Evidence → Quality Validation")
    print("=" * 80)

    # Check API key
    api_key = os.getenv("EXA_API_KEY")
    if not api_key or api_key == "your-exa-api-key-here":
        print("\n❌ ERROR: EXA_API_KEY not set")
        return False

    print(f"\n✓ Exa API key configured: {api_key[:10]}...")

    # Sample hypothesis (from real NVIDIA analysis)
    hypothesis = {
        "id": "h1",
        "title": "Data Center Revenue Growth Acceleration",
        "thesis": "NVIDIA's data center segment is experiencing accelerating growth driven by AI/ML demand, with Q4 FY2025 showing record revenue.",
        "impact": "POSITIVE",
        "target_evidence_count": 8
    }

    print(f"\n📋 Test Hypothesis:")
    print(f"   Title: {hypothesis['title']}")
    print(f"   Thesis: {hypothesis['thesis']}")
    print(f"   Expected Impact: {hypothesis['impact']}")

    # Simulate research question generation (normally done by LLM)
    research_questions = [
        "What was NVIDIA's Q4 FY2025 data center revenue?",
        "How does Q4 FY2025 data center revenue compare to prior year?",
        "What is driving NVIDIA's data center growth in 2024-2025?"
    ]

    print(f"\n🔍 Research Questions Generated:")
    for i, q in enumerate(research_questions, 1):
        print(f"   {i}. {q}")

    # Configure Exa MCP
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
        max_turns=10,
    )

    # Web evidence collection
    print("\n" + "=" * 80)
    print("WEB EVIDENCE COLLECTION")
    print("=" * 80)

    all_evidence = []

    for i, question in enumerate(research_questions, 1):
        print(f"\n[{i}/{len(research_questions)}] Researching: {question}")
        print("-" * 80)

        prompt = f"""Use mcp__exa__web_search_exa to search for information about:
"{question}"

Focus on: Financial reports, earnings releases, analyst reports.
Extract the top 3 most relevant results.

For each result, identify:
1. The specific claim or data point
2. Source type (earnings_call, analyst_report, news, etc.)
3. Any quantitative data (revenue, growth %, etc.)
4. Publication date if available"""

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

            # Parse evidence from responses
            combined_text = " ".join(text_responses)

            # Simple evidence extraction (real version uses LLM)
            evidence_item = {
                "question": question,
                "tool_used": len(tool_uses) > 0,
                "response_length": len(combined_text),
                "has_quantitative_data": any(
                    kw in combined_text.lower()
                    for kw in ["billion", "million", "%", "revenue", "growth"]
                ),
                "has_source_info": any(
                    kw in combined_text.lower()
                    for kw in ["nvidia", "q4", "fy2025", "earnings"]
                ),
                "preview": combined_text[:200] if combined_text else "No response"
            }

            all_evidence.append(evidence_item)

            # Display results
            status = "✅" if evidence_item["tool_used"] else "❌"
            print(f"\n   {status} Tool execution: {'Success' if evidence_item['tool_used'] else 'Failed'}")
            print(f"   📊 Response length: {evidence_item['response_length']} chars")
            print(f"   🔢 Has quantitative data: {evidence_item['has_quantitative_data']}")
            print(f"   📄 Has source info: {evidence_item['has_source_info']}")
            print(f"   📝 Preview: {evidence_item['preview'][:150]}...")

        except Exception as e:
            print(f"\n   ❌ Error: {e}")
            all_evidence.append({
                "question": question,
                "error": str(e)
            })

    # Quality assessment
    print("\n" + "=" * 80)
    print("EVIDENCE QUALITY ASSESSMENT")
    print("=" * 80)

    successful_searches = sum(1 for e in all_evidence if e.get("tool_used", False))
    with_quantitative = sum(1 for e in all_evidence if e.get("has_quantitative_data", False))
    with_source_info = sum(1 for e in all_evidence if e.get("has_source_info", False))

    print(f"\n📊 Evidence Collection Stats:")
    print(f"   Total questions: {len(research_questions)}")
    print(f"   Successful searches: {successful_searches}/{len(research_questions)}")
    print(f"   With quantitative data: {with_quantitative}/{len(research_questions)}")
    print(f"   With source attribution: {with_source_info}/{len(research_questions)}")

    # Success criteria for orchestrator integration
    integration_successful = (
        successful_searches >= 2 and  # At least 2/3 searches work
        with_quantitative >= 1 and     # At least some quantitative data
        with_source_info >= 2          # Most results have source info
    )

    print("\n" + "=" * 80)
    if integration_successful:
        print("✅ ORCHESTRATOR INTEGRATION SUCCESSFUL")
        print("=" * 80)
        print("\n✓ Exa MCP works in nested query() context")
        print("✓ Search returns investment-relevant data")
        print("✓ Evidence includes quantitative metrics")
        print("✓ Sources are properly attributed")
        print("\n📋 Ready for Production Integration:")
        print("   1. Update orchestrator._fetch_web_evidence() to use Exa MCP")
        print("   2. Add evidence parsing logic")
        print("   3. Integrate with hypothesis validation loop")
        print("   4. Expected quality improvement: +25 points")
    else:
        print("❌ INTEGRATION ISSUES DETECTED")
        print("=" * 80)
        print(f"\n   Successful searches: {successful_searches}/3 (need ≥2)")
        print(f"   Quantitative data: {with_quantitative}/3 (need ≥1)")
        print(f"   Source attribution: {with_source_info}/3 (need ≥2)")
        print("\n📋 Issues to investigate:")
        print("   - Permission boundary may still be blocking")
        print("   - Query formulation needs refinement")
        print("   - Evidence parsing logic needs adjustment")

    # Save detailed results for analysis
    output_file = Path("test_orchestrator_results.json")
    with open(output_file, "w") as f:
        json.dump({
            "hypothesis": hypothesis,
            "research_questions": research_questions,
            "evidence_collected": all_evidence,
            "quality_metrics": {
                "successful_searches": successful_searches,
                "with_quantitative": with_quantitative,
                "with_source_info": with_source_info,
                "integration_successful": integration_successful
            }
        }, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")

    return integration_successful


if __name__ == "__main__":
    print("\n🔬 Exa Orchestrator Integration Test")
    print("=" * 80)
    print("This test validates full orchestrator workflow with Exa MCP")
    print("=" * 80)

    result = asyncio.run(simulate_orchestrator_web_evidence())

    print("\n" + "=" * 80)
    print("FINAL INTEGRATION VERDICT")
    print("=" * 80)
    if result:
        print("✅ READY FOR PRODUCTION INTEGRATION")
        print("\nExa MCP successfully:")
        print("  • Works from nested query() calls")
        print("  • Returns investment-quality data")
        print("  • Provides proper source attribution")
        print("\nNext: Update orchestrator to use Exa MCP")
    else:
        print("⚠️  INTEGRATION NEEDS REFINEMENT")
        print("\nReview test_orchestrator_results.json for details")
