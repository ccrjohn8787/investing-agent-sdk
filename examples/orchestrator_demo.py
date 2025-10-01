"""Demo using the Orchestrator with real EDGAR data.

This demo shows the full orchestration loop:
1. Fetch real data from SEC EDGAR
2. Generate hypotheses
3. Iterative deepening loop (1-3 iterations for testing)
4. Build final report

Usage:
    python examples/orchestrator_demo.py
"""

import asyncio
from pathlib import Path
import tempfile

from investing_agents.core.orchestrator import Orchestrator, OrchestratorConfig
from investing_agents.connectors import SourceManager


async def main():
    """Run orchestrator demo with real EDGAR data."""
    # Configuration - use shorter loop for testing
    config = OrchestratorConfig(
        max_iterations=3,  # Short loop for testing (normally 15)
        confidence_threshold=0.85,
        checkpoint_iterations=[1, 2, 3],  # Checkpoint every iteration for testing
        min_iterations=1,
        top_n_hypotheses_for_synthesis=2,
        enable_parallel_research=True,
    )

    # Create work directory
    work_dir = Path(tempfile.mkdtemp())
    print(f"\nWork directory: {work_dir}\n")

    # Initialize source manager
    source_manager = SourceManager()

    # Company to analyze
    ticker = "AAPL"
    company_name = "Apple Inc."

    print("=" * 80)
    print(f"ORCHESTRATOR DEMO: {company_name} ({ticker})")
    print("=" * 80)
    print("\nFetching real data from SEC EDGAR...")

    # Fetch real sources
    sources = await source_manager.fetch_all_sources(
        ticker=ticker,
        company_name=company_name,
        include_fundamentals=True,
        include_filings=True,  # Placeholder for now
        include_news=False,
    )

    print(f"✓ Fetched {len(sources)} sources")
    for source in sources:
        print(f"  - {source['type']}: {source['date']}")

    # Initialize orchestrator with sources
    orchestrator = Orchestrator(
        config=config,
        work_dir=work_dir,
        sources=sources,
    )

    print(f"\n{'=' * 80}")
    print("Starting iterative analysis...")
    print(f"{'=' * 80}\n")

    # Run analysis
    try:
        results = await orchestrator.run_analysis(
            ticker=ticker,
            company_name=company_name,
        )

        # Display results
        print(f"\n{'=' * 80}")
        print("ANALYSIS COMPLETE")
        print(f"{'=' * 80}\n")

        print(f"Analysis ID: {results['analysis_id']}")
        print(f"Company: {results['company']} ({results['ticker']})")
        print(f"Iterations: {results['iterations']}")
        print(f"Final Confidence: {results['final_confidence']:.2%}")
        print(f"\nRecommendation: {results['report']['recommendation']['action']}")
        print(f"Conviction: {results['report']['recommendation'].get('conviction', 'N/A')}")

        # Display metrics
        metrics = results.get('metrics', {})
        print(f"\n{'=' * 80}")
        print("PERFORMANCE METRICS")
        print(f"{'=' * 80}")
        print(f"Total Time: {metrics.get('total_time', 0):.1f}s")
        print(f"Total LLM Calls: {metrics.get('total_calls', 0)}")

        # Display evaluation
        evaluation = results.get('evaluation', {})
        print(f"\nQuality Metrics:")
        print(f"  Overall Quality: {evaluation.get('overall_quality', 0):.2f}")
        print(f"  Final Confidence: {evaluation.get('final_confidence', 0):.2%}")

        print(f"\nState saved to: {results['state_dir']}")
        print(f"Trace saved to: {results['trace_path']}")

        # Display executive summary
        report = results['report']
        if 'executive_summary' in report:
            exec_summary = report['executive_summary']
            print(f"\n{'=' * 80}")
            print("EXECUTIVE SUMMARY")
            print(f"{'=' * 80}")
            if isinstance(exec_summary, dict):
                thesis = exec_summary.get('thesis', '')
                print(f"\nThesis:\n{thesis[:500]}...")
            else:
                print(f"\n{exec_summary[:500]}...")

        print(f"\n{'=' * 80}")
        print("Demo complete!")
        print(f"{'=' * 80}\n")

    except Exception as e:
        print(f"\n❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
