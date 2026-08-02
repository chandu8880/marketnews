"""Per-stock price stats (current price, 52-week low/average/high) for the
stock detail screen, sourced live from Yahoo Finance's free, unauthenticated
chart API - the same source already used for the Nifty/Sensex ticker.

One request per stock (range=1y, weekly candles) covers everything: the
`meta` block has the live price and 52-week high/low, and the weekly close
series lets us compute a genuine 52-week average rather than just the
midpoint of the high/low.
"""
import logging

import httpx

logger = logging.getLogger("stock_price")

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

# A handful of our tracked "tickers" are actually indices, not NSE-listed
# equities, so they need Yahoo's index symbols instead of a ".NS" suffix.
_INDEX_SYMBOLS = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN",
}


def _yahoo_symbol(ticker: str) -> str:
    return _INDEX_SYMBOLS.get(ticker, f"{ticker}.NS")


def fetch_stock_price_stats(ticker: str):
    symbol = _yahoo_symbol(ticker)
    try:
        resp = httpx.get(
            YAHOO_CHART_URL.format(symbol=symbol),
            params={"range": "1y", "interval": "1wk"},
            headers=YAHOO_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        meta = result["meta"]

        # Note: `chartPreviousClose` here is the close at the *start of the
        # requested 1y range* (i.e. ~a year ago), not yesterday's close - so
        # it's deliberately not used to compute a day-over-day change, which
        # would be wrong by construction. Day-change isn't part of this
        # module's job (see market_indices.py for that, using a plain
        # request with no range/interval).
        price = meta.get("regularMarketPrice")

        closes = []
        try:
            closes = [c for c in result["indicators"]["quote"][0]["close"] if c is not None]
        except (KeyError, IndexError, TypeError):
            pass
        week52_avg = round(sum(closes) / len(closes), 2) if closes else None

        return {
            "ticker": ticker,
            "price": round(price, 2) if price is not None else None,
            "week52_low": round(meta["fiftyTwoWeekLow"], 2) if meta.get("fiftyTwoWeekLow") is not None else None,
            "week52_avg": week52_avg,
            "week52_high": round(meta["fiftyTwoWeekHigh"], 2) if meta.get("fiftyTwoWeekHigh") is not None else None,
        }
    except Exception:
        logger.exception("Failed to fetch price stats for %s (%s)", ticker, symbol)
        return None
