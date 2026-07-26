"""Aggregates the per-article sentiment/ticker tagging (already computed in
ingest.py) into one bullish/bearish view per stock, across all news
currently in the store.
"""
from .store import store


def aggregate_stock_sentiment(limit: int = 100):
    articles = store.all_sorted()

    per_ticker = {}
    for article in articles:
        for stock in article.related_stocks:
            entry = per_ticker.setdefault(stock.ticker, {
                "ticker": stock.ticker,
                "name": stock.name,
                "bullish_count": 0,
                "bearish_count": 0,
                "neutral_count": 0,
                "score_sum": 0.0,
                "mentions": 0,
                "latest_articles": [],
            })
            entry["mentions"] += 1
            entry["score_sum"] += article.sentiment_score
            entry[f"{stock.sentiment}_count"] += 1
            if len(entry["latest_articles"]) < 3:
                entry["latest_articles"].append({
                    "id": article.id,
                    "title": article.title,
                    "source": article.source,
                    "link": article.link,
                    "published": article.published,
                    "sentiment_label": article.sentiment_label,
                })

    results = []
    for entry in per_ticker.values():
        net_score = entry["score_sum"] / entry["mentions"] if entry["mentions"] else 0.0
        if net_score >= 0.2:
            overall = "bullish"
        elif net_score <= -0.2:
            overall = "bearish"
        else:
            overall = "neutral"
        results.append({
            "ticker": entry["ticker"],
            "name": entry["name"],
            "mentions": entry["mentions"],
            "bullish_count": entry["bullish_count"],
            "bearish_count": entry["bearish_count"],
            "neutral_count": entry["neutral_count"],
            "net_score": round(net_score, 4),
            "overall_sentiment": overall,
            "latest_articles": entry["latest_articles"],
        })

    results.sort(key=lambda r: (r["mentions"], abs(r["net_score"])), reverse=True)
    return results[:limit]
