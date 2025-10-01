"""End-to-end demo with web UI for real-time monitoring.

This demo runs the complete investment analysis with a web interface
that shows real-time progress, reasoning traces, and metrics.

Usage:
    python examples/demo_with_ui.py

Then open your browser to: http://127.0.0.1:5000
"""

import asyncio
import threading
from pathlib import Path
import tempfile
from datetime import datetime

from investing_agents.agents import (
    DeepResearchAgent,
    DialecticalEngine,
    EvaluatorAgent,
    HypothesisGeneratorAgent,
    NarrativeBuilderAgent,
)
from investing_agents.observability import ReasoningTrace
from investing_agents.metrics import PerformanceMetrics
from investing_agents.web_ui import monitor, run_ui

# Sample sources (same as regular demo)
SAMPLE_SOURCES = [
    {
        "type": "10-Q",
        "date": "2024-06-29",
        "url": "https://sec.gov/apple-10q-q3-2024",
        "content": """Apple Inc. Form 10-Q Q3 2024

Revenue Breakdown:
- Products: $71.2B (75%)
- Services: $23.7B (25%)

YoY Growth:
- Products: -5%
- Services: +18%

Margin Structure:
- Gross margin: 45.2%
- Products margin: 36.5%
- Services margin: 72%
- Operating margin: 30.3%

Key Metrics:
- iPhone revenue: $39.3B (-1% YoY)
- Mac revenue: $7B (+2% YoY)
- iPad revenue: $7.2B (+24% YoY)
- Wearables: $8.1B (-2% YoY)
- Services: $23.7B (+18% YoY)
""",
    },
    {
        "type": "earnings_call",
        "date": "2024-08-01",
        "url": "https://seekingalpha.com/article/apple-q3-2024",
        "content": """Apple Q3 2024 Earnings Call Transcript

CEO Tim Cook:
- Services business crossed 25% of total revenue
- Paid subscriptions exceeded 1 billion milestone
- Strong growth in emerging markets
- Vision Pro ecosystem showing early traction

CFO Luca Maestri:
- Services gross margin expanded to 72%
- Operating leverage driving margin expansion
- Cash flow generation remains strong at $29B
- Returned $27B to shareholders via dividends and buybacks
""",
    },
    {
        "type": "analyst_report",
        "date": "2024-08-15",
        "url": "https://goldman-sachs/research/apple-2024",
        "content": """Goldman Sachs: Apple Inc. Analysis (August 2024)

Investment Thesis:
- Services transformation accelerating faster than expected
- Margin expansion driven by services mix shift
- Price target: $250 (20% upside)

Key Points:
- Services projected to reach 30% of revenue by FY2026
- Gross margin expansion of 130bps through FY2026
- App Store regulatory risks priced in
- iPhone demand stabilizing after China weakness
""",
    },
    {
        "type": "news",
        "date": "2024-08-20",
        "url": "https://bloomberg.com/apple-services-growth",
        "content": """Bloomberg: Apple Services Hit Record High

Apple's services business reached $23.7 billion in Q3 2024,
growing 18% year-over-year and representing exactly 25% of
total company revenue for the first time.

Key drivers:
- Paid subscriptions: 1.03 billion (up 20% YoY)
- App Store revenue: $6.9 billion
- iCloud storage: $4.2 billion (growing 25% YoY)
- Apple Music: 93 million subscribers
- Apple TV+: Strong content investment

Analysts note this milestone validates Apple's transition
from hardware-centric to services-augmented business model.
""",
    },
]


async def run_analysis_with_ui(
    company_name: str,
    ticker: str,
):
    """Run analysis with web UI progress monitoring.

    Args:
        company_name: Company name
        ticker: Stock ticker
    """
    # Create trace directory
    trace_dir = Path(tempfile.mkdtemp())

    # Initialize metrics
    metrics = PerformanceMetrics()

    # Initialize reasoning trace
    trace = ReasoningTrace(
        analysis_id=f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        ticker=ticker,
        trace_dir=trace_dir,
    )

    # Notify UI: analysis starting
    monitor.emit("analysis_start", {
        "company": company_name,
        "ticker": ticker,
        "start_time": datetime.now().isoformat(),
    })

    # Initialize agents
    hypothesis_agent = HypothesisGeneratorAgent()
    research_agent = DeepResearchAgent()
    evaluator = EvaluatorAgent()
    dialectical_engine = DialecticalEngine()
    narrative_agent = NarrativeBuilderAgent()

    print(f"\n{'='*80}")
    print(f"END-TO-END INVESTMENT ANALYSIS: {company_name} ({ticker})")
    print(f"{'='*80}\n")

    # Step 1: Generate Hypotheses
    monitor.emit("step_start", {
        "step_number": 1,
        "step_name": "Generate Investment Hypotheses",
        "agent_name": "HypothesisGeneratorAgent",
    })

    with metrics.timer("agent.hypothesis_generator"):
        context = {
            "name": company_name,
            "ticker": ticker,
            "sector": "Technology",
        }
        hyp_result = await hypothesis_agent.generate(
            company=company_name,
            ticker=ticker,
            context=context,
        )

    metrics.record_call(
        agent_name="HypothesisGeneratorAgent",
        prompt_length=len(str(context)),
        response_length=len(str(hyp_result)),
    )

    monitor.emit("trace_event", {
        "timestamp": datetime.now().isoformat(),
        "description": f"Generated {len(hyp_result['hypotheses'])} investment hypotheses",
        "agent_name": "HypothesisGeneratorAgent",
    })

    monitor.emit("step_complete", {
        "step_number": 1,
        "hypotheses_count": len(hyp_result["hypotheses"]),
    })

    # Select top 3
    top_hypotheses = sorted(
        hyp_result["hypotheses"],
        key=lambda h: (
            {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(h.get("impact", "MEDIUM"), 2),
            h.get("confidence", 0.5),
        ),
        reverse=True,
    )[:3]

    # Step 2: Research Hypotheses (parallel)
    monitor.emit("step_start", {
        "step_number": 2,
        "step_name": "Research Hypotheses (parallel)",
        "agent_name": "DeepResearchAgent",
    })

    async def research_with_monitoring(i, hypothesis):
        with metrics.timer(f"agent.deep_research_h{i}", hypothesis_id=hypothesis["id"]):
            evidence = await research_agent.research_hypothesis(
                hypothesis=hypothesis,
                sources=SAMPLE_SOURCES,
                trace=trace,
            )

        metrics.record_call(
            agent_name="DeepResearchAgent",
            prompt_length=len(str(hypothesis)) + sum(len(str(s)) for s in SAMPLE_SOURCES),
            response_length=len(str(evidence)),
        )

        monitor.emit("trace_event", {
            "timestamp": datetime.now().isoformat(),
            "description": f"Researched hypothesis {i}/3: Found {len(evidence['evidence_items'])} evidence items",
            "agent_name": "DeepResearchAgent",
        })

        return evidence

    evidence_results = await asyncio.gather(*[
        research_with_monitoring(i, hyp)
        for i, hyp in enumerate(top_hypotheses, 1)
    ])

    monitor.emit("step_complete", {
        "step_number": 2,
        "evidence_count": sum(len(e["evidence_items"]) for e in evidence_results),
    })

    # Step 3: Evaluate Evidence
    monitor.emit("step_start", {
        "step_number": 3,
        "step_name": "Evaluate Evidence Quality",
        "agent_name": "EvaluatorAgent",
    })

    all_evidence = []
    for result in evidence_results:
        all_evidence.extend(result["evidence_items"])

    with metrics.timer("agent.evaluator"):
        evidence_eval = await evaluator.evaluate_evidence(all_evidence)

    metrics.record_call(
        agent_name="EvaluatorAgent",
        prompt_length=len(str(all_evidence)),
        response_length=len(str(evidence_eval)),
    )

    monitor.emit("trace_event", {
        "timestamp": datetime.now().isoformat(),
        "description": f"Evaluated evidence: Overall score {evidence_eval['overall_score']:.2f}/1.0",
        "agent_name": "EvaluatorAgent",
    })

    monitor.emit("step_complete", {
        "step_number": 3,
        "evaluation_score": evidence_eval["overall_score"],
    })

    # Step 4: Dialectical Synthesis (parallel)
    monitor.emit("step_start", {
        "step_number": 4,
        "step_name": "Dialectical Synthesis (parallel)",
        "agent_name": "DialecticalEngine",
    })

    async def synthesize_with_monitoring(i, hypothesis, evidence):
        with metrics.timer(f"agent.dialectical_engine_h{i}", hypothesis_id=hypothesis["id"]):
            synthesis = await dialectical_engine.synthesize(
                hypothesis=hypothesis,
                evidence=evidence,
                prior_synthesis=None,
                iteration=6,
                trace=trace,
            )

        metrics.record_call(
            agent_name="DialecticalEngine",
            prompt_length=len(str(hypothesis)) + len(str(evidence)),
            response_length=len(str(synthesis)),
        )

        insights_count = len(synthesis["synthesis"]["non_obvious_insights"])
        monitor.emit("trace_event", {
            "timestamp": datetime.now().isoformat(),
            "description": f"Synthesized hypothesis {i}/2: Generated {insights_count} insights",
            "agent_name": "DialecticalEngine",
        })

        return synthesis

    synthesis_results = await asyncio.gather(*[
        synthesize_with_monitoring(i, hyp, ev)
        for i, (hyp, ev) in enumerate(zip(top_hypotheses[:2], evidence_results[:2]), 1)
    ])

    monitor.emit("step_complete", {
        "step_number": 4,
        "synthesis_count": len(synthesis_results),
    })

    # Step 5: Build Final Report
    monitor.emit("step_start", {
        "step_number": 5,
        "step_name": "Build Final Investment Report",
        "agent_name": "NarrativeBuilderAgent",
    })

    evidence_bundle = {"evidence_items": all_evidence}

    with metrics.timer("agent.narrative_builder"):
        final_report = await narrative_agent.build_report(
            validated_hypotheses=top_hypotheses[:2],
            evidence_bundle=evidence_bundle,
            synthesis_history=synthesis_results,
            trace=trace,
        )

    metrics.record_call(
        agent_name="NarrativeBuilderAgent",
        prompt_length=len(str(top_hypotheses[:2])) + len(str(evidence_bundle)) + len(str(synthesis_results)),
        response_length=len(str(final_report)),
    )

    monitor.emit("trace_event", {
        "timestamp": datetime.now().isoformat(),
        "description": f"Generated final report: Recommendation {final_report['recommendation']['action']}",
        "agent_name": "NarrativeBuilderAgent",
    })

    monitor.emit("step_complete", {
        "step_number": 5,
        "recommendation": final_report["recommendation"]["action"],
    })

    # Save trace
    trace_path = trace.save()

    # Get metrics summary
    metrics_summary = metrics.get_summary()

    # Notify UI: analysis complete
    monitor.emit("analysis_complete", {
        "company": company_name,
        "ticker": ticker,
        "recommendation": final_report["recommendation"]["action"],
        "conviction": final_report["recommendation"].get("conviction"),
        "metrics": {
            "total_time": metrics_summary["total_time"],
            "total_calls": metrics_summary["total_calls"],
            "evidence_count": len(all_evidence),
        },
    })

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}\n")
    print(f"Recommendation: {final_report['recommendation']['action']}")
    print(f"Conviction: {final_report['recommendation'].get('conviction', 'N/A')}")
    print(f"Trace saved: {trace_path}")
    print(f"\nMetrics:")
    metrics.print_summary()


async def main():
    """Run demo with web UI."""
    # Start web UI in background thread
    ui_thread = threading.Thread(target=run_ui, daemon=True)
    ui_thread.start()

    # Wait a moment for server to start
    await asyncio.sleep(2)

    print("\n" + "="*80)
    print("WEB UI READY - Open your browser to: http://127.0.0.1:5000")
    print("="*80 + "\n")
    print("Press Enter to start analysis (or Ctrl+C to exit)...")
    input()

    # Run analysis
    await run_analysis_with_ui(
        company_name="Apple Inc.",
        ticker="AAPL",
    )

    print("\nAnalysis complete! Check the web UI for full details.")
    print("Press Enter to exit...")
    input()


if __name__ == "__main__":
    asyncio.run(main())
