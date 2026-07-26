"""Thread-safe cache for data refreshed on a schedule (dividends, IPO GMP)
rather than served live per-request, since both involve a handful of
external HTTP calls that are too slow to repeat on every page load.
"""
import threading

from .store import now_utc


class TimedCache:
    def __init__(self):
        self._lock = threading.Lock()
        self._data = []
        self._updated_at = None

    def set(self, data):
        with self._lock:
            self._data = data
            self._updated_at = now_utc()

    def get(self):
        with self._lock:
            return list(self._data), self._updated_at


dividends_cache = TimedCache()
ipo_cache = TimedCache()
results_cache = TimedCache()
