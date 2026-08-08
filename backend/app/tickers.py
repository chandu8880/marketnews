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
    "TMCV": ("Tata Motors", ["Tata Motors"]),  # post-2025 demerger symbol (commercial vehicles arm kept the name)
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
    "ETERNAL": ("Eternal (Zomato)", ["Zomato", "Eternal Ltd"]),  # renamed from Zomato/ZOMATO in 2024
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
    # --- Additional large-caps (rounds the tracked list out to ~100 for
    # the Top Analysis screen; also improves general news ticker-tagging) ---
    "LICI": ("Life Insurance Corporation of India", ["LIC India", "Life Insurance Corporation"]),
    "TRENT": ("Trent Limited", ["Trent Ltd", "Trent Limited"]),
    "BEL": ("Bharat Electronics", ["Bharat Electronics"]),
    "VBL": ("Varun Beverages", ["Varun Beverages"]),
    "HAL": ("Hindustan Aeronautics", ["Hindustan Aeronautics", "HAL"]),
    "PFC": ("Power Finance Corporation", ["Power Finance Corporation"]),
    "RECLTD": ("REC Limited", ["REC Limited", "REC Ltd"]),
    "INDIGO": ("InterGlobe Aviation", ["InterGlobe Aviation", "IndiGo"]),
    "TVSMOTOR": ("TVS Motor Company", ["TVS Motor"]),
    "ABB": ("ABB India", ["ABB India"]),
    "GODREJCP": ("Godrej Consumer Products", ["Godrej Consumer"]),
    "DABUR": ("Dabur India", ["Dabur India", "Dabur"]),
    "MARICO": ("Marico Limited", ["Marico"]),
    "COLPAL": ("Colgate-Palmolive India", ["Colgate-Palmolive", "Colgate India"]),
    "HAVELLS": ("Havells India", ["Havells"]),
    "AMBUJACEM": ("Ambuja Cements", ["Ambuja Cements", "Ambuja Cement"]),
    "SHREECEM": ("Shree Cement", ["Shree Cement"]),
    "BOSCHLTD": ("Bosch Limited", ["Bosch Ltd", "Bosch Limited"]),
    "MOTHERSON": ("Samvardhana Motherson International", ["Motherson"]),
    "BANDHANBNK": ("Bandhan Bank", ["Bandhan Bank"]),
    "FEDERALBNK": ("Federal Bank", ["Federal Bank"]),
    "IDFCFIRSTB": ("IDFC First Bank", ["IDFC First Bank"]),
    "AUBANK": ("AU Small Finance Bank", ["AU Small Finance Bank"]),
    "POLYCAB": ("Polycab India", ["Polycab"]),
    "TORNTPHARM": ("Torrent Pharmaceuticals", ["Torrent Pharma"]),
    "LUPIN": ("Lupin Limited", ["Lupin"]),
    "AUROPHARMA": ("Aurobindo Pharma", ["Aurobindo Pharma"]),
    "BIOCON": ("Biocon Limited", ["Biocon"]),
    "MPHASIS": ("Mphasis Limited", ["Mphasis"]),
    "LTIM": ("LTIMindtree", ["LTIMindtree", "LTI Mindtree"]),
    "PERSISTENT": ("Persistent Systems", ["Persistent Systems"]),
    "COFORGE": ("Coforge Limited", ["Coforge"]),
    "NAUKRI": ("Info Edge (Naukri)", ["Info Edge", "Naukri.com"]),
    "SRF": ("SRF Limited", ["SRF Ltd", "SRF Limited"]),
    "BERGEPAINT": ("Berger Paints India", ["Berger Paints"]),
    "INDHOTEL": ("Indian Hotels Company", ["Indian Hotels", "Taj Hotels"]),
    "JUBLFOOD": ("Jubilant FoodWorks", ["Jubilant FoodWorks", "Domino's India"]),
    "MUTHOOTFIN": ("Muthoot Finance", ["Muthoot Finance"]),
    "CHOLAFIN": ("Cholamandalam Investment", ["Cholamandalam Investment", "Chola Finance"]),
    "ICICIGI": ("ICICI Lombard General Insurance", ["ICICI Lombard"]),
    "ICICIPRULI": ("ICICI Prudential Life Insurance", ["ICICI Prudential Life"]),
    "SBICARD": ("SBI Cards and Payment Services", ["SBI Cards"]),
    "CGPOWER": ("CG Power and Industrial Solutions", ["CG Power"]),
    "SUZLON": ("Suzlon Energy", ["Suzlon"]),
    "IRFC": ("Indian Railway Finance Corporation", ["IRFC", "Indian Railway Finance"]),
    "BHEL": ("Bharat Heavy Electricals", ["BHEL", "Bharat Heavy Electricals"]),
    "SAIL": ("Steel Authority of India", ["SAIL", "Steel Authority of India"]),
    "NMDC": ("NMDC Limited", ["NMDC"]),
    "NHPC": ("NHPC Limited", ["NHPC"]),
    "TATAPOWER": ("Tata Power Company", ["Tata Power"]),
    "TATACONSUM": ("Tata Consumer Products", ["Tata Consumer"]),
    "TATACOMM": ("Tata Communications", ["Tata Communications"]),
    "UNITDSPR": ("United Spirits", ["United Spirits"]),
    "PAGEIND": ("Page Industries", ["Page Industries"]),
    "MRF": ("MRF Limited", ["MRF Ltd", "MRF Limited"]),
    "ZYDUSLIFE": ("Zydus Lifesciences", ["Zydus Lifesciences", "Zydus Cadila"]),
    "GLAND": ("Gland Pharma", ["Gland Pharma"]),
    "NIFTY": ("Nifty 50", ["Nifty 50", "Nifty50", "Nifty"]),
    "BANKNIFTY": ("Bank Nifty", ["Bank Nifty", "BankNifty"]),
    "SENSEX": ("BSE Sensex", ["Sensex"]),
}

# The above minus the 3 index entries - this is the "Top Analysis" screen's
# tracked universe. Not a scientifically precise NIFTY-100-by-market-cap
# ranking (that would need a reliable ticker->market-cap join we don't have
# a clean free source for), but a curated set of large, liquid, frequently
# covered NSE names that's reliably compatible with the Yahoo Finance and
# moneycontrol symbol lookups the analysis screen depends on.
TOP_ANALYSIS_TICKERS = [t for t in COMPANY_MAP if t not in ("NIFTY", "BANKNIFTY", "SENSEX")]

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
