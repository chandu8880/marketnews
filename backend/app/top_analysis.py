"""Orchestrates the Top Analysis screen: a cheap list of ~100 tracked NSE
stocks, and a full on-demand deep-dive per stock (indicators + shareholding
+ top-3 news + NVIDIA verdict) computed live only when a stock is opened -
computing all of this for 100 stocks up front would take many minutes and
doesn't fit inside a single request/serverless-function window.
"""
import logging
from urllib.parse import quote

from .indicators import compute_all_indicators
from .ingest import process_raw_articles
from .news_sources import fetch_feed
from .nvidia_llm import get_verdict
from .shareholding import fetch_shareholding_pattern
from .stocks_analysis import aggregate_stock_sentiment
from .store import store
from .tickers import COMPANY_MAP, TOP_ANALYSIS_TICKERS

logger = logging.getLogger("top_analysis")


def list_top_stocks(limit: int = 100):
    """Cheap list: ticker + name + whatever aggregate sentiment we already
    have cached from the news pipeline (0 mentions / neutral is expected
    for tickers that just haven't come up in recent news - the deep-dive
    is what actually looks the stock up properly, live).
    """
    aggregated = {s["ticker"]: s for s in aggregate_stock_sentiment(limit=300)}
    results = []
    for ticker in TOP_ANALYSIS_TICKERS[:limit]:
        name = COMPANY_MAP[ticker][0]
        agg = aggregated.get(ticker)
        results.append({
            "ticker": ticker,
            "name": name,
            "mentions": agg["mentions"] if agg else 0,
            "overall_sentiment": agg["overall_sentiment"] if agg else "neutral",
            "net_score": agg["net_score"] if agg else 0.0,
        })
    return results


def _find_news(ticker: str, name: str, limit: int = 3):
    matched = [a for a in store.all_sorted() if any(s.ticker == ticker for s in a.related_stocks)]
    if len(matched) < limit:
        # Supplement with a live targeted search, same pattern as search.py,
        # for tickers that don't already have enough cached coverage.
        query = quote(f'"{name}" (stock OR shares OR NSE OR BSE)')
        url = f"https://news.google.com/rss/search?q=when:14d+{query}&hl=en-IN&gl=IN&ceid=IN:en"
        try:
            raw = fetch_feed(f"Top Analysis: {ticker}", url)
            fresh = process_raw_articles(raw[:5])
            store.upsert_many(fresh)
            existing_ids = {a.id for a in matched}
            matched = matched + [a for a in fresh if a.id not in existing_ids]
        except Exception:
            logger.exception("Live news supplement failed for %s", ticker)

    matched.sort(key=lambda a: a.published, reverse=True)
    return [
        {
            "id": a.id,
            "title": a.title,
            "source": a.source,
            "link": a.link,
            "published": a.published,
            "sentiment_label": a.sentiment_label,
        }
        for a in matched[:limit]
    ]


def analyze_stock(ticker: str):
    ticker = ticker.upper()
    if ticker not in COMPANY_MAP:
        return None
    name = COMPANY_MAP[ticker][0]

    indicators = compute_all_indicators(ticker)
    shareholding = fetch_shareholding_pattern(ticker, name)
    news = _find_news(ticker, name)
    verdict = get_verdict(ticker, name, indicators, shareholding, news)

    return {
        "ticker": ticker,
        "name": name,
        "indicators": indicators,
        "shareholding": shareholding,
        "news": news,
        "verdict": verdict,
    }
