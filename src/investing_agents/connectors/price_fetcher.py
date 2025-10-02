"""Real-time stock price fetching using yfinance."""

from datetime import datetime
from typing import Dict, Optional

import yfinance as yf


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
