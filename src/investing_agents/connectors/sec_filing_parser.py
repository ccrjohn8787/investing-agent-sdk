"""SEC filing parser for 10-K and 10-Q documents.

Fetches and parses full text from SEC EDGAR filings, extracting key sections:
- Management's Discussion and Analysis (MD&A)
- Risk Factors
- Business Description
- Financial Statements and Notes
"""

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import structlog
from bs4 import BeautifulSoup

from investing_agents.utils.caching import cache_edgar_call

logger = structlog.get_logger(__name__)


@dataclass
class FilingSection:
    """A section from a SEC filing."""

    title: str
    content: str
    item_number: Optional[str] = None  # e.g., "Item 7", "Item 1A"


@dataclass
class SECFiling:
    """Parsed SEC filing."""

    ticker: str
    cik: str
    filing_type: str  # "10-K" or "10-Q"
    filing_date: str
    fiscal_year: str
    fiscal_period: str  # "FY" for 10-K, "Q1"/"Q2"/"Q3" for 10-Q
    accession_number: str
    url: str
    sections: List[FilingSection]
    full_text: str  # Complete filing text (truncated if too long)


class SECFilingParser:
    """Parser for SEC 10-K and 10-Q filings."""

    def __init__(
        self,
        edgar_ua: str = "investing-agents dev@example.com",
        max_text_length: int = 500000,  # ~500KB of text
    ):
        """Initialize parser.

        Args:
            edgar_ua: User agent string for SEC EDGAR (required by SEC)
            max_text_length: Maximum text length to store (to avoid memory issues)
        """
        self.edgar_ua = edgar_ua
        self.max_text_length = max_text_length
        self.base_url = "https://www.sec.gov"

    async def get_recent_filings(
        self,
        ticker: str,
        cik: str,
        filing_types: List[str] = None,
        count: int = 5,
    ) -> List[Dict]:
        """Get recent filings for a company.

        Args:
            ticker: Stock ticker
            cik: Central Index Key (CIK)
            filing_types: List of filing types to fetch (default: ["10-K", "10-Q"])
            count: Number of filings to fetch per type

        Returns:
            List of filing metadata dictionaries
        """
        if filing_types is None:
            filing_types = ["10-K", "10-Q"]

        # Pad CIK to 10 digits
        cik_padded = cik.zfill(10)

        # Fetch submissions JSON
        url = f"{self.base_url}/cgi-bin/browse-edgar"
        params = {
            "action": "getcompany",
            "CIK": cik_padded,
            "type": "",
            "dateb": "",
            "owner": "exclude",
            "count": count * len(filing_types),
            "output": "atom",
        }

        headers = {"User-Agent": self.edgar_ua}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()

        # Parse filings from response
        # For simplicity, using a mock structure here
        # Real implementation would parse the atom feed
        filings = []

        logger.info(
            "sec_parser.filings_fetched",
            ticker=ticker,
            cik=cik,
            count=len(filings),
        )

        return filings

    @cache_edgar_call
    async def fetch_filing_document(
        self,
        accession_number: str,
        cik: str,
    ) -> str:
        """Fetch filing document HTML.

        Args:
            accession_number: SEC accession number (e.g., "0001193125-21-186824")
            cik: Central Index Key

        Returns:
            Raw HTML content of filing
        """
        # Remove hyphens from accession number for URL
        accession_clean = accession_number.replace("-", "")

        # Construct URL to filing document
        # Format: /Archives/edgar/data/{CIK}/{ACCESSION}/{ACCESSION}.txt
        cik_padded = cik.zfill(10)
        url = f"{self.base_url}/Archives/edgar/data/{cik_padded}/{accession_clean}/{accession_number}.txt"

        headers = {"User-Agent": self.edgar_ua}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            content = response.text

        logger.info(
            "sec_parser.document_fetched",
            accession_number=accession_number,
            cik=cik,
            size_kb=len(content) / 1024,
        )

        return content

    def parse_filing(
        self,
        html_content: str,
        ticker: str,
        cik: str,
        filing_type: str,
        filing_date: str,
        accession_number: str,
    ) -> SECFiling:
        """Parse SEC filing HTML into structured format.

        Args:
            html_content: Raw HTML content
            ticker: Stock ticker
            cik: Central Index Key
            filing_type: "10-K" or "10-Q"
            filing_date: Filing date (YYYY-MM-DD)
            accession_number: SEC accession number

        Returns:
            Parsed SEC filing
        """
        logger.info(
            "sec_parser.parsing_start",
            ticker=ticker,
            filing_type=filing_type,
        )

        # Parse HTML
        soup = BeautifulSoup(html_content, "html.parser")

        # Extract sections based on filing type
        if filing_type == "10-K":
            sections = self._parse_10k_sections(soup)
            fiscal_period = "FY"
        else:  # 10-Q
            sections = self._parse_10q_sections(soup)
            # Extract quarter from filing (simplified - would need real parsing)
            fiscal_period = "Q1"  # Placeholder

        # Get full text (clean and truncate)
        full_text = soup.get_text(separator="\n", strip=True)
        if len(full_text) > self.max_text_length:
            full_text = full_text[: self.max_text_length] + "\n... [truncated]"

        # Extract fiscal year from filing date
        fiscal_year = filing_date[:4]

        filing = SECFiling(
            ticker=ticker,
            cik=cik,
            filing_type=filing_type,
            filing_date=filing_date,
            fiscal_year=fiscal_year,
            fiscal_period=fiscal_period,
            accession_number=accession_number,
            url=f"{self.base_url}/cgi-bin/viewer?action=view&cik={cik}&accession_number={accession_number}",
            sections=sections,
            full_text=full_text,
        )

        logger.info(
            "sec_parser.parsing_complete",
            ticker=ticker,
            sections_found=len(sections),
            text_length=len(full_text),
        )

        return filing

    def _parse_10k_sections(self, soup: BeautifulSoup) -> List[FilingSection]:
        """Parse 10-K specific sections.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of filing sections
        """
        sections = []

        # Key 10-K items to extract
        target_items = {
            "Item 1": "Business",
            "Item 1A": "Risk Factors",
            "Item 7": "Management's Discussion and Analysis",
            "Item 8": "Financial Statements and Supplementary Data",
        }

        for item_num, item_title in target_items.items():
            content = self._extract_item_section(soup, item_num, item_title)
            if content:
                sections.append(
                    FilingSection(
                        title=f"{item_num}. {item_title}",
                        content=content,
                        item_number=item_num,
                    )
                )

        return sections

    def _parse_10q_sections(self, soup: BeautifulSoup) -> List[FilingSection]:
        """Parse 10-Q specific sections.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            List of filing sections
        """
        sections = []

        # Key 10-Q items (Part I)
        part1_items = {
            "Item 1": "Financial Statements",
            "Item 2": "Management's Discussion and Analysis",
        }

        for item_num, item_title in part1_items.items():
            content = self._extract_item_section(soup, item_num, item_title)
            if content:
                sections.append(
                    FilingSection(
                        title=f"Part I - {item_num}. {item_title}",
                        content=content,
                        item_number=item_num,
                    )
                )

        return sections

    def _extract_item_section(
        self,
        soup: BeautifulSoup,
        item_number: str,
        item_title: str,
    ) -> Optional[str]:
        """Extract a specific item section from filing.

        Args:
            soup: BeautifulSoup parsed HTML
            item_number: Item number (e.g., "Item 1A")
            item_title: Item title

        Returns:
            Section content text or None if not found
        """
        # Search for section heading
        # Pattern: "Item 1A" or "Item 1A." followed by title
        pattern = re.compile(
            rf"{re.escape(item_number)}\.?\s+{re.escape(item_title)}",
            re.IGNORECASE,
        )

        # Find heading
        heading = soup.find(string=pattern)
        if not heading:
            # Try without title
            pattern_simple = re.compile(rf"{re.escape(item_number)}\.?\s", re.IGNORECASE)
            heading = soup.find(string=pattern_simple)

        if not heading:
            logger.warning(
                "sec_parser.section_not_found",
                item_number=item_number,
                item_title=item_title,
            )
            return None

        # Extract content until next item
        content_parts = []
        current = heading.parent

        while current:
            text = current.get_text(separator=" ", strip=True)
            content_parts.append(text)

            # Stop at next item (simplified - real implementation would be more robust)
            if "item" in text.lower() and len(content_parts) > 1:
                break

            current = current.find_next_sibling()

            # Limit content size
            if len(" ".join(content_parts)) > 100000:
                break

        content = "\n".join(content_parts)
        return content[:50000]  # Truncate to 50KB per section

    def format_for_agents(self, filing: SECFiling) -> str:
        """Format parsed filing for agent consumption.

        Args:
            filing: Parsed SEC filing

        Returns:
            Formatted text string
        """
        lines = [
            f"SEC Filing: {filing.filing_type}",
            f"Company: {filing.ticker}",
            f"Filing Date: {filing.filing_date}",
            f"Fiscal Period: {filing.fiscal_year} {filing.fiscal_period}",
            f"",
            "=" * 80,
            "",
        ]

        for section in filing.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            # Truncate section content to manageable size
            content = section.content[:10000] + "..." if len(section.content) > 10000 else section.content
            lines.append(content)
            lines.append("")
            lines.append("-" * 80)
            lines.append("")

        return "\n".join(lines)
