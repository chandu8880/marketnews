"""Quarterly financial results announcements, sourced live from BSE's
public announcements API (official exchange data, filtered to the
"Result" category), covering the last N days.
"""
import logging
import re
from datetime import date, timedelta
from urllib.parse import quote

import httpx
from dateutil import parser as dateparser

from .ingest import process_raw_articles
from .news_sources import fetch_feed
from .sentiment import classify, score_text
from .store import store
from .tickers import find_tickers

logger = logging.getLogger("results")

_STOPWORDS = {"ltd", "limited", "the", "and", "company", "co", "india", "pvt", "private"}


def _name_words(name: str):
    words = re.findall(r"[a-z0-9]+", name.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) >= 4}


# --- Profit%/estimate extraction, straight from article text (regex only, no LLM) ---

_UP_WORDS = r"rises?|rose|jumps?|surges?|grows?|grew|climbs?|gains?|soars?|increase[sd]?|higher"
_DOWN_WORDS = r"falls?|fell|declines?|declined|drops?|dropped|slips?|slipped|dips?|dipped|plunges?|shrinks?|lower|decrease[sd]?"
_UP_RE = re.compile(_UP_WORDS + r"|rise|growth|jump|surge|increase", re.I)

_PROFIT_METRIC = r"consolidated\s+net\s+profit|net\s+profit|profit\s+after\s+tax|net\s+income|\bpat\b|\bprofit\b"
_REVENUE_METRIC = r"\brevenue\b|\bearnings\b|\bsales\b"

_PCT_A_TEMPLATE = r"(?P<metric>{metric})\D{{0,25}}?(?P<verb>{up}|{down})\D{{0,10}}?(?P<pct>\d{{1,3}}(?:\.\d+)?)\s*%"
_PCT_B_TEMPLATE = r"(?P<pct>\d{{1,3}}(?:\.\d+)?)\s*%\D{{0,20}}?(?P<verb>rise|growth|jump|surge|increase|decline|fall|drop|dip)\D{{0,10}}?in\D{{0,10}}?(?P<metric>{metric})"

_PROFIT_PAT_A = re.compile(_PCT_A_TEMPLATE.format(metric=_PROFIT_METRIC, up=_UP_WORDS, down=_DOWN_WORDS), re.I)
_PROFIT_PAT_B = re.compile(_PCT_B_TEMPLATE.format(metric=_PROFIT_METRIC), re.I)
_REVENUE_PAT_A = re.compile(_PCT_A_TEMPLATE.format(metric=_REVENUE_METRIC, up=_UP_WORDS, down=_DOWN_WORDS), re.I)
_REVENUE_PAT_B = re.compile(_PCT_B_TEMPLATE.format(metric=_REVENUE_METRIC), re.I)

_BEAT_RE = re.compile(
    r"\bbeats?\b\D{0,30}?\bestimates?\b|\btops?\b\D{0,20}?\bestimates?\b|\bexceeds?\b\D{0,20}?\bestimates?\b", re.I)
_MISS_RE = re.compile(
    r"\bmiss(?:es|ed)?\b\D{0,30}?\bestimates?\b|\bfalls?\s+short\b\D{0,20}?\bestimates?\b|\bbelow\b\D{0,20}?\bestimates?\b", re.I)
_INLINE_RE = re.compile(
    r"\bin\s*[- ]?line\s+with\b\D{0,20}?\bestimates?\b|\bmatch(?:es|ed|ing)?\b\D{0,20}?\bestimates?\b", re.I)


def _extract_pct_change(text: str):
    for metric_type, pat_a, pat_b in (
        ("profit", _PROFIT_PAT_A, _PROFIT_PAT_B),
        ("revenue", _REVENUE_PAT_A, _REVENUE_PAT_B),
    ):
        m = pat_a.search(text) or pat_b.search(text)
        if m:
            d = m.groupdict()
            direction = "up" if _UP_RE.search(d["verb"]) else "down"
            return {"metric": metric_type, "pct": float(d["pct"]), "direction": direction}
    return None


def _extract_estimate_status(text: str):
    if _BEAT_RE.search(text):
        return "beat"
    if _MISS_RE.search(text):
        return "miss"
    if _INLINE_RE.search(text):
        return "in-line"
    return None

BSE_ANN_URL = "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w"
BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.bseindia.com/corporates/ann.html",
}
PAGE_SIZE = 50
MAX_PAGES = 20  # safety cap


def _fetch_page(from_date: date, to_date: date, page: int):
    params = {
        "pageno": page,
        "strCat": "Result",
        "strPrevDate": from_date.strftime("%Y%m%d"),
        "strToDate": to_date.strftime("%Y%m%d"),
        "strScrip": "",
        "strSearch": "P",
        "strType": "C",
    }
    resp = httpx.get(BSE_ANN_URL, params=params, headers=BSE_HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.json()


def fetch_quarterly_results(within_days: int = 4):
    """Return quarterly results announcements filed in the last `within_days`
    days, newest first, each tagged with a bullish/bearish/neutral read of
    the headline text (e.g. "EPS Beat", "Net Profit Declines").
    """
    today = date.today()
    from_date = today - timedelta(days=within_days)

    all_rows = []
    try:
        first = _fetch_page(from_date, today, 1)
        all_rows.extend(first.get("Table", []))
        total = first.get("Table1", [{}])[0].get("ROWCNT", len(all_rows))
        page = 2
        while len(all_rows) < total and page <= MAX_PAGES:
            data = _fetch_page(from_date, today, page)
            rows = data.get("Table", [])
            if not rows:
                break
            all_rows.extend(rows)
            page += 1
    except Exception:
        logger.exception("Failed to fetch BSE quarterly results")
        return []

    results = []
    for row in all_rows:
        company = (row.get("SLONGNAME") or "").strip()
        headline = (row.get("HEADLINE") or row.get("NEWSSUB") or "").strip()
        if not company or not headline:
            continue
        try:
            published = dateparser.parse(row.get("News_submission_dt") or row.get("NEWS_DT"))
        except (ValueError, TypeError):
            continue

        score = score_text(headline)
        label = classify(score)
        tickers = find_tickers(f"{company} {headline}")

        results.append({
            "company": company,
            "scrip_code": row.get("SCRIP_CD"),
            "headline": headline,
            "published": published.isoformat(),
            "link": row.get("NSURL") or "",
            "sentiment_label": label,
            "sentiment_score": round(score, 4),
            "related_stocks": tickers,
        })

    results.sort(key=lambda r: r["published"], reverse=True)
    return results


def attach_related_news(results, limit_per_result: int = 3):
    """Return a copy of `results` with each item enriched with a handful of
    recent news articles about the same stock, so the terse BSE filing
    headline ("Results for the quarter ended...") sits alongside actual
    coverage/commentary on that result. Matches by ticker first (cheap,
    precise), falling back to company-name word overlap for companies too
    small to be in our tracked ticker list.

    Returns new dicts rather than mutating `results` in place, since the
    caller passes in the shared cached list and related news depends on the
    (separately, more frequently refreshed) article store at request time.
    """
    articles = store.all_sorted()
    enriched = []

    for r in results:
        tickers = {s["ticker"] for s in r["related_stocks"]}
        company_words = _name_words(r["company"])
        matched = []
        for article in articles:
            article_tickers = {s.ticker for s in article.related_stocks}
            hit = bool(tickers & article_tickers)
            if not hit and company_words:
                haystack_words = _name_words(f"{article.title} {article.summary}")
                hit = len(company_words & haystack_words) >= min(2, len(company_words))
            if hit:
                matched.append(article)
            if len(matched) >= limit_per_result:
                break
        enriched.append({
            **r,
            "related_news": [
                {
                    "id": a.id,
                    "title": a.title,
                    "source": a.source,
                    "link": a.link,
                    "published": a.published,
                    "sentiment_label": a.sentiment_label,
                }
                for a in matched
            ],
        })

    return enriched


_ANALYZE_SEARCH_TEMPLATE = (
    "https://news.google.com/rss/search?q=when:14d+{query}&hl=en-IN&gl=IN&ceid=IN:en"
)


def analyze_result_company(company: str, max_articles: int = 8):
    """Live-search news coverage of `company`'s quarterly results and pull
    out, via regex over the actual article text (no LLM), whatever the
    coverage says about the profit/revenue % change and whether it beat,
    missed, or was in line with analyst estimates. Returns None fields for
    whatever isn't stated in the coverage we find, rather than guessing.
    """
    query = quote(f'"{company}" results (profit OR earnings OR revenue) (beat OR miss OR estimate OR YoY)')
    url = _ANALYZE_SEARCH_TEMPLATE.format(query=query)
    try:
        raw = fetch_feed(f"Results analysis: {company}", url)
    except Exception:
        logger.exception("Live results-analysis fetch failed for company=%s", company)
        raw = []

    articles = process_raw_articles(raw[:max_articles]) if raw else []
    if articles:
        store.upsert_many(articles)

    profit_signal = None
    estimate_status = None
    supporting = []

    for article in articles:
        text = f"{article.title}. {article.summary}"
        pct = _extract_pct_change(text)
        status = _extract_estimate_status(text)
        if pct or status:
            supporting.append({
                "id": article.id,
                "title": article.title,
                "source": article.source,
                "link": article.link,
                "published": article.published,
                "sentiment_label": article.sentiment_label,
            })
        if pct and (profit_signal is None or (profit_signal["metric"] != "profit" and pct["metric"] == "profit")):
            profit_signal = pct
        if status and estimate_status is None:
            estimate_status = status
        if len(supporting) >= 3:
            break

    return {
        "profit_change": profit_signal,
        "estimate_status": estimate_status,
        "supporting_articles": supporting,
        "searched": True,
    }
