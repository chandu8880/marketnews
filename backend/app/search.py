"""Search across cached news, backed by a live targeted fetch so a query
for a stock that isn't already in the store (e.g. a smaller company not
covered by the standing RSS feeds) still pulls fresh results from the web
instead of just searching what happened to already be cached.
"""
import logging
from urllib.parse import quote

from .ingest import process_raw_articles
from .news_sources import fetch_feed
from .store import store
from .tickers import COMPANY_MAP

logger = logging.getLogger("search")

SEARCH_FEED_TEMPLATE = (
    "https://news.google.com/rss/search?q=when:14d+{query}&hl=en-IN&gl=IN&ceid=IN:en"
)


def _live_search_fetch(query: str):
    url = SEARCH_FEED_TEMPLATE.format(query=quote(f'"{query}" (stock OR shares OR NSE OR BSE)'))
    try:
        raw = fetch_feed(f"Search: {query}", url)
    except Exception:
        logger.exception("Live search fetch failed for query=%s", query)
        return []
    return raw


def search_news(query: str, limit: int = 60):
    query = query.strip()
    if not query:
        return []

    # If the query matches a known ticker/company, broaden matching to its name variants too.
    query_upper = query.upper()
    extra_terms = [query.lower()]
    if query_upper in COMPANY_MAP:
        extra_terms.append(COMPANY_MAP[query_upper][0].lower())

    raw = _live_search_fetch(query)
    if raw:
        processed = process_raw_articles(raw)
        store.upsert_many(processed)

    articles = store.all_sorted()
    matches = []
    for article in articles:
        haystack = f"{article.title} {article.summary}".lower()
        ticker_hit = any(s.ticker == query_upper for s in article.related_stocks)
        text_hit = any(term in haystack for term in extra_terms)
        if ticker_hit or text_hit:
            matches.append(article)

    return matches[:limit]
