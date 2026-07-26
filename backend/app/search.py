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
    live_articles = []
    if raw:
        live_articles = process_raw_articles(raw)
        store.upsert_many(live_articles)

    # The live fetch above is already scoped to this exact query (Google News
    # relevance-matched it), so those results are trusted as-is - re-checking
    # them against our own narrow ticker list/substring match would silently
    # drop real hits just because Google matched on relevance rather than an
    # exact substring (e.g. a smaller company not in our curated ticker map).
    # The store-wide scan below is purely a *supplement*, surfacing other
    # previously-cached articles about the same query that the live fetch
    # didn't happen to return this time.
    live_ids = {a.id for a in live_articles}
    extra_matches = []
    for article in store.all_sorted():
        if article.id in live_ids:
            continue
        haystack = f"{article.title} {article.summary}".lower()
        ticker_hit = any(s.ticker == query_upper for s in article.related_stocks)
        text_hit = any(term in haystack for term in extra_terms)
        if ticker_hit or text_hit:
            extra_matches.append(article)

    return (live_articles + extra_matches)[:limit]
