"""End-to-end demo of complete investment analysis workflow.

This demo runs a complete analysis using all 5 core agents:
1. HypothesisGeneratorAgent - Generate testable hypotheses
2. DeepResearchAgent - Gather evidence for hypotheses
3. EvaluatorAgent - Evaluate evidence quality
4. DialecticalEngine - Synthesize bull/bear analysis
5. NarrativeBuilderAgent - Generate final investment report

Flow:
- Generate hypotheses for a company
- Research top 3 hypotheses with sample sources
- Evaluate evidence quality
- Synthesize bull/bear for top 2 hypotheses
- Build comprehensive final report
- Display results with full reasoning traces
"""

import asyncio
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


# Sample sources for research (in production, these would come from EDGAR/news APIs)
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
- Products gross margin: 36.5%
- Services gross margin: 71.8%
- Overall gross margin: 45.2%

Key Metrics:
- iPhone revenue: $39.3B (-1% YoY)
- Mac revenue: $7.0B (+2% YoY)
- iPad revenue: $7.2B (-2% YoY)
- Wearables: $8.1B (-2% YoY)
- Services: $23.7B (+18% YoY)

Services Breakdown:
- App Store: +15% YoY
- iCloud: +22% YoY
- Apple Music: +12% YoY
- AppleCare: +8% YoY
- Apple Pay & Other: +25% YoY""",
    },
    {
        "type": "earnings_call",
        "date": "2024-08-01",
        "url": "https://seekingalpha.com/apple-q3-2024",
        "content": """Apple Q3 2024 Earnings Call Transcript

CEO Tim Cook:
"We're incredibly proud that services has reached 25% of our total revenue this quarter.
This represents a major milestone in our business transformation. With over 1 billion
paid subscriptions across our ecosystem, we're seeing unprecedented engagement."

CFO Luca Maestri:
"Services gross margin reached 72% this quarter, up from 70% last year. We expect
continued double-digit services growth through fiscal 2025. The combination of our
growing installed base and expanding services portfolio creates a powerful flywheel."

Q&A Section:
Analyst: "Can you comment on the sustainability of services growth?"
Cook: "We see multiple growth vectors - installed base expansion, attach rate improvement,
and new services like Apple Pay Later and Apple Sports. We're still early in many categories."

Analyst: "What about App Store regulatory pressure?"
Maestri: "We're diversifying our services portfolio. While App Store is important,
it's now less than 30% of services revenue. We have strong growth in iCloud, subscriptions,
and financial services."

Analyst: "How should we think about margin trajectory?"
Maestri: "As services mix grows, overall margins should continue expanding. Every percentage
point increase in services mix adds approximately 35 basis points to gross margin."
""",
    },
    {
        "type": "analyst_report",
        "date": "2024-08-05",
        "url": "https://gs.com/research/apple-2024",
        "content": """Goldman Sachs: Apple Services Deep Dive
August 2024

Executive Summary:
Apple's services transformation is accelerating. We see services reaching 30% of revenue
by FY2025, driving significant margin expansion and warranting valuation re-rating.

Key Findings:
- Services margin: 72% vs 36% for products
- Subscriber growth: 20% YoY to 1.03B paid subscriptions
- ARPU increasing: $9.50/month per subscription (+12% YoY)
- Services TAM: $300B+ (payments, health, entertainment, cloud)

Forecast:
- Services revenue: $100B in FY2025 (27% of total)
- Services revenue: $120B in FY2026 (30% of total)
- Overall gross margin: 46.5% by FY2026 (vs 45.2% current)

Valuation Impact:
- Services deserves SaaS-like 8-10x revenue multiple
- Hardware deserves 1-2x revenue multiple
- Blended approach suggests 30% upside from current levels

Price Target: $250 (from $190 current)
Rating: BUY
""",
    },
    {
        "type": "news",
        "date": "2024-08-10",
        "url": "https://reuters.com/apple-services",
        "content": """Reuters: Apple Services Growth Accelerates Despite Regulatory Headwinds

Apple's services business continues to defy skeptics, growing 18% year-over-year
despite increased regulatory scrutiny in Europe and the United States.

Key Developments:
- EU Digital Markets Act: Apple must allow third-party app stores
- US antitrust investigation: Focus on App Store practices
- Despite pressure, services growth accelerating (18% vs 15% prior quarter)

Industry experts note that Apple's services diversification strategy is paying off:
- Payments (Apple Pay, Apple Card): Growing 25%+
- Subscriptions (Music, TV+, Fitness+): Growing 15-20%
- Cloud (iCloud): Growing 20%+

"The regulatory risk is real but overblown," said analyst Gene Munster.
"Services is becoming less dependent on App Store. The business model is more
resilient than many realize."

Competitive Position:
- Apple Music: 93M subscribers vs Spotify's 220M (but closing gap)
- Apple TV+: 25M subscribers (small but growing)
- iCloud: 850M+ users (dominant in iOS ecosystem)
- Apple Pay: 43% of US mobile payment transactions
""",
    },
]


async def run_end_to_end_analysis(
    company_name: str,
    ticker: str,
    trace_dir: Path,
) -> dict:
    """Run complete end-to-end investment analysis.

    Args:
        company_name: Company name (e.g., "Apple Inc.")
        ticker: Stock ticker (e.g., "AAPL")
        trace_dir: Directory to save reasoning traces

    Returns:
        Complete analysis results with final report
    """
    # Initialize performance metrics
    metrics = PerformanceMetrics()

    # Initialize reasoning trace
    trace = ReasoningTrace(
        analysis_id=f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        ticker=ticker,
        trace_dir=trace_dir,
    )

    trace.add_planning_step(
        description=f"Starting end-to-end analysis for {company_name} ({ticker})",
        plan={
            "company": company_name,
            "ticker": ticker,
            "workflow": [
                "1. Generate hypotheses",
                "2. Research top 3 hypotheses",
                "3. Evaluate evidence",
                "4. Synthesize bull/bear (top 2)",
                "5. Build final report",
            ],
        },
    )

    # Initialize all agents
    hypothesis_agent = HypothesisGeneratorAgent()
    research_agent = DeepResearchAgent()
    evaluator = EvaluatorAgent()
    dialectical_engine = DialecticalEngine()
    narrative_agent = NarrativeBuilderAgent()

    print(f"\n{'='*80}")
    print(f"END-TO-END INVESTMENT ANALYSIS: {company_name} ({ticker})")
    print(f"{'='*80}\n")

    # =========================================================================
    # Step 1: Generate Hypotheses
    # =========================================================================
    print(f"\n{'─'*80}")
    print("STEP 1: Generating Investment Hypotheses")
    print(f"{'─'*80}\n")

    context = {
        "name": company_name,
        "ticker": ticker,
        "sector": "Technology",
        "description": "Consumer electronics and services company",
    }

    with metrics.timer("agent.hypothesis_generator"):
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

    # Log to trace (HypothesisGenerator doesn't have built-in trace support yet)
    trace.add_step(
        step_type="agent_call",
        description=f"Generated {len(hyp_result['hypotheses'])} investment hypotheses",
        agent_name="HypothesisGeneratorAgent",
    )

    print(f"\n✓ Generated {len(hyp_result['hypotheses'])} hypotheses")
    for i, hyp in enumerate(hyp_result["hypotheses"][:5], 1):
        print(f"  {i}. {hyp['title']} (impact: {hyp.get('impact', 'N/A')})")

    # Select top 3 for research
    top_hypotheses = sorted(
        hyp_result["hypotheses"],
        key=lambda h: (
            {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(h.get("impact", "MEDIUM"), 2),
            h.get("confidence", 0.5),
        ),
        reverse=True,
    )[:3]

    print(f"\n✓ Selected top 3 hypotheses for research")

    # =========================================================================
    # Step 2: Research Hypotheses
    # =========================================================================
    print(f"\n{'─'*80}")
    print("STEP 2: Researching Hypotheses (Deep Evidence Gathering)")
    print(f"{'─'*80}\n")

    # Parallel research for all 3 hypotheses
    print(f"\nResearching all 3 hypotheses in parallel...")

    async def research_with_timing(i, hypothesis):
        """Research single hypothesis with timing."""
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
        return evidence

    # Execute all research in parallel
    evidence_results = await asyncio.gather(*[
        research_with_timing(i, hyp)
        for i, hyp in enumerate(top_hypotheses, 1)
    ])

    # Print results
    for i, evidence in enumerate(evidence_results, 1):
        print(
            f"  ✓ Hypothesis {i}: Found {len(evidence['evidence_items'])} evidence items "
            f"(avg confidence: {evidence['average_confidence']:.2f})"
        )

    # =========================================================================
    # Step 3: Evaluate Evidence Quality
    # =========================================================================
    print(f"\n{'─'*80}")
    print("STEP 3: Evaluating Evidence Quality")
    print(f"{'─'*80}\n")

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

    print(f"✓ Evidence evaluation complete")
    print(f"  Overall score: {evidence_eval['overall_score']:.2f}/1.0")
    print(f"  Dimensions:")
    for dim, score in evidence_eval["dimensions"].items():
        print(f"    - {dim}: {score:.2f}")

    # =========================================================================
    # Step 4: Dialectical Synthesis (Top 2 Hypotheses)
    # =========================================================================
    print(f"\n{'─'*80}")
    print("STEP 4: Dialectical Synthesis (Bull/Bear Analysis)")
    print(f"{'─'*80}\n")

    # Parallel dialectical synthesis for top 2 hypotheses
    print(f"\nSynthesizing both hypotheses in parallel...")

    async def synthesize_with_timing(i, hypothesis, evidence):
        """Synthesize single hypothesis with timing."""
        with metrics.timer(f"agent.dialectical_engine_h{i}", hypothesis_id=hypothesis["id"]):
            synthesis = await dialectical_engine.synthesize(
                hypothesis=hypothesis,
                evidence=evidence,
                prior_synthesis=None,
                iteration=6,  # Simulate checkpoint iteration
                trace=trace,
            )

        metrics.record_call(
            agent_name="DialecticalEngine",
            prompt_length=len(str(hypothesis)) + len(str(evidence)),
            response_length=len(str(synthesis)),
        )
        return synthesis

    # Execute both synthesis in parallel
    synthesis_results = await asyncio.gather(*[
        synthesize_with_timing(i, hyp, ev)
        for i, (hyp, ev) in enumerate(zip(top_hypotheses[:2], evidence_results[:2]), 1)
    ])

    # Print results
    for i, synthesis in enumerate(synthesis_results, 1):
        insights = synthesis["synthesis"]["non_obvious_insights"]
        print(f"  ✓ Hypothesis {i}: Generated {len(insights)} non-obvious insights")
        print(f"    Bull case confidence: {synthesis['bull_case']['confidence']:.2f}")
        print(f"    Bear case confidence: {synthesis['bear_case']['confidence']:.2f}")

    # =========================================================================
    # Step 5: Build Final Report
    # =========================================================================
    print(f"\n{'─'*80}")
    print("STEP 5: Building Final Investment Report")
    print(f"{'─'*80}\n")

    # Aggregate all evidence
    evidence_bundle = {
        "evidence_items": all_evidence,
    }

    # Build comprehensive report
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

    print(f"✓ Final report generated")
    print(f"  Sections: {len(final_report)} major sections")
    print(f"  Recommendation: {final_report['recommendation']['action']}")
    print(f"  Conviction: {final_report['recommendation'].get('conviction', 'N/A')}")

    # Calculate evidence coverage
    coverage = narrative_agent.calculate_evidence_coverage(final_report)
    print(f"  Evidence coverage: {coverage:.1%}")

    # =========================================================================
    # Save Reasoning Trace
    # =========================================================================
    print(f"\n{'─'*80}")
    print("SAVING REASONING TRACE")
    print(f"{'─'*80}\n")

    trace_path = trace.save()
    print(f"✓ Reasoning trace saved to: {trace_path}")
    print(f"  Total steps: {len(trace.steps)}")
    print(f"  Agent calls: {sum(1 for s in trace.steps if s.step_type == 'agent_call')}")

    # Display summary
    trace.display_summary()

    # =========================================================================
    # Performance Metrics
    # =========================================================================
    print("\n")
    metrics.print_summary()

    # =========================================================================
    # Return Results
    # =========================================================================
    return {
        "company": company_name,
        "ticker": ticker,
        "hypotheses": hyp_result["hypotheses"],
        "top_hypotheses": top_hypotheses,
        "evidence_results": evidence_results,
        "evidence_evaluation": evidence_eval,
        "synthesis_results": synthesis_results,
        "final_report": final_report,
        "trace_path": trace_path,
        "metrics": metrics.get_summary(),
    }


async def main():
    """Run end-to-end demo."""
    print("\n" + "="*80)
    print("INVESTMENT ANALYSIS PLATFORM - END-TO-END DEMO")
    print("="*80)
    print("\nThis demo runs a complete investment analysis using all 5 core agents:")
    print("  1. HypothesisGeneratorAgent - Generate testable hypotheses")
    print("  2. DeepResearchAgent - Gather evidence for hypotheses")
    print("  3. EvaluatorAgent - Evaluate evidence quality")
    print("  4. DialecticalEngine - Synthesize bull/bear analysis")
    print("  5. NarrativeBuilderAgent - Generate final investment report")
    print("\nFull reasoning traces will be displayed and saved.")
    print("="*80 + "\n")

    # Run analysis
    with tempfile.TemporaryDirectory() as tmpdir:
        results = await run_end_to_end_analysis(
            company_name="Apple Inc.",
            ticker="AAPL",
            trace_dir=Path(tmpdir),
        )

        # Display final results
        print(f"\n{'='*80}")
        print("ANALYSIS COMPLETE - FINAL RESULTS")
        print(f"{'='*80}\n")

        report = results["final_report"]

        print(f"Company: {results['company']} ({results['ticker']})")
        print(f"\nHypotheses Analyzed: {len(results['top_hypotheses'])}")
        for i, hyp in enumerate(results["top_hypotheses"], 1):
            print(f"  {i}. {hyp['title']}")

        print(f"\nEvidence Gathered: {len(results['evidence_results'])} hypothesis research sessions")
        total_evidence = sum(len(e["evidence_items"]) for e in results["evidence_results"])
        print(f"  Total evidence items: {total_evidence}")

        print(f"\nSynthesis:")
        for i, syn in enumerate(results["synthesis_results"], 1):
            print(f"  Hypothesis {i}:")
            print(f"    - Bull case: {syn['bull_case']['overall_strength']}")
            print(f"    - Bear case: {syn['bear_case']['overall_strength']}")
            print(f"    - Insights: {len(syn['synthesis']['non_obvious_insights'])}")

        print(f"\n{'─'*80}")
        print("FINAL INVESTMENT RECOMMENDATION")
        print(f"{'─'*80}\n")

        rec = report["recommendation"]
        exec_summary = report["executive_summary"]

        print(f"Action: {rec['action']}")
        print(f"Conviction: {rec.get('conviction', 'N/A')}")
        print(f"Timeframe: {rec.get('timeframe', 'N/A')}")
        print(f"\nThesis: {exec_summary.get('thesis', 'N/A')}")
        print(f"\nKey Catalysts:")
        for catalyst in exec_summary.get("catalysts", [])[:3]:
            print(f"  • {catalyst}")
        print(f"\nKey Risks:")
        for risk in exec_summary.get("risks", [])[:3]:
            print(f"  • {risk}")

        print(f"\n{'='*80}")
        print("DEMO COMPLETE")
        print(f"{'='*80}\n")
        print(f"Reasoning trace saved to: {results['trace_path']}")
        print("\nAll 5 agents successfully integrated and produced a complete analysis!")
        print("\nNext steps:")
        print("  - Review the reasoning trace to see full transparency")
        print("  - Run with different companies to test robustness")
        print("  - Enhance with real EDGAR data fetching")
        print("  - Add iteration loop for hypothesis refinement")
        print()


if __name__ == "__main__":
    asyncio.run(main())
