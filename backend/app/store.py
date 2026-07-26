"""Thread-safe in-memory article store.

A background scheduler thread writes new articles while FastAPI's async
request handlers read from it concurrently, so all access goes through a lock.
"""
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .models import Article

MAX_ARTICLES = 500


class ArticleStore:
    def __init__(self):
        self._lock = threading.Lock()
        self._articles: Dict[str, Article] = {}

    def upsert_many(self, articles: List[Article]) -> int:
        """Add new articles (by id). Returns count of newly-added articles."""
        added = 0
        with self._lock:
            for article in articles:
                if article.id not in self._articles:
                    added += 1
                self._articles[article.id] = article
            if len(self._articles) > MAX_ARTICLES:
                ordered = sorted(self._articles.values(), key=lambda a: a.published, reverse=True)
                keep = ordered[:MAX_ARTICLES]
                self._articles = {a.id: a for a in keep}
        return added

    def get(self, article_id: str) -> Optional[Article]:
        with self._lock:
            return self._articles.get(article_id)

    def all_sorted(self) -> List[Article]:
        with self._lock:
            return sorted(self._articles.values(), key=lambda a: a.published, reverse=True)

    def fetched_after(self, since: datetime) -> List[Article]:
        with self._lock:
            items = [a for a in self._articles.values() if a.fetched_at > since]
        return sorted(items, key=lambda a: a.published, reverse=True)

    def count(self) -> int:
        with self._lock:
            return len(self._articles)


store = ArticleStore()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
