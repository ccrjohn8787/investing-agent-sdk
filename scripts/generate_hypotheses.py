"""Generate investment hypotheses for a ticker.

This standalone script generates hypotheses that can be used for web research.
Run this first to get hypotheses, then ask Claude Code to research them.

Usage:
    python scripts/generate_hypotheses.py NVDA --company "NVIDIA Corporation"
"""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from investing_agents.agents.hypothesis_generator import HypothesisGeneratorAgent
from investing_agents.connectors.source_manager import SourceManager


async def generate_hypotheses(ticker: str, company_name: str):
    """Generate hypotheses for a ticker."""
    print(f"\nGenerating hypotheses for {ticker} ({company_name})...")
    print("=" * 80)

    # Fetch sources
    print("\n1. Fetching data from SEC EDGAR...")
    source_manager = SourceManager()
    sources = await source_manager.fetch_all_sources(
        ticker=ticker,
        company_name=company_name,
        include_filings=True,
        include_fundamentals=True,
        include_news=False,
    )
    print(f"   ✓ Fetched {len(sources)} sources")

    # Generate hypotheses
    print("\n2. Generating investment hypotheses...")
    hypothesis_agent = HypothesisGeneratorAgent()
    hypotheses = await hypothesis_agent.generate(
        ticker=ticker,
        company_name=company_name,
        sources=sources,
        num_hypotheses=7,
    )
    print(f"   ✓ Generated {len(hypotheses)} hypotheses")

    # Display hypotheses
    print("\n3. Generated Hypotheses:")
    print("=" * 80)
    for i, h in enumerate(hypotheses, 1):
        print(f"\n[{i}] {h['title']}")
        print(f"    Thesis: {h['thesis'][:100]}...")
        print(f"    Impact: {h.get('impact', 'UNKNOWN')}")

    # Save to file
    output_file = Path(f"{ticker}_hypotheses.json")
    with open(output_file, "w") as f:
        json.dump(hypotheses, f, indent=2)

    print(f"\n4. Saved hypotheses to: {output_file}")
    print("\n" + "=" * 80)
    print("\nNext steps:")
    print("1. Review the hypotheses above")
    print("2. Ask Claude Code to research these hypotheses using WebSearch")
    print("3. Run analysis with the web research results")
    print("\n" + "=" * 80)

    return hypotheses


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate investment hypotheses")
    parser.add_argument("ticker", help="Stock ticker symbol")
    parser.add_argument("--company", required=True, help="Company name")

    args = parser.parse_args()

    asyncio.run(generate_hypotheses(args.ticker, args.company))
