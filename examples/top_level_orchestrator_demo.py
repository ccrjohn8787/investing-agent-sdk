"""Demo of top-level orchestrator with WebSearch access.

This demo MUST be run from Claude Code context where WebSearch is available.

Usage:
    From Claude Code, ask:
    "Run the top-level orchestrator demo for NVIDIA"

    Or directly:
    python examples/top_level_orchestrator_demo.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investing_agents.top_level_orchestrator import run_top_level_research


async def main():
    """Run top-level research demo."""
    print("\n" + "=" * 80)
    print("TOP-LEVEL ORCHESTRATOR DEMO")
    print("WITH AUTOMATED WEB RESEARCH")
    print("=" * 80)
    print("\nThis demo demonstrates:")
    print("  ✅ Web research working at top level (WebSearch available!)")
    print("  ✅ Python agents called for specialized tasks")
    print("  ✅ Full automated workflow with no permission boundary issues")
    print("\n" + "=" * 80 + "\n")

    # Configuration
    ticker = "NVDA"
    company_name = "NVIDIA Corporation"
    work_dir = Path("top_level_research_demo")

    # Run research
    result = await run_top_level_research(
        ticker=ticker,
        company_name=company_name,
        num_iterations=1,  # Start with 1 iteration for demo
        web_research_enabled=True,
        work_dir=work_dir,
    )

    # Display summary
    print("\n" + "=" * 80)
    print("DEMO COMPLETE - SUMMARY")
    print("=" * 80)

    final_hypotheses = result.get("final_hypotheses", [])
    print(f"\nFinal Hypotheses: {len(final_hypotheses)}")

    for i, hyp in enumerate(final_hypotheses[:3], 1):  # Show top 3
        print(f"\n{i}. {hyp.get('title', 'Unknown')}")
        print(f"   Confidence: {hyp.get('confidence', 0):.2f}")

        # Check for web evidence
        web_evidence = hyp.get("web_evidence", [])
        sec_evidence = hyp.get("evidence", [])

        print(f"   Evidence: {len(sec_evidence)} SEC + {len(web_evidence)} Web")

        if web_evidence:
            print(f"   ✅ WEB RESEARCH WORKED! Found {len(web_evidence)} web items")
        else:
            print(f"   ⚠️  No web evidence (WebSearch may not be available)")

    print(f"\n{'=' * 80}")
    print(f"Full report: {work_dir / 'final_report.json'}")
    print(f"{'=' * 80}\n")

    # Verification
    total_web_evidence = sum(
        len(h.get("web_evidence", []))
        for h in final_hypotheses
    )

    if total_web_evidence > 0:
        print("✅ SUCCESS: Web research is working at top level!")
        print(f"   Found {total_web_evidence} web evidence items across all hypotheses")
        print("\nThis proves:")
        print("  • WebSearch is accessible from top-level orchestrator")
        print("  • Python agents work correctly when called from top level")
        print("  • Permission boundary issue is SOLVED")
    else:
        print("⚠️  WARNING: No web evidence found")
        print("\nPossible reasons:")
        print("  • This was not run from Claude Code (WebSearch not available)")
        print("  • WebSearch permission not granted")
        print("  • Run this from Claude Code context for full functionality")

    return result


if __name__ == "__main__":
    print("\n🚀 Starting Top-Level Orchestrator Demo...")
    print("=" * 80)
    print("NOTE: For web research to work, run this from Claude Code")
    print("      where WebSearch tool is available")
    print("=" * 80 + "\n")

    result = asyncio.run(main())
