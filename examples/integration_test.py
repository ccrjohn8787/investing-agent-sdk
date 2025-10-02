"""Integration test for multi-company analysis.

Tests the full orchestrator pipeline with MSFT and GOOGL to validate:
1. End-to-end analysis works for different companies
2. Data fetching from SEC EDGAR
3. All 5 agents execute successfully
4. Report generation completes
5. Quality evaluation runs
6. Results can be compared
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path

from investing_agents.connectors import SourceManager
from investing_agents.core.orchestrator import Orchestrator, OrchestratorConfig
from investing_agents.evaluation import AutomatedQualityMetrics, ReportEvaluator


async def run_company_analysis(ticker: str, company_name: str, work_dir: Path) -> dict:
    """Run analysis for a single company.

    Args:
        ticker: Stock ticker
        company_name: Company name
        work_dir: Working directory

    Returns:
        Analysis results dictionary
    """
    print(f"\n{'='*80}")
    print(f"ANALYZING: {company_name} ({ticker})")
    print(f"{'='*80}\n")

    # Configure for quick integration test (2 iterations)
    config = OrchestratorConfig(
        max_iterations=2,
        min_iterations=1,
        confidence_threshold=0.80,
        checkpoint_iterations=[1, 2],
        enable_parallel_research=True,
        enable_context_compression=False,  # Not needed for 2 iterations
    )

    # Fetch sources
    print(f"[{ticker}] Fetching data from SEC EDGAR...")
    source_manager = SourceManager()

    try:
        sources = await source_manager.fetch_all_sources(
            ticker=ticker,
            company_name=company_name,
            include_fundamentals=True,
            include_filings=True,
            include_news=False,
        )
        print(f"[{ticker}] ✓ Fetched {len(sources)} sources")
    except Exception as e:
        print(f"[{ticker}] ✗ Error fetching sources: {e}")
        return {
            "ticker": ticker,
            "company": company_name,
            "error": str(e),
            "status": "failed_data_fetch",
        }

    # Run analysis
    print(f"[{ticker}] Starting multi-agent analysis (2 iterations)...")
    company_work_dir = work_dir / ticker.lower()
    company_work_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = Orchestrator(
        config=config,
        work_dir=company_work_dir,
        sources=sources,
    )

    try:
        start_time = datetime.utcnow()
        results = await orchestrator.run_analysis(
            ticker=ticker,
            company_name=company_name,
        )
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        print(f"[{ticker}] ✓ Analysis complete in {duration:.1f}s")
        print(f"[{ticker}]   Iterations: {results['iterations']}")
        print(f"[{ticker}]   Confidence: {results['final_confidence']:.1%}")
        print(f"[{ticker}]   LLM Calls: {results['metrics'].get('total_calls', 0)}")

        results["status"] = "success"
        results["duration_seconds"] = duration
        return results

    except Exception as e:
        print(f"[{ticker}] ✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "ticker": ticker,
            "company": company_name,
            "error": str(e),
            "status": "failed_analysis",
        }


async def evaluate_results(results: dict) -> dict:
    """Evaluate analysis results.

    Args:
        results: Analysis results

    Returns:
        Evaluation results
    """
    ticker = results.get("ticker", "UNKNOWN")

    if results.get("status") != "success":
        print(f"[{ticker}] Skipping evaluation (analysis failed)")
        return {"status": "skipped", "reason": "analysis_failed"}

    print(f"[{ticker}] Evaluating report quality...")

    # Get report from results
    report = results.get("report", {})
    if not report:
        print(f"[{ticker}] ✗ No report found")
        return {"status": "skipped", "reason": "no_report"}

    # Initialize evaluator
    evaluator = ReportEvaluator()

    # Evaluate quality
    quality = evaluator.evaluate_report(report)

    # Calculate automated metrics
    auto_metrics = AutomatedQualityMetrics.calculate_metrics(report)

    # Compare with benchmark if available
    comparison = evaluator.compare_with_benchmark(report, ticker)

    print(f"[{ticker}] Quality Score: {quality.total_score:.2%}")
    print(f"[{ticker}]   Strengths: {len(quality.strengths)}")
    print(f"[{ticker}]   Weaknesses: {len(quality.weaknesses)}")

    if comparison.get("benchmark_available"):
        delta = comparison["total_score_delta"]
        print(f"[{ticker}]   vs Benchmark: {delta:+.1%}")

    return {
        "status": "evaluated",
        "quality_score": quality.total_score,
        "strengths_count": len(quality.strengths),
        "weaknesses_count": len(quality.weaknesses),
        "automated_metrics": auto_metrics,
        "benchmark_comparison": comparison,
    }


async def main():
    """Run integration tests."""
    print("\n" + "="*80)
    print("INTEGRATION TEST: Multi-Company Analysis")
    print("="*80)
    print("\nTesting MSFT and GOOGL with 2 iterations each")
    print("This validates:")
    print("  1. End-to-end pipeline for different companies")
    print("  2. SEC EDGAR data fetching")
    print("  3. All 5 agents execute successfully")
    print("  4. Report generation completes")
    print("  5. Quality evaluation runs")

    # Setup
    work_dir = Path("integration_test_output")
    work_dir.mkdir(parents=True, exist_ok=True)

    # Test companies
    companies = [
        ("MSFT", "Microsoft Corporation"),
        ("GOOGL", "Alphabet Inc."),
    ]

    # Run analyses
    all_results = {}
    all_evaluations = {}

    for ticker, company_name in companies:
        results = await run_company_analysis(ticker, company_name, work_dir)
        all_results[ticker] = results

        # Evaluate if successful
        if results.get("status") == "success":
            evaluation = await evaluate_results(results)
            all_evaluations[ticker] = evaluation

    # Summary
    print("\n" + "="*80)
    print("INTEGRATION TEST SUMMARY")
    print("="*80)

    successful = [t for t, r in all_results.items() if r.get("status") == "success"]
    failed = [t for t, r in all_results.items() if r.get("status") != "success"]

    print(f"\nResults:")
    print(f"  Total Companies: {len(companies)}")
    print(f"  Successful: {len(successful)}")
    print(f"  Failed: {len(failed)}")

    if successful:
        print(f"\n✓ Successful Analyses:")
        for ticker in successful:
            results = all_results[ticker]
            evaluation = all_evaluations.get(ticker, {})

            print(f"\n  {ticker}:")
            print(f"    Duration: {results.get('duration_seconds', 0):.1f}s")
            print(f"    Iterations: {results.get('iterations', 0)}")
            print(f"    Confidence: {results.get('final_confidence', 0):.1%}")
            print(f"    LLM Calls: {results['metrics'].get('total_calls', 0)}")

            if evaluation.get("status") == "evaluated":
                print(f"    Quality Score: {evaluation['quality_score']:.2%}")
                print(f"    Strengths: {evaluation['strengths_count']}")
                print(f"    Weaknesses: {evaluation['weaknesses_count']}")

    if failed:
        print(f"\n✗ Failed Analyses:")
        for ticker in failed:
            results = all_results[ticker]
            print(f"  {ticker}: {results.get('error', 'Unknown error')}")

    # Save results
    summary_file = work_dir / "integration_test_summary.json"
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_companies": len(companies),
        "successful": len(successful),
        "failed": len(failed),
        "companies_tested": companies,
        "results": {
            ticker: {
                "status": results.get("status"),
                "duration_seconds": results.get("duration_seconds"),
                "iterations": results.get("iterations"),
                "confidence": results.get("final_confidence"),
                "quality_score": all_evaluations.get(ticker, {}).get("quality_score"),
                "error": results.get("error"),
            }
            for ticker, results in all_results.items()
        },
    }

    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"\n✓ Summary saved to: {summary_file}")

    # Exit code
    if failed:
        print("\n⚠️  Some analyses failed. Review errors above.")
        return 1
    else:
        print("\n✓ All analyses completed successfully!")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
