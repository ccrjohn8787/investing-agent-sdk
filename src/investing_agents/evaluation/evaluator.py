"""Main evaluation orchestrator for investment reports.

Coordinates quality assessment, benchmarking against real analyst reports,
and automated quality metrics.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import structlog

from investing_agents.evaluation.quality_rubric import (
    OverallQuality,
    QualityRubric,
)

logger = structlog.get_logger(__name__)


class ReportEvaluator:
    """Evaluates investment reports against quality standards."""

    def __init__(
        self,
        rubric: Optional[QualityRubric] = None,
        benchmark_dir: Optional[Path] = None,
    ):
        """Initialize evaluator.

        Args:
            rubric: Quality rubric to use (default: creates new with default weights)
            benchmark_dir: Directory containing benchmark analyst reports
        """
        self.rubric = rubric or QualityRubric()
        self.benchmark_dir = benchmark_dir or Path(__file__).parent / "benchmarks"

        if not self.benchmark_dir.exists():
            logger.warning(
                "evaluator.benchmark_dir_missing",
                path=str(self.benchmark_dir),
            )

    def evaluate_report(self, report: Dict[str, Any]) -> OverallQuality:
        """Evaluate a single report.

        Args:
            report: Investment report to evaluate

        Returns:
            Overall quality assessment
        """
        logger.info("evaluator.evaluate_report_start")

        quality = self.rubric.evaluate(report)

        logger.info(
            "evaluator.evaluate_report_complete",
            total_score=quality.total_score,
            strengths=len(quality.strengths),
            weaknesses=len(quality.weaknesses),
        )

        return quality

    def load_benchmark_report(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Load benchmark analyst report for a ticker.

        Args:
            ticker: Stock ticker

        Returns:
            Benchmark report if found, None otherwise
        """
        benchmark_path = self.benchmark_dir / f"{ticker.upper()}_benchmark.json"

        if not benchmark_path.exists():
            logger.warning(
                "evaluator.benchmark_not_found",
                ticker=ticker,
                path=str(benchmark_path),
            )
            return None

        try:
            with open(benchmark_path) as f:
                benchmark = json.load(f)
                logger.info(
                    "evaluator.benchmark_loaded",
                    ticker=ticker,
                    path=str(benchmark_path),
                )
                return benchmark
        except Exception as e:
            logger.error(
                "evaluator.benchmark_load_error",
                ticker=ticker,
                error=str(e),
            )
            return None

    def compare_with_benchmark(
        self,
        report: Dict[str, Any],
        ticker: str,
    ) -> Dict[str, Any]:
        """Compare generated report with benchmark analyst report.

        Args:
            report: Generated investment report
            ticker: Stock ticker

        Returns:
            Comparison results dictionary
        """
        logger.info("evaluator.compare_start", ticker=ticker)

        # Load benchmark
        benchmark = self.load_benchmark_report(ticker)
        if not benchmark:
            return {
                "benchmark_available": False,
                "message": f"No benchmark report found for {ticker}",
            }

        # Evaluate both reports
        generated_quality = self.evaluate_report(report)
        benchmark_quality = self.evaluate_report(benchmark.get("report", {}))

        # Compare scores
        score_comparison = {
            criterion.value: {
                "generated": generated_quality.criterion_scores[criterion].score,
                "benchmark": benchmark_quality.criterion_scores[criterion].score,
                "delta": generated_quality.criterion_scores[criterion].score
                - benchmark_quality.criterion_scores[criterion].score,
            }
            for criterion in generated_quality.criterion_scores.keys()
        }

        # Overall comparison
        total_delta = generated_quality.total_score - benchmark_quality.total_score

        logger.info(
            "evaluator.compare_complete",
            ticker=ticker,
            generated_score=generated_quality.total_score,
            benchmark_score=benchmark_quality.total_score,
            delta=total_delta,
        )

        return {
            "benchmark_available": True,
            "ticker": ticker,
            "generated_quality": {
                "total_score": generated_quality.total_score,
                "strengths": generated_quality.strengths,
                "weaknesses": generated_quality.weaknesses,
                "recommendations": generated_quality.recommendations,
            },
            "benchmark_quality": {
                "total_score": benchmark_quality.total_score,
                "strengths": benchmark_quality.strengths,
                "weaknesses": benchmark_quality.weaknesses,
            },
            "score_comparison": score_comparison,
            "total_score_delta": total_delta,
            "performance": "better" if total_delta > 0 else "worse" if total_delta < 0 else "equal",
        }

    def evaluate_batch(
        self,
        reports: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Evaluate a batch of reports.

        Args:
            reports: List of investment reports to evaluate

        Returns:
            Batch evaluation results
        """
        logger.info("evaluator.evaluate_batch_start", count=len(reports))

        results = []
        for i, report in enumerate(reports):
            try:
                quality = self.evaluate_report(report)
                results.append(
                    {
                        "report_id": i,
                        "ticker": report.get("ticker", "UNKNOWN"),
                        "total_score": quality.total_score,
                        "quality": quality,
                    }
                )
            except Exception as e:
                logger.error(
                    "evaluator.evaluate_batch_error",
                    report_id=i,
                    error=str(e),
                )
                results.append(
                    {
                        "report_id": i,
                        "ticker": report.get("ticker", "UNKNOWN"),
                        "error": str(e),
                    }
                )

        # Calculate aggregate statistics
        successful_evals = [r for r in results if "total_score" in r]
        if successful_evals:
            avg_score = sum(r["total_score"] for r in successful_evals) / len(successful_evals)
            min_score = min(r["total_score"] for r in successful_evals)
            max_score = max(r["total_score"] for r in successful_evals)
        else:
            avg_score = min_score = max_score = 0.0

        logger.info(
            "evaluator.evaluate_batch_complete",
            total=len(reports),
            successful=len(successful_evals),
            avg_score=avg_score,
        )

        return {
            "total_reports": len(reports),
            "successful_evaluations": len(successful_evals),
            "failed_evaluations": len(reports) - len(successful_evals),
            "aggregate_stats": {
                "average_score": avg_score,
                "min_score": min_score,
                "max_score": max_score,
            },
            "results": results,
        }

    def save_evaluation_results(
        self,
        results: Dict[str, Any],
        output_path: Path,
    ) -> None:
        """Save evaluation results to JSON file.

        Args:
            results: Evaluation results to save
            output_path: Path to output file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(results, indent=2, default=str, fp=f)

        logger.info(
            "evaluator.results_saved",
            path=str(output_path),
        )


class AutomatedQualityMetrics:
    """Automated quality metrics for investment reports."""

    @staticmethod
    def calculate_metrics(report: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate automated quality metrics.

        Args:
            report: Investment report

        Returns:
            Dictionary of automated metrics
        """
        metrics = {}

        # Report completeness (presence of expected sections)
        expected_sections = [
            "executive_summary",
            "recommendation",
            "key_findings",
            "analysis",
            "risks",
        ]
        present_sections = [s for s in expected_sections if s in report]
        metrics["completeness"] = len(present_sections) / len(expected_sections)

        # Content depth (total word count)
        report_text = json.dumps(report)
        word_count = len(report_text.split())
        metrics["word_count"] = word_count
        metrics["depth_score"] = min(word_count / 5000, 1.0)  # Target: 5000+ words

        # Structure score (nested analysis depth)
        def count_depth(obj, current_depth=0, max_depth=0):
            if isinstance(obj, dict):
                for v in obj.values():
                    max_depth = max(max_depth, count_depth(v, current_depth + 1, max_depth))
            elif isinstance(obj, list):
                for item in obj:
                    max_depth = max(max_depth, count_depth(item, current_depth, max_depth))
            return max(current_depth, max_depth)

        structure_depth = count_depth(report)
        metrics["structure_depth"] = structure_depth
        metrics["structure_score"] = min(structure_depth / 5, 1.0)  # Target: depth 5+

        # Data richness (number of sources)
        sources_count = len(report.get("sources_used", []))
        metrics["sources_count"] = sources_count
        metrics["data_richness"] = min(sources_count / 3, 1.0)  # Target: 3+ sources

        # Actionability (has recommendation and conviction)
        has_recommendation = "recommendation" in report
        has_conviction = (
            "recommendation" in report
            and isinstance(report["recommendation"], dict)
            and "conviction" in report["recommendation"]
        )
        metrics["actionability"] = 0.5 if has_recommendation else 0.0
        if has_conviction:
            metrics["actionability"] += 0.5

        # Overall automated score (average of all metrics)
        score_metrics = [
            metrics["completeness"],
            metrics["depth_score"],
            metrics["structure_score"],
            metrics["data_richness"],
            metrics["actionability"],
        ]
        metrics["overall_automated_score"] = sum(score_metrics) / len(score_metrics)

        logger.info(
            "automated_metrics.calculated",
            overall_score=metrics["overall_automated_score"],
            word_count=word_count,
            sources=sources_count,
        )

        return metrics
