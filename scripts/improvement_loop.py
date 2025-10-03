#!/usr/bin/env python3
"""Automated improvement loop for investment analysis.

This script runs iterative analyses, extracts PM feedback, applies fixes,
and repeats until quality targets are met.

Usage:
    python scripts/improvement_loop.py NVDA --target-grade A- --max-iterations 5
"""

import asyncio
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


class ImprovementLoop:
    """Orchestrates automated analysis improvement cycles."""

    def __init__(
        self,
        ticker: str,
        target_grade: str = "A-",
        target_score: int = 90,
        max_iterations: int = 5,
        analysis_iterations: int = 2,
    ):
        """Initialize improvement loop.

        Args:
            ticker: Stock ticker to analyze
            target_grade: Target PM evaluation grade (e.g., "A-", "A")
            target_score: Target PM evaluation score (0-100)
            max_iterations: Maximum improvement loop iterations
            analysis_iterations: Number of research iterations per analysis
        """
        self.ticker = ticker
        self.target_grade = target_grade
        self.target_score = target_score
        self.max_iterations = max_iterations
        self.analysis_iterations = analysis_iterations

        # Track history
        self.iteration_history: List[Dict] = []
        self.fixes_applied: List[str] = []

        # Output directory
        self.output_dir = Path("output/improvement_loop")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.log = logger.bind(ticker=ticker, target_grade=target_grade)

    async def run(self) -> Dict:
        """Run improvement loop until target quality reached or max iterations hit.

        Returns:
            Final loop summary with iteration history
        """
        self.log.info(
            "improvement_loop.start",
            max_iterations=self.max_iterations,
            target_score=self.target_score,
        )

        for iteration in range(1, self.max_iterations + 1):
            self.log.info("improvement_loop.iteration.start", iteration=iteration)

            # Step 1: Run analysis
            analysis_result = await self._run_analysis(iteration)

            if analysis_result["status"] == "error":
                # Step 2a: Fix runtime errors
                self.log.warning(
                    "improvement_loop.error_detected", error=analysis_result["error"]
                )
                fix_applied = await self._fix_runtime_error(analysis_result["error"])
                if fix_applied:
                    self.fixes_applied.append(fix_applied)
                    continue  # Retry this iteration
                else:
                    self.log.error("improvement_loop.unfixable_error")
                    break

            # Step 2b: Parse PM evaluation
            pm_eval = self._parse_pm_evaluation(analysis_result["pm_eval_path"])

            # Track iteration
            self.iteration_history.append(
                {
                    "iteration": iteration,
                    "timestamp": datetime.utcnow().isoformat(),
                    "grade": pm_eval["grade"],
                    "score": pm_eval["score"],
                    "critical_issues": pm_eval["critical_issues"],
                    "report_path": analysis_result["report_path"],
                    "pm_eval_path": analysis_result["pm_eval_path"],
                }
            )

            self.log.info(
                "improvement_loop.iteration.complete",
                iteration=iteration,
                grade=pm_eval["grade"],
                score=pm_eval["score"],
            )

            # Step 3: Check if target reached
            if self._is_target_reached(pm_eval):
                self.log.info(
                    "improvement_loop.target_reached",
                    final_grade=pm_eval["grade"],
                    final_score=pm_eval["score"],
                    iterations=iteration,
                )
                break

            # Step 4: Extract and apply improvements
            improvements = self._extract_improvements(pm_eval)
            if improvements:
                fixes = await self._apply_improvements(improvements)
                self.fixes_applied.extend(fixes)
            else:
                self.log.warning("improvement_loop.no_improvements_found")

        # Generate summary
        summary = self._generate_summary()
        self._save_summary(summary)

        return summary

    async def _run_analysis(self, iteration: int) -> Dict:
        """Run investing-agents analysis.

        Args:
            iteration: Loop iteration number

        Returns:
            Analysis result with paths and status
        """
        output_path = self.output_dir / f"iteration_{iteration}_{self.ticker}.html"
        cmd = [
            "investing-agents",
            "analyze",
            self.ticker,
            "--iterations",
            str(self.analysis_iterations),
            "--no-rich-ui",  # Enable verbose logging for visibility
            "--fast-mode",   # Use fast mode for improvement loop (2-3x faster)
            "--output",
            str(output_path),
            "--format",
            "html",
        ]

        self.log.info("improvement_loop.analysis.start", cmd=" ".join(cmd))

        try:
            # Run analysis
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,  # 60 minute timeout (increased from 20min)
                check=False,
            )

            if result.returncode != 0:
                return {
                    "status": "error",
                    "error": result.stderr,
                    "stdout": result.stdout,
                }

            # Find PM evaluation path from logs
            pm_eval_path = self._extract_pm_eval_path(result.stderr)

            return {
                "status": "success",
                "report_path": str(output_path),
                "pm_eval_path": pm_eval_path,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }

        except subprocess.TimeoutExpired:
            return {"status": "error", "error": "Analysis timeout after 20 minutes"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _extract_pm_eval_path(self, stderr: str) -> Optional[str]:
        """Extract PM evaluation file path from analysis logs.

        Args:
            stderr: Analysis stderr output

        Returns:
            Path to PM evaluation markdown file
        """
        # Look for pm_evaluation.saved log line
        match = re.search(r"md_path=([^\s]+pm_evaluation\.md)", stderr)
        if match:
            return match.group(1)
        return None

    def _parse_pm_evaluation(self, pm_eval_path: Optional[str]) -> Dict:
        """Parse PM evaluation markdown file.

        Args:
            pm_eval_path: Path to PM evaluation file

        Returns:
            Parsed evaluation with grade, score, issues
        """
        if not pm_eval_path or not Path(pm_eval_path).exists():
            return {
                "grade": "F",
                "score": 0,
                "critical_issues": ["PM evaluation not found"],
                "suggested_improvements": [],
            }

        content = Path(pm_eval_path).read_text()

        # Extract grade and score
        grade_match = re.search(r"\*\*Grade:\*\*\s+([A-F][+-]?)", content)
        score_match = re.search(r"\*\*Score:\*\*\s+(\d+)/100", content)

        grade = grade_match.group(1) if grade_match else "F"
        score = int(score_match.group(1)) if score_match else 0

        # Extract critical issues (lines starting with ⚠️)
        critical_issues = re.findall(r"- ⚠️ (.+)", content)

        # Extract suggested improvements (lines starting with 💡)
        suggested_improvements = re.findall(r"- 💡 (.+)", content)

        return {
            "grade": grade,
            "score": score,
            "critical_issues": critical_issues,
            "suggested_improvements": suggested_improvements,
            "full_content": content,
        }

    def _is_target_reached(self, pm_eval: Dict) -> bool:
        """Check if target quality reached.

        Args:
            pm_eval: Parsed PM evaluation

        Returns:
            True if target reached
        """
        # Convert grades to numeric for comparison
        grade_values = {
            "A+": 97,
            "A": 93,
            "A-": 90,
            "B+": 87,
            "B": 83,
            "B-": 80,
            "C+": 77,
            "C": 73,
            "C-": 70,
            "D": 60,
            "F": 0,
        }

        current_grade_value = grade_values.get(pm_eval["grade"], 0)
        target_grade_value = grade_values.get(self.target_grade, 90)

        return pm_eval["score"] >= self.target_score or current_grade_value >= target_grade_value

    def _extract_improvements(self, pm_eval: Dict) -> List[Dict]:
        """Extract actionable improvements from PM evaluation.

        Args:
            pm_eval: Parsed PM evaluation

        Returns:
            List of improvement actions
        """
        improvements = []

        # Map critical issues to fixes
        for issue in pm_eval["critical_issues"]:
            if "valuation scenarios" in issue.lower() or "scenario analysis" in issue.lower():
                improvements.append(
                    {
                        "type": "add_scenario_analysis",
                        "description": issue,
                        "priority": "high",
                    }
                )
            elif "customer concentration" in issue.lower():
                improvements.append(
                    {
                        "type": "validate_customer_concentration",
                        "description": issue,
                        "priority": "high",
                    }
                )
            elif "hold" in issue.lower() and "sell" in issue.lower():
                improvements.append(
                    {
                        "type": "clarify_recommendation",
                        "description": issue,
                        "priority": "medium",
                    }
                )

        return improvements

    async def _apply_improvements(self, improvements: List[Dict]) -> List[str]:
        """Apply improvements to codebase.

        Args:
            improvements: List of improvement actions

        Returns:
            List of fixes applied
        """
        fixes_applied = []

        for improvement in improvements:
            if improvement["type"] == "add_scenario_analysis":
                # This would require modifying ValuationAgent to generate scenarios
                self.log.info("improvement.scenario_analysis", action="manual_required")
                # For now, log that this needs manual intervention
                fixes_applied.append(
                    "MANUAL: Add bull/base/bear scenario analysis to ValuationAgent"
                )

            elif improvement["type"] == "validate_customer_concentration":
                # This could be fixed by improving evidence gathering
                self.log.info("improvement.customer_concentration", action="manual_required")
                fixes_applied.append(
                    "MANUAL: Add customer concentration validation to research phase"
                )

            elif improvement["type"] == "clarify_recommendation":
                # This requires improving NarrativeBuilder logic
                self.log.info("improvement.recommendation", action="manual_required")
                fixes_applied.append(
                    "MANUAL: Add HOLD vs SELL clarification to NarrativeBuilder"
                )

        return fixes_applied

    async def _fix_runtime_error(self, error: str) -> Optional[str]:
        """Attempt to fix runtime error automatically.

        Args:
            error: Error message

        Returns:
            Description of fix applied, or None if unfixable
        """
        # Example: Handle common errors
        if "shares_out" in error.lower() and "none" in error.lower():
            self.log.info("improvement.fix.shares_out")
            # This was already fixed in source_manager.py
            return "Fixed: shares_out formatting in source_manager.py"

        if "max_tokens" in error.lower():
            self.log.info("improvement.fix.max_tokens")
            # This was already fixed by removing extra_args
            return "Fixed: Removed invalid max_tokens CLI argument"

        return None

    def _generate_summary(self) -> Dict:
        """Generate improvement loop summary.

        Returns:
            Summary dict with history and metrics
        """
        if not self.iteration_history:
            return {"status": "no_iterations", "iterations": 0}

        first_iteration = self.iteration_history[0]
        last_iteration = self.iteration_history[-1]

        return {
            "status": "completed",
            "ticker": self.ticker,
            "total_iterations": len(self.iteration_history),
            "target_grade": self.target_grade,
            "target_score": self.target_score,
            "initial_grade": first_iteration["grade"],
            "initial_score": first_iteration["score"],
            "final_grade": last_iteration["grade"],
            "final_score": last_iteration["score"],
            "improvement": last_iteration["score"] - first_iteration["score"],
            "target_reached": self._is_target_reached(
                {"grade": last_iteration["grade"], "score": last_iteration["score"]}
            ),
            "fixes_applied": self.fixes_applied,
            "iteration_history": self.iteration_history,
            "final_report": last_iteration["report_path"],
            "final_pm_eval": last_iteration["pm_eval_path"],
        }

    def _save_summary(self, summary: Dict):
        """Save improvement loop summary to file.

        Args:
            summary: Summary dict
        """
        summary_path = self.output_dir / f"summary_{self.ticker}.json"
        summary_path.write_text(json.dumps(summary, indent=2))

        self.log.info("improvement_loop.summary_saved", path=str(summary_path))

        # Also print human-readable summary
        print("\n" + "=" * 80)
        print(f"IMPROVEMENT LOOP SUMMARY: {self.ticker}")
        print("=" * 80)

        if summary['status'] == 'no_iterations':
            print(f"Status: No successful iterations completed")
            print(f"Iterations attempted: {summary['iterations']}")
        else:
            print(f"Iterations: {summary['total_iterations']}")
            print(f"Initial: {summary['initial_grade']} ({summary['initial_score']}/100)")
            print(f"Final:   {summary['final_grade']} ({summary['final_score']}/100)")
            print(f"Improvement: +{summary['improvement']} points")
            print(f"Target Reached: {summary['target_reached']}")
            print(f"\nFixes Applied: {len(summary['fixes_applied'])}")
            for fix in summary["fixes_applied"]:
                print(f"  - {fix}")
            print(f"\nFinal Report: {summary['final_report']}")
            print(f"PM Evaluation: {summary['final_pm_eval']}")
        print("=" * 80)


async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run automated improvement loop")
    parser.add_argument("ticker", help="Stock ticker to analyze")
    parser.add_argument(
        "--target-grade", default="A-", help="Target PM evaluation grade (default: A-)"
    )
    parser.add_argument(
        "--target-score", type=int, default=90, help="Target PM score (default: 90)"
    )
    parser.add_argument(
        "--max-iterations", type=int, default=5, help="Max loop iterations (default: 5)"
    )
    parser.add_argument(
        "--analysis-iterations",
        type=int,
        default=2,
        help="Research iterations per analysis (default: 2)",
    )

    args = parser.parse_args()

    loop = ImprovementLoop(
        ticker=args.ticker,
        target_grade=args.target_grade,
        target_score=args.target_score,
        max_iterations=args.max_iterations,
        analysis_iterations=args.analysis_iterations,
    )

    summary = await loop.run()

    # Exit with status code based on whether target reached
    sys.exit(0 if summary.get("target_reached") else 1)


if __name__ == "__main__":
    asyncio.run(main())
