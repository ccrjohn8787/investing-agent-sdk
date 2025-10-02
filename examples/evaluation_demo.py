"""Demonstration of the evaluation framework.

Shows how to:
1. Evaluate report quality using the quality rubric
2. Compare against benchmark analyst reports
3. Run the benchmark suite
"""

import asyncio
import json
from pathlib import Path

from investing_agents.evaluation import (
    AutomatedQualityMetrics,
    BenchmarkSuite,
    ReportEvaluator,
)


async def demo_quality_evaluation():
    """Demonstrate quality evaluation of a generated report."""
    print("=" * 80)
    print("DEMO 1: Quality Evaluation")
    print("=" * 80)

    # Sample generated report (simplified for demo)
    sample_report = {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "executive_summary": {
            "thesis": "Apple maintains strong competitive position with growing services "
            "revenue and robust ecosystem. Hardware upgrade cycles provide predictable "
            "revenue base while services expansion drives margin improvement."
        },
        "recommendation": {
            "action": "Buy",
            "conviction": "Moderate",
        },
        "key_findings": [
            "Services revenue growing 15% YoY, now 20% of total revenue",
            "iPhone market share remains dominant at 52% in premium segment",
            "Operating margins expanding due to services mix",
            "$90B+ annual buyback program supports EPS growth",
        ],
        "analysis": {
            "revenue_growth": "Historical 8-10% CAGR, expecting 7-9% forward",
            "margin_profile": "Gross margins 42%, operating margins 30%",
            "competitive_position": "Strong moat from ecosystem lock-in",
        },
        "risks": [
            "China exposure (~20% revenue) vulnerable to geopolitics",
            "Regulatory scrutiny on App Store fees",
            "Hardware upgrade cycles lengthening",
        ],
        "sources_used": ["10-K", "10-Q", "Earnings calls"],
    }

    # Initialize evaluator
    evaluator = ReportEvaluator()

    # Evaluate the report
    quality = evaluator.evaluate_report(sample_report)

    # Display results
    print(f"\nOverall Quality Score: {quality.total_score:.2%}\n")

    print("Criterion Scores:")
    for criterion, score in quality.criterion_scores.items():
        print(f"  {criterion.value:25s}: {score.score:.2%}  - {score.reasoning}")

    print(f"\nStrengths ({len(quality.strengths)}):")
    for strength in quality.strengths[:3]:
        print(f"  + {strength}")

    print(f"\nWeaknesses ({len(quality.weaknesses)}):")
    for weakness in quality.weaknesses[:3]:
        print(f"  - {weakness}")

    print(f"\nRecommendations ({len(quality.recommendations)}):")
    for rec in quality.recommendations[:3]:
        print(f"  → {rec}")

    # Automated metrics
    print("\n" + "-" * 80)
    print("Automated Quality Metrics:")
    print("-" * 80)

    metrics = AutomatedQualityMetrics.calculate_metrics(sample_report)
    print(f"  Completeness:       {metrics['completeness']:.2%}")
    print(f"  Depth Score:        {metrics['depth_score']:.2%}")
    print(f"  Structure Score:    {metrics['structure_score']:.2%}")
    print(f"  Data Richness:      {metrics['data_richness']:.2%}")
    print(f"  Actionability:      {metrics['actionability']:.2%}")
    print(f"  Overall Automated:  {metrics['overall_automated_score']:.2%}")


async def demo_benchmark_comparison():
    """Demonstrate comparison with benchmark analyst reports."""
    print("\n\n" + "=" * 80)
    print("DEMO 2: Benchmark Comparison")
    print("=" * 80)

    # Sample generated report
    sample_report = {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "executive_summary": {
            "thesis": "Strong fundamentals with services growth driving margin expansion."
        },
        "recommendation": {"action": "Buy", "conviction": "Moderate"},
        "key_findings": [
            "Services revenue at 15% growth",
            "iPhone dominance in premium",
            "Strong buyback program",
        ],
        "analysis": {"revenue": "Growing steadily"},
        "risks": ["China exposure", "Regulatory pressure"],
        "sources_used": ["10-K", "10-Q"],
    }

    # Initialize evaluator
    evaluator = ReportEvaluator()

    # Compare with benchmark (AAPL benchmark was created in benchmark setup)
    comparison = evaluator.compare_with_benchmark(sample_report, "AAPL")

    if comparison["benchmark_available"]:
        print(f"\nTicker: {comparison['ticker']}")
        print(f"Performance vs Benchmark: {comparison['performance'].upper()}")
        print(f"Score Delta: {comparison['total_score_delta']:+.2%}\n")

        print("Detailed Comparison:")
        print(f"{'Criterion':<30s} {'Generated':>12s} {'Benchmark':>12s} {'Delta':>12s}")
        print("-" * 70)

        for criterion, scores in comparison["score_comparison"].items():
            print(
                f"{criterion:<30s} "
                f"{scores['generated']:>11.2%} "
                f"{scores['benchmark']:>11.2%} "
                f"{scores['delta']:>+11.2%}"
            )

        print("\nGenerated Report Quality:")
        gen_quality = comparison["generated_quality"]
        print(f"  Total Score: {gen_quality['total_score']:.2%}")
        print(f"  Strengths: {len(gen_quality['strengths'])}")
        print(f"  Weaknesses: {len(gen_quality['weaknesses'])}")

        print("\nBenchmark Report Quality:")
        bench_quality = comparison["benchmark_quality"]
        print(f"  Total Score: {bench_quality['total_score']:.2%}")
        print(f"  Strengths: {len(bench_quality['strengths'])}")
    else:
        print(f"\n{comparison['message']}")


async def demo_benchmark_suite():
    """Demonstrate running the benchmark test suite."""
    print("\n\n" + "=" * 80)
    print("DEMO 3: Benchmark Suite")
    print("=" * 80)

    # Initialize benchmark suite
    suite = BenchmarkSuite()

    print(f"\nLoaded {len(suite.test_cases)} test cases:")
    for case in suite.test_cases:
        print(f"  - {case.ticker}: {case.description}")
        print(f"    Tags: {', '.join(case.tags)}")
        print(f"    Min Score: {case.expected_min_score:.0%}")

    # For demo, create mock reports for all test cases
    mock_reports = {}
    for case in suite.test_cases:
        mock_reports[case.ticker] = {
            "ticker": case.ticker,
            "company": case.company_name,
            "executive_summary": {
                "thesis": f"Investment thesis for {case.company_name}"
            },
            "recommendation": {"action": "Hold", "conviction": "Moderate"},
            "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
            "analysis": {"competitive_position": "Strong"},
            "risks": ["Risk 1", "Risk 2"],
            "sources_used": ["10-K", "10-Q"],
        }

    # Run the suite (mock for demo - real run would use actual generated reports)
    print("\n" + "-" * 80)
    print("Running Benchmark Suite (mock)...")
    print("-" * 80)

    results = suite.run_suite(mock_reports)

    print(f"\nSuite Results:")
    print(f"  Total Tests:   {results['total_tests']}")
    print(f"  Passed:        {results['passed']}")
    print(f"  Failed:        {results['failed']}")
    print(f"  Pass Rate:     {results['pass_rate']:.1%}")
    print(f"  Average Score: {results['average_score']:.2%}")

    print(f"\nIndividual Test Results:")
    for result in results["results"]:
        if "quality" in result:
            ticker = result["test_case"]["ticker"]
            passed = "✓" if result["passed"] else "✗"
            score = result["quality"]["total_score"]
            threshold = result["pass_threshold"]
            print(f"  {passed} {ticker:<6s}: {score:.2%} (threshold: {threshold:.0%})")


async def main():
    """Run all evaluation demos."""
    print("\n" + "=" * 80)
    print("INVESTMENT ANALYSIS EVALUATION FRAMEWORK DEMO")
    print("=" * 80)

    # Run demos
    await demo_quality_evaluation()
    await demo_benchmark_comparison()
    await demo_benchmark_suite()

    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nThe evaluation framework provides:")
    print("  1. Quality rubric with 8 criteria for assessing report quality")
    print("  2. Benchmark comparison against real analyst reports")
    print("  3. Automated quality metrics (completeness, depth, structure)")
    print("  4. Benchmark test suite for regression testing")
    print("\nUse this framework to:")
    print("  - Evaluate generated reports for quality")
    print("  - Compare against human-written analyst reports")
    print("  - Track quality improvements over time")
    print("  - Identify areas for prompt tuning")


if __name__ == "__main__":
    asyncio.run(main())
