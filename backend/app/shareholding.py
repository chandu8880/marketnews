"""FII/DII/Promoter/Public shareholding pattern, quarter by quarter -
sourced live from moneycontrol's stock quote page, which embeds the full
trend as inline JSON in a <script> tag (no separate API call needed once
the page is located).

moneycontrol's own internal stock codes don't match NSE tickers (e.g.
Reliance is "RI", not "RELIANCE"), so this first resolves the ticker to a
quote-page URL via their public autosuggest search, cross-checking the
result against the ticker/company name so a fuzzy match (e.g. "Bajaj"
matching the wrong Bajaj entity) doesn't silently return the wrong
company's data.
"""
import logging
import re

import httpx

logger = logging.getLogger("shareholding")

SEARCH_URL = "https://www.moneycontrol.com/mccode/common/autosuggestion_solr.php"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

_TREND_RE = re.compile(r"var trend_jsn = '(.+?)';")


def _find_quote_url(ticker: str, company_name: str):
    for query in (company_name, ticker):
        try:
            resp = httpx.get(
                SEARCH_URL,
                params={"classic": "true", "query": query, "type": "1", "format": "json"},
                headers=HEADERS,
                timeout=15,
            )
            resp.raise_for_status()
            results = resp.json()
        except Exception:
            logger.exception("moneycontrol search failed for %s", query)
            continue

        for item in results:
            # pdt_dis_nm embeds "ISIN, NSE_SYMBOL, BSE_CODE" - matching our
            # ticker here confirms we've got the right company, not just
            # whatever ranked first for a fuzzy name search.
            if ticker.upper() in item.get("pdt_dis_nm", "").upper():
                return item.get("link_src")
        # First query (company name) found results but none matched the
        # ticker exactly - still worth trying the plainer ticker query below
        # rather than giving up immediately.
    return None


def fetch_shareholding_pattern(ticker: str, company_name: str):
    url = _find_quote_url(ticker, company_name)
    if not url:
        logger.warning("Could not resolve moneycontrol quote page for %s", ticker)
        return None

    try:
        resp = httpx.get(url, headers=HEADERS, timeout=20, follow_redirects=True)
        resp.raise_for_status()
    except Exception:
        logger.exception("Failed to fetch moneycontrol quote page for %s (%s)", ticker, url)
        return None

    m = _TREND_RE.search(resp.text)
    if not m:
        logger.warning("Shareholding trend data not found on page for %s", ticker)
        return None

    import json
    try:
        trend = json.loads(m.group(1))
    except json.JSONDecodeError:
        logger.exception("Failed to parse shareholding trend JSON for %s", ticker)
        return None

    # Each category maps quarter-label -> {"Holding": pct, ...}; collect the
    # union of quarter labels present (they're consistent across categories
    # in practice) and take the most recent 3.
    all_quarters = []
    for cat_data in trend.values():
        for q in cat_data:
            if q not in all_quarters:
                all_quarters.append(q)
    # moneycontrol emits these oldest-first; last 3 = most recent 3 quarters.
    recent_quarters = all_quarters[-3:]

    quarters = []
    for q in recent_quarters:
        entry = {"quarter": q}
        for category in ("Promoter", "FII", "DII", "Public", "Others"):
            cat_data = trend.get(category, {})
            holding = cat_data.get(q, {}).get("Holding")
            entry[category.lower()] = holding
        quarters.append(entry)

    return {"ticker": ticker, "source_url": url, "quarters": quarters}
