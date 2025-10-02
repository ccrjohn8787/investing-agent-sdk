"""Benchmark suite for testing investment analysis quality.

Provides test cases and benchmark reports for evaluating system performance.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from investing_agents.evaluation.evaluator import AutomatedQualityMetrics, ReportEvaluator
from investing_agents.evaluation.quality_rubric import OverallQuality

logger = structlog.get_logger(__name__)


@dataclass
class BenchmarkCase:
    """A benchmark test case."""

    ticker: str
    company_name: str
    expected_min_score: float  # Minimum acceptable quality score
    description: str
    tags: List[str]  # e.g., ["tech", "large-cap", "growth"]


class BenchmarkSuite:
    """Suite of benchmark tests for investment analysis."""

    def __init__(self, benchmark_dir: Optional[Path] = None):
        """Initialize benchmark suite.

        Args:
            benchmark_dir: Directory containing benchmark data
        """
        self.benchmark_dir = benchmark_dir or Path(__file__).parent / "benchmarks"
        self.benchmark_dir.mkdir(parents=True, exist_ok=True)

        self.evaluator = ReportEvaluator(benchmark_dir=self.benchmark_dir)
        self.test_cases = self._load_test_cases()

    def _load_test_cases(self) -> List[BenchmarkCase]:
        """Load benchmark test cases.

        Returns:
            List of benchmark test cases
        """
        # Default test cases
        default_cases = [
            BenchmarkCase(
                ticker="AAPL",
                company_name="Apple Inc.",
                expected_min_score=0.70,
                description="Large-cap tech company with strong fundamentals",
                tags=["tech", "large-cap", "hardware", "services"],
            ),
            BenchmarkCase(
                ticker="MSFT",
                company_name="Microsoft Corporation",
                expected_min_score=0.70,
                description="Large-cap tech company, cloud and software leader",
                tags=["tech", "large-cap", "software", "cloud"],
            ),
            BenchmarkCase(
                ticker="GOOGL",
                company_name="Alphabet Inc.",
                expected_min_score=0.70,
                description="Large-cap tech company, digital advertising leader",
                tags=["tech", "large-cap", "advertising", "cloud"],
            ),
        ]

        # Try to load from file
        cases_file = self.benchmark_dir / "test_cases.json"
        if cases_file.exists():
            try:
                with open(cases_file) as f:
                    data = json.load(f)
                    loaded_cases = [
                        BenchmarkCase(
                            ticker=case["ticker"],
                            company_name=case["company_name"],
                            expected_min_score=case.get("expected_min_score", 0.70),
                            description=case.get("description", ""),
                            tags=case.get("tags", []),
                        )
                        for case in data
                    ]
                    logger.info(
                        "benchmark.test_cases_loaded",
                        count=len(loaded_cases),
                        path=str(cases_file),
                    )
                    return loaded_cases
            except Exception as e:
                logger.error(
                    "benchmark.test_cases_load_error",
                    error=str(e),
                    path=str(cases_file),
                )

        logger.info(
            "benchmark.using_default_cases",
            count=len(default_cases),
        )
        return default_cases

    def save_test_cases(self) -> None:
        """Save test cases to file."""
        cases_file = self.benchmark_dir / "test_cases.json"

        data = [
            {
                "ticker": case.ticker,
                "company_name": case.company_name,
                "expected_min_score": case.expected_min_score,
                "description": case.description,
                "tags": case.tags,
            }
            for case in self.test_cases
        ]

        with open(cases_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(
            "benchmark.test_cases_saved",
            count=len(data),
            path=str(cases_file),
        )

    def add_benchmark_report(
        self,
        ticker: str,
        report: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a benchmark analyst report.

        Args:
            ticker: Stock ticker
            report: Analyst report to use as benchmark
            metadata: Optional metadata about the report
        """
        benchmark_path = self.benchmark_dir / f"{ticker.upper()}_benchmark.json"

        benchmark_data = {
            "ticker": ticker.upper(),
            "report": report,
            "metadata": metadata or {},
            "added_date": "2025-10-01",
        }

        with open(benchmark_path, "w") as f:
            json.dump(benchmark_data, f, indent=2, default=str)

        logger.info(
            "benchmark.report_added",
            ticker=ticker,
            path=str(benchmark_path),
        )

    def run_test_case(
        self,
        test_case: BenchmarkCase,
        generated_report: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run a single benchmark test case.

        Args:
            test_case: Benchmark test case
            generated_report: Generated report to evaluate

        Returns:
            Test results dictionary
        """
        logger.info(
            "benchmark.run_test_case_start",
            ticker=test_case.ticker,
        )

        # Evaluate report
        quality = self.evaluator.evaluate_report(generated_report)

        # Compare with benchmark if available
        comparison = self.evaluator.compare_with_benchmark(
            generated_report,
            test_case.ticker,
        )

        # Check if meets minimum score
        passed = quality.total_score >= test_case.expected_min_score

        result = {
            "test_case": {
                "ticker": test_case.ticker,
                "company_name": test_case.company_name,
                "expected_min_score": test_case.expected_min_score,
                "description": test_case.description,
                "tags": test_case.tags,
            },
            "quality": {
                "total_score": quality.total_score,
                "strengths": quality.strengths,
                "weaknesses": quality.weaknesses,
                "recommendations": quality.recommendations,
            },
            "automated_metrics": AutomatedQualityMetrics.calculate_metrics(generated_report),
            "benchmark_comparison": comparison,
            "passed": passed,
            "pass_threshold": test_case.expected_min_score,
        }

        logger.info(
            "benchmark.run_test_case_complete",
            ticker=test_case.ticker,
            passed=passed,
            score=quality.total_score,
            threshold=test_case.expected_min_score,
        )

        return result

    def run_suite(
        self,
        generated_reports: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Run full benchmark suite.

        Args:
            generated_reports: Dictionary mapping ticker -> generated report

        Returns:
            Suite results dictionary
        """
        logger.info(
            "benchmark.run_suite_start",
            test_cases=len(self.test_cases),
        )

        results = []
        passed_count = 0

        for test_case in self.test_cases:
            ticker = test_case.ticker
            if ticker not in generated_reports:
                logger.warning(
                    "benchmark.report_missing",
                    ticker=ticker,
                )
                results.append(
                    {
                        "test_case": {
                            "ticker": ticker,
                            "company_name": test_case.company_name,
                        },
                        "error": "Report not provided",
                        "passed": False,
                    }
                )
                continue

            generated_report = generated_reports[ticker]
            result = self.run_test_case(test_case, generated_report)
            results.append(result)

            if result["passed"]:
                passed_count += 1

        # Calculate suite statistics
        total_tests = len(self.test_cases)
        pass_rate = passed_count / total_tests if total_tests > 0 else 0.0

        successful_results = [r for r in results if "quality" in r]
        if successful_results:
            avg_score = sum(r["quality"]["total_score"] for r in successful_results) / len(
                successful_results
            )
        else:
            avg_score = 0.0

        suite_results = {
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": total_tests - passed_count,
            "pass_rate": pass_rate,
            "average_score": avg_score,
            "results": results,
        }

        logger.info(
            "benchmark.run_suite_complete",
            total=total_tests,
            passed=passed_count,
            pass_rate=pass_rate,
            avg_score=avg_score,
        )

        return suite_results

    def save_suite_results(
        self,
        results: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """Save suite results to file.

        Args:
            results: Suite results
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        logger.info(
            "benchmark.suite_results_saved",
            path=str(output_path),
        )


def create_sample_benchmark_reports() -> None:
    """Create sample benchmark reports for testing.

    This function creates simplified benchmark reports to demonstrate
    the structure expected for real analyst reports.
    """
    suite = BenchmarkSuite()

    # Sample AAPL benchmark report
    aapl_report = {
        "ticker": "AAPL",
        "company": "Apple Inc.",
        "executive_summary": {
            "thesis": "Apple maintains strong competitive position in consumer hardware "
            "with growing services revenue. Valuation remains elevated but justified by "
            "consistent execution and robust ecosystem."
        },
        "recommendation": {
            "action": "Buy",
            "conviction": "Moderate",
            "target_price": 180.0,
        },
        "key_findings": [
            "Services revenue growing at 15% CAGR, now 20% of total revenue",
            "iPhone remains dominant with 52% market share in premium segment",
            "Operating margins expanding to 30%+ due to services mix shift",
            "$90B+ annual buyback program supports EPS growth",
            "Vision Pro represents new growth vector in spatial computing",
        ],
        "risks": [
            "China exposure (20% of revenue) vulnerable to geopolitical tensions",
            "Regulatory scrutiny on App Store fees and ecosystem lock-in",
            "Hardware upgrade cycles lengthening as innovation slows",
        ],
        "bull_case": "Services revenue accelerates, margins expand, buybacks drive EPS",
        "bear_case": "China weakness, regulatory pressure, slowing hardware cycles",
        "sources_used": ["10-K", "10-Q", "Earnings calls", "Industry reports"],
    }

    suite.add_benchmark_report(
        "AAPL",
        aapl_report,
        metadata={
            "source": "Sample benchmark for testing",
            "quality_level": "institutional",
        },
    )

    # Sample MSFT benchmark report
    msft_report = {
        "ticker": "MSFT",
        "company": "Microsoft Corporation",
        "executive_summary": {
            "thesis": "Microsoft is the clear leader in enterprise cloud and AI, with Azure "
            "growing 30%+ and Copilot driving new revenue streams. Strong competitive moat "
            "and recurring revenue model justify premium valuation."
        },
        "recommendation": {
            "action": "Strong Buy",
            "conviction": "High",
            "target_price": 450.0,
        },
        "key_findings": [
            "Azure revenue growing 30%+ YoY, gaining share vs AWS",
            "Office 365 Copilot early traction with enterprise customers",
            "Gaming division stabilizing post-Activision acquisition",
            "Operating margins above 40% with strong free cash flow",
            "LinkedIn and Dynamics remain underappreciated growth drivers",
        ],
        "risks": [
            "Elevated valuation leaves little room for execution missteps",
            "Dependency on enterprise IT spending cyclicality",
            "Open-source AI models could commoditize AI features",
        ],
        "bull_case": "AI monetization exceeds expectations, Azure share gains accelerate",
        "bear_case": "Enterprise spending slowdown, AI commoditization pressure",
        "sources_used": ["10-K", "10-Q", "Azure growth reports", "Industry surveys"],
    }

    suite.add_benchmark_report(
        "MSFT",
        msft_report,
        metadata={
            "source": "Sample benchmark for testing",
            "quality_level": "institutional",
        },
    )

    logger.info("benchmark.sample_reports_created", count=2)
