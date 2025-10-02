"""Test orchestrator-level WebSearch integration."""

import asyncio
from investing_agents.core.orchestrator import Orchestrator, OrchestratorConfig


async def test_orchestrator_web_search():
    """Test the orchestrator's web search methods directly."""
    print("\n" + "=" * 80)
    print("Testing Orchestrator Web Search Integration")
    print("=" * 80)

    # Create minimal orchestrator
    config = OrchestratorConfig(
        enable_web_research=True,
        web_research_questions_per_hypothesis=2,
        web_research_results_per_query=5,
    )

    orchestrator = Orchestrator(
        sources=[],  # No sources needed for this test
        work_dir="/tmp/test_websearch",
        config=config,
    )

    # Test hypothesis
    hypothesis = {
        "id": "h_test",
        "title": "NVIDIA Data Center Revenue Growth",
        "thesis": "NVIDIA's data center revenue continues to grow rapidly",
        "evidence_needed": ["quarterly revenue", "growth rate", "customer data"],
    }

    # Test 1: Generate research questions
    print("\n" + "-" * 80)
    print("TEST 1: Generate Research Questions")
    print("-" * 80)

    questions = await orchestrator._generate_research_questions(
        hypothesis=hypothesis, num_questions=2
    )

    print(f"\nGenerated {len(questions)} questions:")
    for i, q in enumerate(questions, 1):
        print(f"  {i}. {q}")

    # Test 2: Fetch web evidence
    print("\n" + "-" * 80)
    print("TEST 2: Fetch Web Evidence")
    print("-" * 80)

    evidence_items = await orchestrator._fetch_web_evidence(
        hypothesis=hypothesis, questions=questions, results_per_query=5
    )

    print(f"\nExtracted {len(evidence_items)} evidence items:")
    if evidence_items:
        for i, item in enumerate(evidence_items[:3], 1):  # Show first 3
            print(f"\n  Evidence {i}:")
            print(f"    Claim: {item['claim'][:100]}...")
            print(f"    Source: {item.get('source_reference', 'N/A')}")
            print(f"    Confidence: {item.get('confidence', 0.0)}")
            print(f"    URL: {item.get('url', 'N/A')[:60]}...")
    else:
        print("  ⚠️  No evidence extracted - need to debug parsing!")

    # Test 3: Raw response inspection
    print("\n" + "-" * 80)
    print("TEST 3: Debug Mode - Print Raw Response")
    print("-" * 80)
    print("This would require modifying _fetch_web_evidence to return raw text...")

    return len(evidence_items) > 0


if __name__ == "__main__":
    print("\n🔬 Orchestrator WebSearch Integration Test")
    print("=" * 80)

    result = asyncio.run(test_orchestrator_web_search())

    print("\n" + "=" * 80)
    print("RESULT")
    print("=" * 80)

    if result:
        print("✅ SUCCESS: Web evidence extracted successfully!")
        print("   The orchestrator-level approach is working.")
    else:
        print("❌ FAILURE: No evidence extracted")
        print("   Need to debug:")
        print("   1. Check if WebSearch tool is actually executing")
        print("   2. Verify JSON response format from LLM")
        print("   3. Test _parse_web_evidence() with sample data")
