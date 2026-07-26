"""IPO grey market premium (GMP) and subscription data, scraped from
ipowatch.in — a publicly accessible, server-rendered IPO tracking site.
(The more commonly cited GMP source, investorgain.com, renders its table
client-side via JS and can't be fetched with a plain HTTP request.)
"""
import logging
import re
from datetime import date, timedelta

import httpx
from dateutil import parser as dateparser
from bs4 import BeautifulSoup

logger = logging.getLogger("ipo")

GMP_URL = "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/"
SUBSCRIPTION_URL = "https://ipowatch.in/ipo-subscription-status-today/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

_NUM_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def _norm_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _first_number(text: str):
    m = _NUM_RE.search(text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def _fetch_table_rows(url: str):
    resp = httpx.get(url, headers=HEADERS, timeout=25, follow_redirects=True)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    table = soup.find("table")
    if not table:
        return []
    rows = table.find_all("tr")
    parsed = []
    for row in rows[1:]:  # skip header row
        cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
        if cells:
            parsed.append(cells)
    return parsed


def fetch_gmp():
    """Columns: IPO Name, IPO GMP*, Trend, Price Band, Est. Listing, Date, Type, Status, Last Updated"""
    try:
        rows = _fetch_table_rows(GMP_URL)
    except Exception:
        logger.exception("Failed to fetch IPO GMP page")
        return []

    results = []
    for cells in rows:
        if len(cells) < 9:
            continue
        name, gmp, trend, price_band, est_listing, date_range, ipo_type, status, last_updated = cells[:9]
        if not name:
            continue
        results.append({
            "company": name,
            "gmp_amount": _first_number(gmp),
            "gmp_trend": trend,
            "price_band": price_band,
            "est_listing_gain": est_listing,
            "date_range": date_range,
            "type": ipo_type,
            "status": status,
            "gmp_last_updated": last_updated,
        })
    return results


def fetch_subscription():
    """Columns: IPO, Type, Closing Date, QIB (X), NII (X), Retail (X), Total (X), Last Updated"""
    try:
        rows = _fetch_table_rows(SUBSCRIPTION_URL)
    except Exception:
        logger.exception("Failed to fetch IPO subscription page")
        return []

    results = []
    for cells in rows:
        if len(cells) < 8:
            continue
        name, ipo_type, closing_date, qib, nii, retail, total, last_updated = cells[:8]
        if not name:
            continue
        results.append({
            "company": name,
            "type": ipo_type,
            "closing_date": closing_date,
            "qib_times": _first_number(qib),
            "nii_times": _first_number(nii),
            "retail_times": _first_number(retail),
            "total_times": _first_number(total),
            "subscription_last_updated": last_updated,
        })
    return results


_STOPWORDS = {"ltd", "limited", "trust", "invit", "the", "and", "company", "co"}


def _name_words(name: str):
    words = re.findall(r"[a-z0-9]+", name.lower())
    return {w for w in words if w not in _STOPWORDS}


def _closest_match(name: str, candidates: dict, candidate_words: dict):
    """Both sites use slightly different company name variants (dropped
    'Limited'/'InvIT' suffixes, inserted parenthetical brand names like
    '(Mala)'), so exact match is tried first, then word-overlap, before
    giving up.
    """
    key = _norm_name(name)
    if key in candidates:
        return candidates[key]

    words = _name_words(name)
    if not words:
        return None
    best_key, best_score = None, 0.0
    for cand_key, cand_words in candidate_words.items():
        if not cand_words:
            continue
        overlap = len(words & cand_words) / min(len(words), len(cand_words))
        if overlap > best_score:
            best_key, best_score = cand_key, overlap
    if best_score >= 0.6:
        return candidates[best_key]
    return None


RECENT_WINDOW_DAYS = 21  # how far back a *closed* IPO stays visible


def _is_recent_enough(closing_date_str: str) -> bool:
    if not closing_date_str:
        return True  # no date info -> don't filter it out
    try:
        parsed = dateparser.parse(closing_date_str, fuzzy=True).date()
    except (ValueError, OverflowError, TypeError):
        return True
    return parsed >= date.today() - timedelta(days=RECENT_WINDOW_DAYS)


def fetch_ipo_data():
    """Fetch GMP + subscription data, merge by company name, and keep only
    IPOs that are upcoming, currently open, or closed within the last
    ~3 weeks (the underlying pages are running historical logs, so without
    this filter the list would include IPOs from months ago).
    """
    gmp_rows = fetch_gmp()
    sub_rows = fetch_subscription()
    sub_by_name = {_norm_name(r["company"]): r for r in sub_rows}
    sub_words_by_name = {_norm_name(r["company"]): _name_words(r["company"]) for r in sub_rows}

    merged = []
    matched_sub_keys = set()
    for row in gmp_rows:
        if row.get("status") not in ("Upcoming", "Open", "Closed"):
            continue
        sub = _closest_match(row["company"], sub_by_name, sub_words_by_name)
        if sub:
            matched_sub_keys.add(_norm_name(sub["company"]))
        merged.append({**row, "subscription": sub})

    # Include IPOs that only appear in the subscription table (GMP not posted yet).
    for row in sub_rows:
        key = _norm_name(row["company"])
        if key in matched_sub_keys:
            continue
        if not _is_recent_enough(row.get("closing_date")):
            continue
        merged.append({
            "company": row["company"],
            "gmp_amount": None,
            "gmp_trend": None,
            "price_band": None,
            "est_listing_gain": None,
            "date_range": None,
            "type": row["type"],
            "status": None,
            "gmp_last_updated": None,
            "subscription": row,
        })

    return merged
