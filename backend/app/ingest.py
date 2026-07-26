import logging

from .llm_sentiment import classify_with_llm
from .models import Article, RelatedStock
from .news_sources import fetch_all_feeds
from .sentiment import classify, score_text
from .store import now_utc, store
from .tickers import find_tickers

logger = logging.getLogger("ingest")


def process_raw_articles(raw_articles) -> list[Article]:
    """Score sentiment and tag related stocks for a batch of raw feed
    entries, returning fully-formed Article objects (not yet stored).

    Feeds are re-fetched in full on every refresh cycle, so most raw
    entries here are ones we've already scored on a previous cycle -
    those are reused as-is rather than re-classified, both to avoid
    wasted work and because re-classifying would burn through the free
    LLM API's rate limit for headlines that haven't changed.
    """
    fetched_at = now_utc()
    processed = []
    for raw in raw_articles:
        existing = store.get(raw["id"])
        if existing is not None:
            processed.append(existing)
            continue

        text = f"{raw['title']}. {raw['summary']}"
        score = score_text(text)
        label = classify(score)
        llm_result = classify_with_llm(text)
        if llm_result is not None:
            label, score = llm_result
        tickers = find_tickers(text)
        related = [
            RelatedStock(ticker=t["ticker"], name=t["name"], sentiment=label)
            for t in tickers
        ]
        processed.append(Article(
            id=raw["id"],
            source=raw["source"],
            title=raw["title"],
            summary=raw["summary"],
            link=raw["link"],
            published=raw["published"],
            fetched_at=fetched_at,
            sentiment_score=round(score, 4),
            sentiment_label=label,
            related_stocks=related,
        ))
    return processed


def refresh_news() -> int:
    """Fetch all feeds, score sentiment, tag related stocks, and store new articles.
    Returns the number of newly added articles.
    """
    raw_articles = fetch_all_feeds()
    processed = process_raw_articles(raw_articles)
    added = store.upsert_many(processed)
    logger.info("Refreshed news: %d fetched, %d new, %d total in store", len(processed), added, store.count())
    return added
