"""Look up stock metadata (name, sector, industry, ISIN) via yfinance."""

from __future__ import annotations

import logging
from functools import lru_cache

import yfinance as yf

log = logging.getLogger(__name__)


def to_yfinance_ticker(symbol: str, exchange: str = "NSE") -> str:
    """Convert NSE/BSE symbol to yfinance format.

    NSE: 'INFY' -> 'INFY.NS'
    BSE: 'INFY' -> 'INFY.BO'
    """
    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    if symbol.endswith(suffix):
        return symbol
    return f"{symbol}{suffix}"


@lru_cache(maxsize=512)
def fetch_metadata(symbol: str, exchange: str = "NSE") -> dict:
    """Fetch name, sector, industry, ISIN for a symbol.

    Cached in-process; lookups are slow. yfinance returns wide-ranging info;
    we extract only what we need.

    Returns a dict with keys: name, sector, industry, isin, current_price.
    Missing fields are returned as empty strings / None.
    """
    ticker_str = to_yfinance_ticker(symbol, exchange)
    try:
        ticker = yf.Ticker(ticker_str)
        info = ticker.info or {}
        # ISIN sometimes lives separately
        try:
            isin = ticker.isin or info.get("isin", "") or ""
        except Exception:
            isin = info.get("isin", "") or ""
        # Normalize: yfinance uses "-" for missing values
        isin = "" if isin in ("-", "N/A", "None") else isin.strip().upper()
        # Validate format (12 chars, alphanumeric uppercase)
        if not (len(isin) == 12 and isin.isalnum()):
            isin = ""

        return {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "yfinance_ticker": ticker_str,
            "name": info.get("longName") or info.get("shortName") or "",
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "isin": (isin or "").upper(),
            "current_price": info.get("currentPrice") or info.get("regularMarketPrice"),
            "currency": info.get("currency", "INR"),
        }
    except Exception as exc:
        log.warning("yfinance lookup failed for %s: %s", ticker_str, exc)
        return {
            "symbol": symbol.upper(),
            "exchange": exchange.upper(),
            "yfinance_ticker": ticker_str,
            "name": "",
            "sector": "",
            "industry": "",
            "isin": "",
            "current_price": None,
            "currency": "INR",
        }
