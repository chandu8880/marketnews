"""Bulk technical-indicator screener for the top 75 tracked NSE stocks -
one table, every stock's RSI/Stochastic RSI/CCI/MACD/VWAP/DI/ADX at once,
sortable client-side by any column.

Each stock only needs one Yahoo Finance call (see indicators.py), but 75
of them run sequentially would take well over a minute - so this fetches
them concurrently via a thread pool, the same approach news_sources.py
uses for the 12 RSS feeds. The result is cached and refreshed on a
schedule (see scheduler.py) rather than recomputed on every page load,
since a screen of 75 concurrent external requests is too expensive to
repeat per visit.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .indicators import compute_all_indicators
from .tickers import COMPANY_MAP, TOP_ANALYSIS_TICKERS

logger = logging.getLogger("screener")

SCREENER_TICKER_COUNT = 75
MAX_WORKERS = 15


def fetch_screener_data(limit: int = SCREENER_TICKER_COUNT):
    tickers = TOP_ANALYSIS_TICKERS[:limit]
    rows = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(compute_all_indicators, t): t for t in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                data = future.result()
            except Exception:
                logger.exception("Screener indicator fetch failed for %s", ticker)
                continue
            if data is None:
                continue
            rows.append({
                "ticker": ticker,
                "name": COMPANY_MAP[ticker][0],
                "rsi": data["rsi"],
                "stoch_rsi": data["stoch_rsi"],
                "cci": data["cci"],
                "macd": data["macd"],
                "macd_signal_line": data["macd_signal_line"],
                "macd_histogram": data["macd_histogram"],
                "vwap": data["vwap"],
                "plus_di": data["plus_di"],
                "minus_di": data["minus_di"],
                "adx": data["adx"],
            })

    # Concurrent completion order is nondeterministic - sort back to the
    # tracked-list order so the table doesn't reshuffle between refreshes.
    order = {t: i for i, t in enumerate(tickers)}
    rows.sort(key=lambda r: order.get(r["ticker"], 999))
    return rows
