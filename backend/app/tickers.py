"""Static company-name / ticker map used to detect which stocks a news article is about.

Kept intentionally simple (no external data provider): a curated list of large,
frequently-in-the-news companies is enough to make the "related stocks" feature
useful without needing an API key.
"""
import re

# NSE ticker -> (company display name, list of name variants to search for in text)
COMPANY_MAP = {
    "RELIANCE": ("Reliance Industries", ["Reliance Industries", "Reliance Ind", "RIL"]),
    "TCS": ("Tata Consultancy Services", ["Tata Consultancy Services", "TCS"]),
    "INFY": ("Infosys", ["Infosys"]),
    "HDFCBANK": ("HDFC Bank", ["HDFC Bank"]),
    "ICICIBANK": ("ICICI Bank", ["ICICI Bank"]),
    "SBIN": ("State Bank of India", ["State Bank of India", "SBI"]),
    "BHARTIARTL": ("Bharti Airtel", ["Bharti Airtel", "Airtel"]),
    "ITC": ("ITC Limited", ["ITC Ltd", "ITC Limited"]),
    "KOTAKBANK": ("Kotak Mahindra Bank", ["Kotak Mahindra Bank", "Kotak Bank"]),
    "LT": ("Larsen & Toubro", ["Larsen & Toubro", "Larsen and Toubro", "L&T"]),
    "HINDUNILVR": ("Hindustan Unilever", ["Hindustan Unilever", "HUL"]),
    "AXISBANK": ("Axis Bank", ["Axis Bank"]),
    "ASIANPAINT": ("Asian Paints", ["Asian Paints"]),
    "MARUTI": ("Maruti Suzuki", ["Maruti Suzuki", "Maruti"]),
    "TATAMOTORS": ("Tata Motors", ["Tata Motors"]),
    "TATASTEEL": ("Tata Steel", ["Tata Steel"]),
    "SUNPHARMA": ("Sun Pharmaceutical", ["Sun Pharma", "Sun Pharmaceutical"]),
    "NTPC": ("NTPC Limited", ["NTPC"]),
    "ONGC": ("Oil and Natural Gas Corporation", ["ONGC", "Oil and Natural Gas Corporation"]),
    "POWERGRID": ("Power Grid Corporation", ["Power Grid Corporation", "Power Grid"]),
    "ULTRACEMCO": ("UltraTech Cement", ["UltraTech Cement", "UltraTech"]),
    "NESTLEIND": ("Nestle India", ["Nestle India"]),
    "TITAN": ("Titan Company", ["Titan Company", "Titan"]),
    "INDUSINDBK": ("IndusInd Bank", ["IndusInd Bank"]),
    "JSWSTEEL": ("JSW Steel", ["JSW Steel"]),
    "COALINDIA": ("Coal India", ["Coal India"]),
    "HINDALCO": ("Hindalco Industries", ["Hindalco"]),
    "GRASIM": ("Grasim Industries", ["Grasim"]),
    "HDFCLIFE": ("HDFC Life Insurance", ["HDFC Life"]),
    "SBILIFE": ("SBI Life Insurance", ["SBI Life"]),
    "DIVISLAB": ("Divi's Laboratories", ["Divi's Laboratories", "Divis Labs"]),
    "DRREDDY": ("Dr Reddy's Laboratories", ["Dr Reddy's", "Dr Reddy"]),
    "CIPLA": ("Cipla", ["Cipla"]),
    "BRITANNIA": ("Britannia Industries", ["Britannia"]),
    "EICHERMOT": ("Eicher Motors", ["Eicher Motors"]),
    "BPCL": ("Bharat Petroleum", ["Bharat Petroleum", "BPCL"]),
    "HEROMOTOCO": ("Hero MotoCorp", ["Hero MotoCorp"]),
    "BAJAJ-AUTO": ("Bajaj Auto", ["Bajaj Auto"]),
    "BAJFINANCE": ("Bajaj Finance", ["Bajaj Finance"]),
    "BAJAJFINSV": ("Bajaj Finserv", ["Bajaj Finserv"]),
    "TECHM": ("Tech Mahindra", ["Tech Mahindra"]),
    "WIPRO": ("Wipro", ["Wipro"]),
    "HCLTECH": ("HCL Technologies", ["HCL Technologies", "HCL Tech"]),
    "M&M": ("Mahindra & Mahindra", ["Mahindra & Mahindra", "Mahindra and Mahindra"]),
    "UPL": ("UPL Limited", ["UPL Ltd", "UPL Limited"]),
    "APOLLOHOSP": ("Apollo Hospitals", ["Apollo Hospitals"]),
    "ADANIENT": ("Adani Enterprises", ["Adani Enterprises"]),
    "ADANIPORTS": ("Adani Ports", ["Adani Ports"]),
    "ADANIGREEN": ("Adani Green Energy", ["Adani Green"]),
    "ADANIPOWER": ("Adani Power", ["Adani Power"]),
    "VEDL": ("Vedanta Limited", ["Vedanta"]),
    "DLF": ("DLF Limited", ["DLF"]),
    "ZOMATO": ("Eternal (Zomato)", ["Zomato", "Eternal Ltd"]),
    "PAYTM": ("One97 Communications (Paytm)", ["Paytm"]),
    "NYKAA": ("FSN E-Commerce (Nykaa)", ["Nykaa"]),
    "IRCTC": ("IRCTC", ["IRCTC"]),
    "PNB": ("Punjab National Bank", ["Punjab National Bank", "PNB"]),
    "BANKBARODA": ("Bank of Baroda", ["Bank of Baroda"]),
    "CANBK": ("Canara Bank", ["Canara Bank"]),
    "GAIL": ("GAIL India", ["GAIL"]),
    "IOC": ("Indian Oil Corporation", ["Indian Oil Corporation", "IOC", "IndianOil"]),
    "SHRIRAMFIN": ("Shriram Finance", ["Shriram Finance"]),
    "PIDILITIND": ("Pidilite Industries", ["Pidilite"]),
    "DMART": ("Avenue Supermarts (DMart)", ["DMart", "Avenue Supermarts"]),
    "SIEMENS": ("Siemens India", ["Siemens"]),
    "NIFTY": ("Nifty 50", ["Nifty 50", "Nifty50", "Nifty"]),
    "BANKNIFTY": ("Bank Nifty", ["Bank Nifty", "BankNifty"]),
    "SENSEX": ("BSE Sensex", ["Sensex"]),
}

_PATTERNS = None


def _get_patterns():
    global _PATTERNS
    if _PATTERNS is None:
        patterns = []
        for ticker, (name, variants) in COMPANY_MAP.items():
            for variant in variants:
                patterns.append((re.compile(r"\b" + re.escape(variant) + r"\b", re.IGNORECASE), ticker, name))
        # Direct cashtag / bare-ticker mentions, e.g. "$AAPL" or standalone "AAPL"
        for ticker in COMPANY_MAP:
            patterns.append((re.compile(r"\$" + ticker + r"\b"), ticker, COMPANY_MAP[ticker][0]))
        _PATTERNS = patterns
    return _PATTERNS


def find_tickers(text: str):
    """Return a list of unique {ticker, name} dicts mentioned in the given text."""
    if not text:
        return []
    found = {}
    for pattern, ticker, name in _get_patterns():
        if ticker in found:
            continue
        if pattern.search(text):
            found[ticker] = name
    return [{"ticker": t, "name": n} for t, n in found.items()]
