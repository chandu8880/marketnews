"""The full universe of BSE/NSE-listed company names+symbols, sourced from
BSE's public scrip-master API. Used to power "search any Indian stock"
autocomplete, independent of the much smaller set of ~65 tickers we
recognize/tag inside news text (tickers.py) - that curated list stays as
the news-tagging source of truth, this is purely for search suggestions.
"""
import logging

import httpx

logger = logging.getLogger("stock_universe")

BSE_SCRIPS_URL = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
BSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://www.bseindia.com/corporates/List_Scrips.html",
}
BSE_PARAMS = {
    "Group": "",
    "Scripcode": "",
    "industry": "",
    "segment": "Equity",
    "status": "Active",
}


def fetch_stock_universe():
    """Return every active BSE-listed equity as {symbol, name}, deduped and
    sorted by name. This changes rarely (new listings/delistings only), so
    it's refreshed on a long interval rather than every request.
    """
    try:
        resp = httpx.get(BSE_SCRIPS_URL, params=BSE_PARAMS, headers=BSE_HEADERS, timeout=25)
        resp.raise_for_status()
        rows = resp.json()
    except Exception:
        logger.exception("Failed to fetch BSE scrip master")
        return []

    seen = set()
    stocks = []
    for row in rows:
        symbol = (row.get("scrip_id") or "").strip()
        name = (row.get("Issuer_Name") or row.get("Scrip_Name") or "").strip()
        if not symbol or not name or symbol in seen:
            continue
        seen.add(symbol)
        stocks.append({"symbol": symbol, "name": name})

    stocks.sort(key=lambda s: s["name"])
    return stocks
