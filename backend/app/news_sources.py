"""RSS feed definitions and fetch/parse logic for pulling market news
from multiple trusted, publicly available sources (no API key required).
"""
import hashlib
import logging
from datetime import datetime, timezone

import feedparser
from dateutil import parser as dateparser

logger = logging.getLogger("news_sources")

FEEDS = [
    {"source": "Moneycontrol Business", "url": "https://www.moneycontrol.com/rss/business.xml"},
    {"source": "Moneycontrol Markets", "url": "https://www.moneycontrol.com/rss/marketreports.xml"},
    {"source": "Moneycontrol Latest", "url": "https://www.moneycontrol.com/rss/latestnews.xml"},
    {"source": "Economic Times Markets", "url": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"},
    {"source": "Economic Times Top Stories", "url": "https://economictimes.indiatimes.com/rssfeedstopstories.cms"},
    {"source": "LiveMint Markets", "url": "https://www.livemint.com/rss/markets"},
    {"source": "LiveMint Money", "url": "https://www.livemint.com/rss/money"},
    {"source": "The Hindu BusinessLine Markets", "url": "https://www.thehindubusinessline.com/markets/feeder/default.rss"},
    {"source": "Google News India Markets", "url": "https://news.google.com/rss/search?q=when:24h+(NSE+OR+Sensex+OR+Nifty+OR+BSE)&hl=en-IN&gl=IN&ceid=IN:en"},
    # Official exchange / regulator feeds — corporate disclosures and notices
    # straight from NSE/BSE/SEBI rather than media coverage of them.
    {"source": "NSE Corporate Announcements", "url": "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml", "max_items": 40},
    {"source": "BSE Notices", "url": "https://www.bseindia.com/data/xml/notices.xml"},
    {"source": "SEBI Press Releases", "url": "https://www.sebi.gov.in/sebirss.xml"},
]

# feedparser needs a browser-like User-Agent for some Indian publishers
# (Moneycontrol, Economic Times) or they return empty/blocked responses.
FEED_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def _make_id(entry) -> str:
    key = entry.get("id") or entry.get("link") or entry.get("title", "")
    return hashlib.sha256(key.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _parse_published(entry):
    for field in ("published", "updated", "pubDate"):
        val = entry.get(field)
        if val:
            try:
                dt = dateparser.parse(val)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except (ValueError, OverflowError):
                continue
    return datetime.now(timezone.utc)


def fetch_feed(source: str, url: str, max_items: int = None):
    """Fetch and parse a single RSS feed. Returns a list of normalized article dicts.
    Failures on one feed must never break the others, so errors are caught and logged.
    """
    articles = []
    try:
        parsed = feedparser.parse(url, request_headers=FEED_REQUEST_HEADERS)
        if parsed.bozo and not parsed.entries:
            logger.warning("Feed %s (%s) failed to parse: %s", source, url, parsed.get("bozo_exception"))
            return articles
        entries = parsed.entries[:max_items] if max_items else parsed.entries
        for entry in entries:
            title = entry.get("title", "").strip()
            if not title:
                continue
            summary = entry.get("summary", "") or entry.get("description", "")
            articles.append({
                "id": _make_id(entry),
                "source": source,
                "title": title,
                "summary": summary,
                "link": entry.get("link", ""),
                "published": _parse_published(entry),
            })
    except Exception:
        logger.exception("Error fetching feed %s (%s)", source, url)
    return articles


def fetch_all_feeds():
    """Fetch every configured feed and return a flat list of normalized articles."""
    all_articles = []
    for feed in FEEDS:
        all_articles.extend(fetch_feed(feed["source"], feed["url"], feed.get("max_items")))
    return all_articles
