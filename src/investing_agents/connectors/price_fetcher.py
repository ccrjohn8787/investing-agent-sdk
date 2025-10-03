"""Real-time stock price and financial fundamentals fetching using yfinance."""

from datetime import datetime
from typing import Dict, Optional

import structlog
import yfinance as yf

logger = structlog.get_logger(__name__)


async def fetch_current_price(ticker: str) -> Dict[str, any]:
    """Fetch real-time stock price using Yahoo Finance.

    Args:
        ticker: Stock ticker symbol (e.g., "NVDA", "AAPL")

    Returns:
        Dict with:
            - price_per_share: Current stock price
            - date: ISO timestamp of fetch
            - source: Data source identifier
            - currency: Price currency
            - market_cap: Market capitalization in billions (if available)

    Raises:
        ValueError: If ticker is invalid or price cannot be fetched
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Try multiple price fields in priority order
        current_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )

        if current_price is None:
            raise ValueError(f"Unable to fetch price for ticker: {ticker}")

        # Get additional context
        market_cap_raw = info.get("marketCap")
        market_cap_billions = market_cap_raw / 1e9 if market_cap_raw else None

        return {
            "price_per_share": round(float(current_price), 2),
            "date": datetime.now().isoformat(),
            "source": "Yahoo Finance (yfinance)",
            "currency": info.get("currency", "USD"),
            "market_cap_billions": (
                round(market_cap_billions, 2) if market_cap_billions else None
            ),
            "ticker": ticker.upper(),
        }

    except Exception as e:
        raise ValueError(f"Failed to fetch price for {ticker}: {str(e)}") from e


def fetch_current_price_sync(ticker: str) -> Dict[str, any]:
    """Synchronous version of fetch_current_price for backwards compatibility.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Price data dict (same structure as async version)

    Raises:
        ValueError: If ticker is invalid or price cannot be fetched
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        current_price = (
            info.get("currentPrice")
            or info.get("regularMarketPrice")
            or info.get("previousClose")
        )

        if current_price is None:
            raise ValueError(f"Unable to fetch price for ticker: {ticker}")

        market_cap_raw = info.get("marketCap")
        market_cap_billions = market_cap_raw / 1e9 if market_cap_raw else None

        return {
            "price_per_share": round(float(current_price), 2),
            "date": datetime.now().isoformat(),
            "source": "Yahoo Finance (yfinance)",
            "currency": info.get("currency", "USD"),
            "market_cap_billions": (
                round(market_cap_billions, 2) if market_cap_billions else None
            ),
            "ticker": ticker.upper(),
        }

    except Exception as e:
        raise ValueError(f"Failed to fetch price for {ticker}: {str(e)}") from e


async def fetch_financial_fundamentals(ticker: str) -> Dict[str, any]:
    """Fetch comprehensive financial fundamentals from Yahoo Finance API.

    This function fetches FACTUAL financial data that should be used as-is
    for DCF valuation, rather than parsing from text with LLM (which is error-prone).

    Args:
        ticker: Stock ticker symbol (e.g., "META", "NVDA")

    Returns:
        Dict with:
            - shares_outstanding_millions: Shares outstanding in millions
            - total_revenue_billions: TTM revenue in billions
            - operating_margin_pct: TTM operating margin as percentage (0-100)
            - total_debt_billions: Total debt in billions
            - total_cash_billions: Cash & equivalents in billions
            - effective_tax_rate_pct: Effective tax rate as percentage (0-100)
            - current_price: Current stock price
            - market_cap_billions: Market cap in billions
            - ebitda_billions: TTM EBITDA in billions (if available)
            - free_cash_flow_billions: TTM FCF in billions (if available)
            - data_quality: Dict showing which fields were available
            - fetch_timestamp: ISO timestamp of fetch

    Note:
        Returns None for unavailable fields. Caller should handle fallback to LLM extraction.
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Track data availability for logging
        available_fields = []
        missing_fields = []

        # Helper to safely extract and convert values
        def safe_extract(field_name: str, divisor: float = 1.0, multiply: float = 1.0) -> Optional[float]:
            value = info.get(field_name)
            if value is not None:
                available_fields.append(field_name)
                try:
                    return round(float(value) / divisor * multiply, 2)
                except (ValueError, TypeError):
                    logger.warning(
                        "fundamentals.field_conversion_failed",
                        ticker=ticker,
                        field=field_name,
                        value=value,
                    )
                    return None
            else:
                missing_fields.append(field_name)
                return None

        # Extract all fundamental fields
        result = {
            # CRITICAL: Shares outstanding (convert to millions)
            "shares_outstanding_millions": safe_extract("sharesOutstanding", divisor=1e6),

            # Revenue metrics (convert to billions)
            "total_revenue_billions": safe_extract("totalRevenue", divisor=1e9),

            # Profitability metrics (already in percentage or decimal)
            "operating_margin_pct": (
                safe_extract("operatingMargins", multiply=100)  # Convert 0.42 → 42%
                if info.get("operatingMargins") is not None
                else None
            ),

            # Balance sheet (convert to billions)
            "total_debt_billions": safe_extract("totalDebt", divisor=1e9),
            "total_cash_billions": safe_extract("totalCash", divisor=1e9),

            # Tax rate (already in percentage or decimal)
            "effective_tax_rate_pct": (
                safe_extract("effectiveTaxRate", multiply=100)  # Convert 0.15 → 15%
                if info.get("effectiveTaxRate") is not None
                else None
            ),

            # Additional metrics
            "ebitda_billions": safe_extract("ebitda", divisor=1e9),
            "free_cash_flow_billions": safe_extract("freeCashflow", divisor=1e9),

            # Price data (already handled by fetch_current_price, but included for completeness)
            "current_price": (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            ),
            "market_cap_billions": safe_extract("marketCap", divisor=1e9),

            # Metadata
            "ticker": ticker.upper(),
            "fetch_timestamp": datetime.now().isoformat(),
            "source": "Yahoo Finance (yfinance)",
            "currency": info.get("currency", "USD"),

            # Data quality tracking
            "data_quality": {
                "available_fields": available_fields,
                "missing_fields": missing_fields,
                "completeness_pct": round(
                    len(available_fields) / (len(available_fields) + len(missing_fields)) * 100, 1
                ) if (available_fields or missing_fields) else 0,
            },
        }

        # Log data quality for debugging
        logger.info(
            "fundamentals.fetched",
            ticker=ticker,
            available=len(available_fields),
            missing=len(missing_fields),
            completeness=result["data_quality"]["completeness_pct"],
            missing_fields=missing_fields[:5],  # Show first 5 missing fields
        )

        return result

    except Exception as e:
        logger.error(
            "fundamentals.fetch_failed",
            ticker=ticker,
            error=str(e),
        )
        raise ValueError(f"Failed to fetch fundamentals for {ticker}: {str(e)}") from e


def fetch_financial_fundamentals_sync(ticker: str) -> Dict[str, any]:
    """Synchronous version of fetch_financial_fundamentals.

    Args:
        ticker: Stock ticker symbol

    Returns:
        Financial fundamentals dict (same structure as async version)
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        available_fields = []
        missing_fields = []

        def safe_extract(field_name: str, divisor: float = 1.0, multiply: float = 1.0) -> Optional[float]:
            value = info.get(field_name)
            if value is not None:
                available_fields.append(field_name)
                try:
                    return round(float(value) / divisor * multiply, 2)
                except (ValueError, TypeError):
                    logger.warning(
                        "fundamentals.field_conversion_failed",
                        ticker=ticker,
                        field=field_name,
                        value=value,
                    )
                    return None
            else:
                missing_fields.append(field_name)
                return None

        result = {
            "shares_outstanding_millions": safe_extract("sharesOutstanding", divisor=1e6),
            "total_revenue_billions": safe_extract("totalRevenue", divisor=1e9),
            "operating_margin_pct": (
                safe_extract("operatingMargins", multiply=100)
                if info.get("operatingMargins") is not None
                else None
            ),
            "total_debt_billions": safe_extract("totalDebt", divisor=1e9),
            "total_cash_billions": safe_extract("totalCash", divisor=1e9),
            "effective_tax_rate_pct": (
                safe_extract("effectiveTaxRate", multiply=100)
                if info.get("effectiveTaxRate") is not None
                else None
            ),
            "ebitda_billions": safe_extract("ebitda", divisor=1e9),
            "free_cash_flow_billions": safe_extract("freeCashflow", divisor=1e9),
            "current_price": (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
            ),
            "market_cap_billions": safe_extract("marketCap", divisor=1e9),
            "ticker": ticker.upper(),
            "fetch_timestamp": datetime.now().isoformat(),
            "source": "Yahoo Finance (yfinance)",
            "currency": info.get("currency", "USD"),
            "data_quality": {
                "available_fields": available_fields,
                "missing_fields": missing_fields,
                "completeness_pct": round(
                    len(available_fields) / (len(available_fields) + len(missing_fields)) * 100, 1
                ) if (available_fields or missing_fields) else 0,
            },
        }

        logger.info(
            "fundamentals.fetched",
            ticker=ticker,
            available=len(available_fields),
            missing=len(missing_fields),
            completeness=result["data_quality"]["completeness_pct"],
        )

        return result

    except Exception as e:
        logger.error(
            "fundamentals.fetch_failed",
            ticker=ticker,
            error=str(e),
        )
        raise ValueError(f"Failed to fetch fundamentals for {ticker}: {str(e)}") from e
