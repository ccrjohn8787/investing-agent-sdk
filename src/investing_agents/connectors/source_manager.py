"""Unified source manager for fetching investment data.

Handles data fetching from multiple sources:
- SEC EDGAR filings (10-K, 10-Q, 8-K)
- Company fundamentals
- News articles (placeholder)
- Analyst reports (placeholder)
"""

import httpx
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from investing_agents.connectors.edgar import (
    fetch_companyfacts,
    parse_companyfacts_to_fundamentals,
)

logger = structlog.get_logger(__name__)


class SourceManager:
    """Unified manager for fetching investment research sources."""

    def __init__(self, edgar_ua: Optional[str] = None):
        """Initialize source manager.

        Args:
            edgar_ua: User-Agent string for SEC EDGAR requests
        """
        self.edgar_ua = edgar_ua or "email@example.com Investing-Agent/0.1"
        self.log = logger.bind(component="SourceManager")

    async def fetch_all_sources(
        self,
        ticker: str,
        company_name: str,
        include_fundamentals: bool = True,
        include_filings: bool = True,
        include_news: bool = False,
    ) -> List[Dict[str, Any]]:
        """Fetch all available sources for a company.

        Args:
            ticker: Stock ticker symbol
            company_name: Company name
            include_fundamentals: Fetch company fundamentals from EDGAR
            include_filings: Fetch recent SEC filings
            include_news: Fetch news articles (placeholder)

        Returns:
            List of source documents with metadata
        """
        sources: List[Dict[str, Any]] = []

        self.log.info(
            "fetching.sources.start",
            ticker=ticker,
            company=company_name,
            fundamentals=include_fundamentals,
            filings=include_filings,
            news=include_news,
        )

        # Fetch fundamentals from EDGAR
        if include_fundamentals:
            fundamentals_source = await self._fetch_fundamentals(ticker, company_name)
            if fundamentals_source:
                sources.append(fundamentals_source)

        # Fetch SEC filings
        if include_filings:
            # TODO: Implement actual filing fetcher
            # For now, use placeholder that describes what data would come from filings
            filing_source = self._create_filing_placeholder(ticker, company_name)
            sources.append(filing_source)

        # Fetch news (placeholder)
        if include_news:
            news_source = self._create_news_placeholder(ticker, company_name)
            sources.append(news_source)

        self.log.info("fetching.sources.complete", ticker=ticker, source_count=len(sources))

        return sources

    async def _fetch_fundamentals(self, ticker: str, company_name: str) -> Optional[Dict[str, Any]]:
        """Fetch company fundamentals from SEC EDGAR.

        Args:
            ticker: Stock ticker
            company_name: Company name

        Returns:
            Source document with fundamentals data
        """
        try:
            self.log.info("fetching.fundamentals.start", ticker=ticker)

            # Fetch companyfacts from EDGAR
            with httpx.Client() as client:
                companyfacts_json, meta = fetch_companyfacts(
                    ticker, edgar_ua=self.edgar_ua, client=client
                )

            # Parse to fundamentals
            fundamentals = parse_companyfacts_to_fundamentals(
                companyfacts_json, ticker, company_name
            )

            # Format as source document
            source = {
                "type": "fundamentals",
                "date": datetime.utcnow().strftime("%Y-%m-%d"),
                "url": meta.get("source_url", ""),
                "content": self._format_fundamentals(fundamentals),
                "metadata": {
                    "source": "SEC EDGAR API",
                    "retrieved_at": meta.get("retrieved_at"),
                    "ticker": ticker,
                    "company": company_name,
                },
            }

            self.log.info(
                "fetching.fundamentals.complete",
                ticker=ticker,
                revenue_years=len(fundamentals.revenue),
                has_ttm=fundamentals.revenue_ttm is not None,
            )

            return source

        except Exception as e:
            self.log.error("fetching.fundamentals.error", ticker=ticker, error=str(e))
            return None

    def _format_fundamentals(self, fundamentals) -> str:
        """Format fundamentals data as readable text.

        Args:
            fundamentals: Fundamentals object

        Returns:
            Formatted string
        """
        lines = [
            f"Company: {fundamentals.company}",
            f"Ticker: {fundamentals.ticker}",
            f"Currency: {fundamentals.currency}",
            "",
            "Annual Revenue:",
        ]

        # Add revenue data
        if fundamentals.revenue:
            for year in sorted(fundamentals.revenue.keys(), reverse=True)[:5]:
                lines.append(f"  {year}: ${fundamentals.revenue[year]:,.0f}")

        if fundamentals.revenue_ttm:
            lines.append(f"  TTM: ${fundamentals.revenue_ttm:,.0f}")

        # Add EBIT data
        if fundamentals.ebit:
            lines.append("")
            lines.append("Annual EBIT (Operating Income):")
            for year in sorted(fundamentals.ebit.keys(), reverse=True)[:5]:
                lines.append(f"  {year}: ${fundamentals.ebit[year]:,.0f}")

        if fundamentals.ebit_ttm:
            lines.append(f"  TTM: ${fundamentals.ebit_ttm:,.0f}")

        # Add shares outstanding
        if fundamentals.shares_out:
            lines.append("")
            shares_millions = fundamentals.shares_out / 1e6
            lines.append(f"Shares Outstanding: {shares_millions:,.1f} million shares")
            lines.append(f"  (Raw count: {fundamentals.shares_out:,.0f})")

        # Add tax rate
        if fundamentals.tax_rate:
            lines.append(f"Effective Tax Rate: {fundamentals.tax_rate * 100:.1f}%")

        # Add D&A
        if fundamentals.dep_amort:
            lines.append("")
            lines.append("Annual Depreciation & Amortization:")
            for year in sorted(fundamentals.dep_amort.keys(), reverse=True)[:3]:
                lines.append(f"  {year}: ${fundamentals.dep_amort[year]:,.0f}")

        # Add CapEx
        if fundamentals.capex:
            lines.append("")
            lines.append("Annual Capital Expenditures:")
            for year in sorted(fundamentals.capex.keys(), reverse=True)[:3]:
                # CapEx is often negative in filings, take absolute value
                capex_val = abs(fundamentals.capex[year])
                lines.append(f"  {year}: ${capex_val:,.0f}")

        return "\n".join(lines)

    def _create_filing_placeholder(self, ticker: str, company_name: str) -> Dict[str, Any]:
        """Create placeholder for SEC filing data.

        Args:
            ticker: Stock ticker
            company_name: Company name

        Returns:
            Placeholder source document
        """
        return {
            "type": "10-Q",
            "date": "2024-09-30",
            "url": f"https://sec.gov/{ticker.lower()}-10q-placeholder",
            "content": f"""{company_name} Form 10-Q (Placeholder)

Note: This is a placeholder. In production, this would contain:
- Revenue breakdown by segment
- Gross margin and operating margin
- Key metrics (growth rates, unit economics)
- Management discussion (MD&A)
- Risk factors

Future implementation will:
1. Fetch actual 10-Q/10-K filings from EDGAR
2. Parse XBRL data for financial statements
3. Extract MD&A sections
4. Parse exhibits for material contracts

For now, agents will work with fundamentals data from companyfacts API.
""",
            "metadata": {
                "source": "SEC EDGAR (placeholder)",
                "ticker": ticker,
                "company": company_name,
                "filing_type": "10-Q",
            },
        }

    def _create_news_placeholder(self, ticker: str, company_name: str) -> Dict[str, Any]:
        """Create placeholder for news data.

        Args:
            ticker: Stock ticker
            company_name: Company name

        Returns:
            Placeholder source document
        """
        return {
            "type": "news",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "url": f"https://news-placeholder/{ticker.lower()}",
            "content": f"""{company_name} News Summary (Placeholder)

Note: This is a placeholder. In production, this would contain:
- Recent news articles
- Press releases
- Analyst upgrades/downgrades
- Industry developments

Future implementation options:
1. NewsAPI.org integration
2. RSS feed aggregation
3. Google News scraping
4. Financial news APIs (Alpha Vantage, IEX Cloud)

For now, focus is on SEC fundamentals data for hypothesis testing.
""",
            "metadata": {
                "source": "News aggregator (placeholder)",
                "ticker": ticker,
                "company": company_name,
            },
        }
