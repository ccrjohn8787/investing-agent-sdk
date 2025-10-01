"""Demo of reasoning trace system for transparency.

This shows how the system logs its thinking process,
similar to Claude/GPT reasoning traces.

Run with:
    python examples/reasoning_trace_demo.py
"""

import asyncio
from pathlib import Path

from investing_agents.agents import HypothesisGeneratorAgent
from investing_agents.observability import ReasoningTrace


async def main():
    print("\n" + "=" * 80)
    print("REASONING TRACE DEMO - Full Transparency System")
    print("=" * 80)
    print("\nThis demonstrates how the system shows its thinking process")
    print("Similar to Claude/GPT reasoning traces\n")

    # Create reasoning trace
    trace = ReasoningTrace(
        analysis_id="demo_001",
        ticker="AAPL",
        trace_dir=Path("./logs"),
    )

    # Step 1: Planning
    print("\n🎯 Step 1: Planning Analysis\n")
    trace.add_planning_step(
        description="Planning hypothesis generation strategy",
        plan={
            "company": "Apple Inc.",
            "ticker": "AAPL",
            "focus_areas": ["Services growth", "Hardware margins", "AI capabilities"],
            "hypothesis_count": 7,
        },
    )

    # Step 2: Generate hypotheses (real LLM call with trace)
    print("\n🧠 Step 2: Generating Hypotheses (Real LLM Call)\n")

    generator = HypothesisGeneratorAgent()

    # Build prompt
    prompt = generator._build_prompt("Apple", "AAPL", {})

    # Log the prompt
    print("📤 Sending prompt to LLM...")
    print(f"   Prompt length: {len(prompt)} characters")

    # Make real call
    result = await generator.generate("Apple", "AAPL", {})

    # Extract response for trace
    response_summary = f"Generated {len(result['hypotheses'])} hypotheses:\n"
    for h in result["hypotheses"][:3]:  # Show first 3
        response_summary += f"  - {h['title']} ({h['impact']} impact)\n"
    if len(result["hypotheses"]) > 3:
        response_summary += f"  ... and {len(result['hypotheses']) - 3} more"

    # Add to trace
    trace.add_agent_call(
        agent_name="HypothesisGeneratorAgent",
        description=f"Generated {len(result['hypotheses'])} investment hypotheses",
        prompt=prompt,  # Full prompt logged
        response=str(result),  # Full response logged
    )

    # Step 3: Evaluate quality
    print("\n📊 Step 3: Evaluating Hypothesis Quality\n")
    trace.add_evaluation(
        description="Evaluating generated hypotheses",
        scores={
            "count": 1.0,  # 7 hypotheses generated
            "specificity": 0.85,
            "falsifiability": 1.0,
            "unique": 1.0,
        },
        passed=True,
    )

    # Step 4: Synthesis (mock for demo)
    print("\n🔄 Step 4: Synthesizing Initial Insights\n")
    trace.add_synthesis(
        description="Identified key themes across hypotheses",
        hypotheses_analyzed=[h["id"] for h in result["hypotheses"]],
        key_insights=[
            "Services revenue growth is a major theme (3 hypotheses)",
            "Hardware margin sustainability is questioned (2 hypotheses)",
            "AI capabilities represent new growth vector",
        ],
    )

    # Display summary
    trace.display_summary()

    # Save trace
    trace_path = trace.save()
    print(f"\n💾 Reasoning trace saved to: {trace_path}")

    print("\n📖 How to Use Reasoning Traces:")
    print("   1. Run analysis with reasoning trace enabled")
    print("   2. Watch console for real-time transparency")
    print("   3. Review saved trace file for full details")
    print("   4. Debug issues by examining prompts/responses")
    print("   5. Understand system reasoning at each step")

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
