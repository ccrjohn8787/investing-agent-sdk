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

from investing_agents.connectors import SourceManager
from investing_agents.core.orchestrator import Orchestrator, OrchestratorConfig


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
        choices=["text", "json", "markdown"],
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

    return parser


async def run_analysis(args: argparse.Namespace) -> dict:
    """Run investment analysis.

    Args:
        args: Parsed command-line arguments

    Returns:
        Analysis results dictionary
    """
    # Configuration
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

    print(f"\nAnalyzing {args.ticker}...", file=sys.stderr)
    print(f"Work directory: {work_dir}\n", file=sys.stderr)

    # Fetch sources
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

    print(f"✓ Fetched {len(sources)} sources\n", file=sys.stderr)

    # Initialize orchestrator
    orchestrator = Orchestrator(
        config=config,
        work_dir=work_dir,
        sources=sources,
    )

    # Run analysis
    print("Running multi-agent analysis...\n", file=sys.stderr)
    results = await orchestrator.run_analysis(
        ticker=args.ticker,
        company_name=company_name,
    )

    print(f"\n✓ Analysis complete!\n", file=sys.stderr)

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
