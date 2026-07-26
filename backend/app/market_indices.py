"""Live values for the three headline indices shown at the top of the
Overview screen: Nifty 50, Sensex (both via Yahoo Finance's free,
unauthenticated chart API), and GIFT Nifty (Nifty's pre-market/overnight
indicator, traded on NSE's International Exchange in GIFT City - not
covered by Yahoo, so scraped from moneycontrol's live global-indices table
instead, which renders it server-side in a plain HTML table).
"""
import logging
import re

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("market_indices")

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

GIFT_NIFTY_URL = "https://www.moneycontrol.com/indian-indices/gift-nifty-90.html"
MC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

YAHOO_INDICES = [
    {"name": "NIFTY 50", "symbol": "^NSEI"},
    {"name": "SENSEX", "symbol": "^BSESN"},
]

_NUM_RE = re.compile(r"[-+]?[\d,]*\.?\d+")


def _first_number(text: str):
    m = _NUM_RE.search(text.replace(",", ""))
    if not m:
        return None
    try:
        return float(m.group().replace(",", ""))
    except ValueError:
        return None


def _fetch_yahoo_index(name: str, symbol: str):
    try:
        resp = httpx.get(
            YAHOO_CHART_URL.format(symbol=symbol),
            headers=YAHOO_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        meta = resp.json()["chart"]["result"][0]["meta"]
        price = meta["regularMarketPrice"]
        prev_close = meta["chartPreviousClose"]
        change = price - prev_close
        change_pct = (change / prev_close) * 100 if prev_close else 0
        return {
            "name": name,
            "value": round(price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
        }
    except Exception:
        logger.exception("Failed to fetch Yahoo index %s (%s)", name, symbol)
        return None


def _fetch_gift_nifty():
    try:
        resp = httpx.get(GIFT_NIFTY_URL, headers=MC_HEADERS, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")

        link = soup.find("a", string=re.compile(r"GIFT\s*NIFTY", re.I))
        if not link:
            logger.warning("GIFT NIFTY row not found on moneycontrol page")
            return None
        row = link.find_parent("tr")
        cells = row.find_all("td")
        if len(cells) < 4:
            return None

        value = _first_number(cells[1].get_text())
        change = _first_number(cells[2].get_text())
        change_pct = _first_number(cells[3].get_text())
        if value is None:
            return None
        # moneycontrol shows losses in a "red_color" span without an explicit
        # minus sign on the value/percent columns - only the change column
        # reliably carries the sign, so mirror it onto %change if needed.
        if change is not None and change < 0 and change_pct is not None and change_pct > 0:
            change_pct = -change_pct

        return {
            "name": "GIFT NIFTY",
            "value": round(value, 2),
            "change": round(change, 2) if change is not None else None,
            "change_pct": round(change_pct, 2) if change_pct is not None else None,
        }
    except Exception:
        logger.exception("Failed to fetch GIFT NIFTY from moneycontrol")
        return None


def fetch_market_indices():
    """Returns [GIFT NIFTY, NIFTY 50, SENSEX] - whichever of the three
    succeed; a failure on one source never blocks the other two.
    """
    results = []

    gift = _fetch_gift_nifty()
    if gift:
        results.append(gift)

    for idx in YAHOO_INDICES:
        data = _fetch_yahoo_index(idx["name"], idx["symbol"])
        if data:
            results.append(data)

    return results
