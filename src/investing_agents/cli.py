"""Command-line interface for investment analysis.

Usage:
    investing-agents analyze AAPL
    investing-agents analyze AAPL --iterations 5
    investing-agents analyze AAPL --format json --output report.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from investing_agents.connectors import SourceManager
from investing_agents.core.orchestrator import Orchestrator, OrchestratorConfig
from investing_agents.evaluation.pm_evaluator import PMEvaluator
from investing_agents.monitoring import ConsoleUI
from investing_agents.output import HTMLReportGenerator
from investing_agents.utils.logging_config import LogLevel, configure_logging


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser.

    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        prog="investing-agents",
        description="Generate institutional-grade equity research reports using multi-agent AI",
        epilog="For more information, visit: https://github.com/chaorong/investing-agent-sdk",
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Analyze command
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Analyze a company and generate investment report",
    )
    analyze_parser.add_argument(
        "ticker",
        type=str,
        help="Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)",
    )
    analyze_parser.add_argument(
        "--company",
        type=str,
        help="Company name (auto-detected from ticker if not provided)",
    )
    analyze_parser.add_argument(
        "--iterations",
        type=int,
        default=3,
        help="Maximum number of iterations (default: 3)",
    )
    analyze_parser.add_argument(
        "--confidence",
        type=float,
        default=0.85,
        help="Confidence threshold for stopping (default: 0.85)",
    )
    analyze_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (default: stdout)",
    )
    analyze_parser.add_argument(
        "--format",
        "-f",
        type=str,
        choices=["text", "json", "markdown", "html"],
        default="text",
        help="Output format (default: text)",
    )
    analyze_parser.add_argument(
        "--work-dir",
        type=str,
        help="Working directory for state/logs (default: temp directory)",
    )
    analyze_parser.add_argument(
        "--no-parallel",
        action="store_true",
        help="Disable parallel research (slower but uses less resources)",
    )
    analyze_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging (very verbose)",
    )
    analyze_parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )
    analyze_parser.add_argument(
        "--log-file",
        type=str,
        help="Log to file in addition to console",
    )
    analyze_parser.add_argument(
        "--no-rich-ui",
        action="store_true",
        help="Disable rich console UI (enabled by default)",
    )
    analyze_parser.add_argument(
        "--fast-mode",
        action="store_true",
        help="Enable fast mode: fewer web searches, no deep-dive (2-3x faster, 70%% quality)",
    )

    return parser


async def run_analysis(args: argparse.Namespace) -> dict:
    """Run investment analysis.

    Args:
        args: Parsed command-line arguments

    Returns:
        Analysis results dictionary
    """
    # Configure logging
    log_level = LogLevel.INFO
    if args.debug:
        log_level = LogLevel.DEBUG
    elif args.verbose:
        log_level = LogLevel.INFO  # Already default, but explicit

    log_file = Path(args.log_file) if args.log_file else None

    configure_logging(
        level=log_level,
        debug_mode=args.debug,
        log_file=log_file,
        enable_colors=True,
    )

    # Configuration
    if args.fast_mode:
        # Fast mode: 2-3x faster, ~70% quality
        config = OrchestratorConfig(
            max_iterations=args.iterations,
            confidence_threshold=args.confidence,
            checkpoint_iterations=[i for i in range(1, args.iterations + 1)],
            min_iterations=1,
            top_n_hypotheses_for_synthesis=1,  # Minimal synthesis
            enable_parallel_research=not args.no_parallel,
            # Speed optimizations
            web_research_questions_per_hypothesis=2,  # Down from 4 (50% fewer searches)
            web_research_results_per_query=5,          # Down from 8
            enable_deep_dive=False,                    # No Round 2 deep-dive
        )
    else:
        # Normal mode: full quality
        config = OrchestratorConfig(
            max_iterations=args.iterations,
            confidence_threshold=args.confidence,
            checkpoint_iterations=[i for i in range(1, args.iterations + 1)],
            min_iterations=1,
            top_n_hypotheses_for_synthesis=2,
            enable_parallel_research=not args.no_parallel,
        )

    # Work directory
    if args.work_dir:
        work_dir = Path(args.work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
    else:
        import tempfile

        work_dir = Path(tempfile.mkdtemp())

    # Determine if Rich UI should be used (enabled by default unless --no-rich-ui)
    use_rich_ui = not args.no_rich_ui

    if not use_rich_ui:
        print(f"\nAnalyzing {args.ticker}...", file=sys.stderr)
        print(f"Work directory: {work_dir}\n", file=sys.stderr)

    # Fetch sources
    if not use_rich_ui:
        print("Fetching data from SEC EDGAR...", file=sys.stderr)

    source_manager = SourceManager()

    # Determine company name
    company_name = args.company or f"{args.ticker} Inc."

    sources = await source_manager.fetch_all_sources(
        ticker=args.ticker,
        company_name=company_name,
        include_fundamentals=True,
        include_filings=True,
        include_news=False,
    )

    if not use_rich_ui:
        print(f"✓ Fetched {len(sources)} sources\n", file=sys.stderr)

    # Initialize orchestrator
    orchestrator = Orchestrator(
        config=config,
        work_dir=work_dir,
        sources=sources,
    )

    # Initialize Rich Console UI if enabled
    console_ui = None
    if use_rich_ui:
        console_ui = ConsoleUI(orchestrator.progress)
        console_ui.start(ticker=args.ticker, company=company_name)
        # Attach UI to orchestrator for updates
        orchestrator.console_ui = console_ui

    try:
        # Run analysis
        if not use_rich_ui:
            print("Running multi-agent analysis...\n", file=sys.stderr)

        results = await orchestrator.run_analysis(
            ticker=args.ticker,
            company_name=company_name,
        )

        if not use_rich_ui:
            print(f"\n✓ Analysis complete!\n", file=sys.stderr)

    finally:
        # Stop Rich UI if it was started
        if console_ui:
            console_ui.stop()
            # Print completion message after UI stops
            print(f"\n✓ Analysis complete!\n", file=sys.stderr)

    # Display PM evaluation results
    pm_eval = results.get("pm_evaluation", {})
    if pm_eval:
        print("\n" + "=" * 60, file=sys.stderr)
        print("📊 PM EVALUATION RESULTS", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"Grade: {pm_eval.get('overall_grade', 'N/A')}", file=sys.stderr)
        print(f"Score: {pm_eval.get('overall_score', 0)}/100", file=sys.stderr)
        print(f"\nEvaluation saved to:", file=sys.stderr)
        print(f"  {work_dir}/evaluation/pm_evaluation.md", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

    return results


def format_text_output(results: dict) -> str:
    """Format results as human-readable text.

    Args:
        results: Analysis results

    Returns:
        Formatted text string
    """
    lines = []

    # Header
    lines.append("=" * 80)
    lines.append(f"INVESTMENT ANALYSIS: {results['company']} ({results['ticker']})")
    lines.append("=" * 80)
    lines.append("")

    # Recommendation
    report = results["report"]
    recommendation = report["recommendation"]
    lines.append(f"RECOMMENDATION: {recommendation['action']}")
    lines.append(f"Conviction: {recommendation.get('conviction', 'N/A')}")
    lines.append("")

    # Executive Summary
    if "executive_summary" in report:
        lines.append("EXECUTIVE SUMMARY")
        lines.append("-" * 80)
        exec_summary = report["executive_summary"]
        if isinstance(exec_summary, dict):
            thesis = exec_summary.get("thesis", "")
            lines.append(thesis)
        else:
            lines.append(str(exec_summary))
        lines.append("")

    # Key Findings
    if "key_findings" in report and report["key_findings"]:
        lines.append("KEY FINDINGS")
        lines.append("-" * 80)
        for i, finding in enumerate(report["key_findings"][:5], 1):
            lines.append(f"{i}. {finding}")
        lines.append("")

    # Metrics
    metrics = results.get("metrics", {})
    lines.append("PERFORMANCE METRICS")
    lines.append("-" * 80)
    lines.append(f"Total Time: {metrics.get('total_time', 0):.1f}s")
    lines.append(f"Total LLM Calls: {metrics.get('total_calls', 0)}")
    lines.append(f"Iterations: {results['iterations']}")
    lines.append(f"Final Confidence: {results['final_confidence']:.1%}")
    lines.append("")

    # Evaluation
    evaluation = results.get("evaluation", {})
    lines.append(f"Overall Quality: {evaluation.get('overall_quality', 0):.2f}/1.0")
    lines.append("")

    # Footer
    lines.append("=" * 80)
    lines.append(f"State saved to: {results['state_dir']}")
    lines.append(f"Trace saved to: {results.get('trace_path', 'N/A')}")
    lines.append("=" * 80)

    return "\n".join(lines)


def format_markdown_output(results: dict) -> str:
    """Format results as Markdown.

    Args:
        results: Analysis results

    Returns:
        Formatted Markdown string
    """
    lines = []

    # Header
    lines.append(f"# Investment Analysis: {results['company']} ({results['ticker']})")
    lines.append("")

    # Recommendation
    report = results["report"]
    recommendation = report["recommendation"]
    lines.append("## Recommendation")
    lines.append("")
    lines.append(f"**Action:** {recommendation['action']}")
    lines.append(f"**Conviction:** {recommendation.get('conviction', 'N/A')}")
    lines.append("")

    # Executive Summary
    if "executive_summary" in report:
        lines.append("## Executive Summary")
        lines.append("")
        exec_summary = report["executive_summary"]
        if isinstance(exec_summary, dict):
            thesis = exec_summary.get("thesis", "")
            lines.append(thesis)
        else:
            lines.append(str(exec_summary))
        lines.append("")

    # Key Findings
    if "key_findings" in report and report["key_findings"]:
        lines.append("## Key Findings")
        lines.append("")
        for finding in report["key_findings"][:5]:
            lines.append(f"- {finding}")
        lines.append("")

    # Metrics
    metrics = results.get("metrics", {})
    evaluation = results.get("evaluation", {})
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- **Total Time:** {metrics.get('total_time', 0):.1f}s")
    lines.append(f"- **Total LLM Calls:** {metrics.get('total_calls', 0)}")
    lines.append(f"- **Iterations:** {results['iterations']}")
    lines.append(f"- **Final Confidence:** {results['final_confidence']:.1%}")
    lines.append(f"- **Overall Quality:** {evaluation.get('overall_quality', 0):.2f}/1.0")
    lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(f"*State saved to: `{results['state_dir']}`*")
    lines.append(f"*Trace saved to: `{results.get('trace_path', 'N/A')}`*")

    return "\n".join(lines)


def main() -> int:
    """Main CLI entry point.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "analyze":
        try:
            # Run analysis
            results = asyncio.run(run_analysis(args))

            # Format output
            if args.format == "json":
                output = json.dumps(results, indent=2, default=str)
            elif args.format == "markdown":
                output = format_markdown_output(results)
            elif args.format == "html":
                html_gen = HTMLReportGenerator()
                output = html_gen.generate(
                    report=results.get("report", {}),
                    valuation=results.get("valuation"),
                    ticker=results.get("ticker", ""),
                    company=results.get("company", ""),
                )
            else:  # text
                output = format_text_output(results)

            # Write output
            if args.output:
                output_path = Path(args.output)
                output_path.write_text(output)
                print(f"Report saved to: {output_path}", file=sys.stderr)
            else:
                print(output)

            return 0

        except KeyboardInterrupt:
            print("\n\nAnalysis interrupted by user", file=sys.stderr)
            return 1

        except Exception as e:
            print(f"\n\nError: {e}", file=sys.stderr)
            import traceback

            traceback.print_exc(file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
