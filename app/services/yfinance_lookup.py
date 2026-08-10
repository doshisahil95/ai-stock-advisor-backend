"""Look up stock metadata (name, sector, industry, ISIN) via yfinance."""

from __future__ import annotations

import logging

import yfinance as yf

log = logging.getLogger(__name__)

# #80 M9: replace @lru_cache with a success-only in-process cache.
# @lru_cache caches FAILURES (empty result dict) permanently for the process
# lifetime — a single transient yfinance hiccup wipes metadata resolution for
# a symbol until the service restarts (potentially hours/days on the single
# long-lived Uvicorn worker). We only cache results where the lookup actually
# succeeded (non-empty name or ISIN).
_metadata_cache: dict[tuple[str, str], dict] = {}


def to_yfinance_ticker(symbol: str, exchange: str = "NSE") -> str:
    """Convert NSE/BSE symbol to yfinance format.

    NSE: 'INFY' -> 'INFY.NS'
    BSE: 'INFY' -> 'INFY.BO'
    """
    suffix = ".NS" if exchange.upper() == "NSE" else ".BO"
    if symbol.endswith(suffix):
        return symbol
    return f"{symbol}{suffix}"


def fetch_metadata(symbol: str, exchange: str = "NSE") -> dict:
    """Fetch name, sector, industry, ISIN for a symbol.

    Cached in-process; lookups are slow. yfinance returns wide-ranging info;
    we extract only what we need.

    Returns a dict with keys: name, sector, industry, isin, current_price.
    Missing fields are returned as empty strings / None.
    """
    cache_key = (symbol.upper(), exchange.upper())
    if cache_key in _metadata_cache:
        return _metadata_cache[cache_key]

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

        result = {
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
        # Only cache on success (non-empty name or ISIN = lookup actually worked).
        if result["name"] or result["isin"]:
            _metadata_cache[cache_key] = result
        return result
    except Exception as exc:
        log.warning("yfinance lookup failed for %s: %s", ticker_str, exc)
        # Do NOT cache failures — a transient error must be retried next call.
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
