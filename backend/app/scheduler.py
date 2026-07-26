import logging
import os
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from .cache import dividends_cache, ipo_cache, results_cache
from .dividends import fetch_upcoming_dividends
from .ingest import refresh_news
from .ipo import fetch_ipo_data
from .results import fetch_quarterly_results

logger = logging.getLogger("scheduler")

# On Vercel, a blocking startup risks the request that triggered the cold
# start (e.g. a login attempt) timing out before the app can respond at
# all - so there, even the news refresh is deferred to the scheduler
# thread like the other jobs, instead of blocking `lifespan` startup.
IS_DEPLOYED = bool(os.environ.get("VERCEL"))

NEWS_REFRESH_SECONDS = 60
DIVIDENDS_REFRESH_SECONDS = 30 * 60
IPO_REFRESH_SECONDS = 15 * 60
RESULTS_REFRESH_SECONDS = 20 * 60

_scheduler = BackgroundScheduler()


def _now():
    return datetime.now()


def refresh_dividends():
    try:
        dividends_cache.set(fetch_upcoming_dividends(within_days=4))
    except Exception:
        logger.exception("Dividend refresh failed")


def refresh_ipo():
    try:
        ipo_cache.set(fetch_ipo_data())
    except Exception:
        logger.exception("IPO refresh failed")


def refresh_results():
    try:
        results_cache.set(fetch_quarterly_results(within_days=4))
    except Exception:
        logger.exception("Quarterly results refresh failed")


def start_scheduler():
    # Locally, news is populated synchronously so the feed isn't empty on
    # first load. On Vercel this would block the app from responding to
    # anything (including a login attempt) until 12 RSS feeds have been
    # fetched, risking the cold-start request timing out - so there it's
    # deferred to the scheduler thread instead, same as dividends/IPO/results.
    news_kwargs = {}
    if IS_DEPLOYED:
        news_kwargs["next_run_time"] = _now()
    else:
        try:
            refresh_news()
        except Exception:
            logger.exception("Initial news refresh failed")

    _scheduler.add_job(
        refresh_news, "interval", seconds=NEWS_REFRESH_SECONDS,
        id="refresh_news", max_instances=1, coalesce=True, **news_kwargs,
    )
    _scheduler.add_job(
        refresh_dividends, "interval", seconds=DIVIDENDS_REFRESH_SECONDS,
        id="refresh_dividends", max_instances=1, coalesce=True, next_run_time=_now(),
    )
    _scheduler.add_job(
        refresh_ipo, "interval", seconds=IPO_REFRESH_SECONDS,
        id="refresh_ipo", max_instances=1, coalesce=True, next_run_time=_now(),
    )
    _scheduler.add_job(
        refresh_results, "interval", seconds=RESULTS_REFRESH_SECONDS,
        id="refresh_results", max_instances=1, coalesce=True, next_run_time=_now(),
    )
    _scheduler.start()


def stop_scheduler():
    _scheduler.shutdown(wait=False)
