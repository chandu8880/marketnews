"""Upcoming dividend corporate actions, sourced live from BSE's public
corporate-actions API (official exchange data, no API key required).
"""
import logging
import re
from datetime import date, datetime, timedelta

import httpx

logger = logging.getLogger("dividends")

BSE_CORP_ACTIONS_URL = "https://api.bseindia.com/BseIndiaAPI/api/DefaultData/w"
BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.bseindia.com/corporates/corporate_act.aspx",
}
BSE_PARAMS = {
    "json": '{"Grp":"","bDate":"Alert","frDt":"","toDt":"","segment":"Equity"}'
}

_AMOUNT_RE = re.compile(r"Rs\.?\s*-?\s*([\d.]+)")


def _parse_amount(purpose: str):
    m = _AMOUNT_RE.search(purpose)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _dividend_type(purpose: str) -> str:
    for label in ("Interim Dividend", "Final Dividend", "Special Dividend", "Dividend"):
        if label in purpose:
            return label
    return "Dividend"


def fetch_upcoming_dividends(within_days: int = 4):
    """Return dividend-paying stocks whose ex-date falls within the next
    `within_days` days (inclusive of today), sorted by ex-date ascending.
    """
    try:
        resp = httpx.get(BSE_CORP_ACTIONS_URL, params=BSE_PARAMS, headers=BSE_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("Failed to fetch BSE corporate actions")
        return []

    today = date.today()
    cutoff = today + timedelta(days=within_days)

    results = []
    for item in data:
        purpose = item.get("Purpose", "")
        if "Dividend" not in purpose:
            continue
        exdate_str = item.get("exdate", "")
        try:
            ex_date = datetime.strptime(exdate_str, "%Y%m%d").date()
        except ValueError:
            continue
        if not (today <= ex_date <= cutoff):
            continue
        results.append({
            "symbol": item.get("short_name", "").strip(),
            "company": item.get("long_name", "").strip(),
            "ex_date": ex_date.isoformat(),
            "days_away": (ex_date - today).days,
            "dividend_type": _dividend_type(purpose),
            "amount": _parse_amount(purpose),
            "purpose": purpose.strip(),
        })

    results.sort(key=lambda r: r["ex_date"])
    return results
