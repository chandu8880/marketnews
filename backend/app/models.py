from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class OtpRequest(BaseModel):
    email: str


class OtpRequestResponse(BaseModel):
    ok: bool
    error: Optional[str] = None
    dev_otp: Optional[str] = None
    expires_in_seconds: Optional[int] = None
    emailed: Optional[bool] = None


class OtpVerifyRequest(BaseModel):
    email: str
    code: str


class OtpVerifyResponse(BaseModel):
    ok: bool
    error: Optional[str] = None


class SessionCheckResponse(BaseModel):
    valid: bool
    email: Optional[str] = None


class RelatedStock(BaseModel):
    ticker: str
    name: str
    sentiment: str  # "bullish" | "bearish" | "neutral"


class Article(BaseModel):
    id: str
    source: str
    title: str
    summary: str
    link: str
    published: datetime
    fetched_at: datetime
    sentiment_score: float
    sentiment_label: str  # "bullish" | "bearish" | "neutral"
    related_stocks: List[RelatedStock]


class TranslateRequest(BaseModel):
    text: str
    target_lang: str = "te"


class TranslateResponse(BaseModel):
    original: str
    translated: str
    target_lang: str


class NewsResponse(BaseModel):
    articles: List[Article]
    server_time: datetime
    total: int


class LatestResponse(BaseModel):
    articles: List[Article]
    server_time: datetime


class StockArticleRef(BaseModel):
    id: str
    title: str
    source: str
    link: str
    published: datetime
    sentiment_label: str


class StockAnalysis(BaseModel):
    ticker: str
    name: str
    mentions: int
    bullish_count: int
    bearish_count: int
    neutral_count: int
    net_score: float
    overall_sentiment: str
    latest_articles: List[StockArticleRef]


class StocksResponse(BaseModel):
    stocks: List[StockAnalysis]
    server_time: datetime


class DividendItem(BaseModel):
    symbol: str
    company: str
    ex_date: str
    days_away: int
    dividend_type: str
    amount: Optional[float]
    purpose: str


class DividendsResponse(BaseModel):
    dividends: List[DividendItem]
    server_time: datetime


class QuarterlyResultItem(BaseModel):
    company: str
    scrip_code: Optional[int]
    headline: str
    published: datetime
    link: str
    sentiment_label: str
    sentiment_score: float
    related_stocks: List[dict]
    related_news: List[StockArticleRef] = []


class ResultsResponse(BaseModel):
    results: List[QuarterlyResultItem]
    server_time: datetime


class ProfitChangeSignal(BaseModel):
    metric: str  # "profit" | "revenue"
    pct: float
    direction: str  # "up" | "down"


class ResultAnalysis(BaseModel):
    profit_change: Optional[ProfitChangeSignal]
    estimate_status: Optional[str]  # "beat" | "miss" | "in-line" | None
    supporting_articles: List[StockArticleRef]
    searched: bool


class IpoSubscription(BaseModel):
    type: str
    closing_date: str
    qib_times: Optional[float]
    nii_times: Optional[float]
    retail_times: Optional[float]
    total_times: Optional[float]
    subscription_last_updated: str


class IpoItem(BaseModel):
    company: str
    gmp_amount: Optional[float]
    gmp_trend: Optional[str]
    price_band: Optional[str]
    est_listing_gain: Optional[str]
    date_range: Optional[str]
    type: Optional[str]
    status: Optional[str]
    gmp_last_updated: Optional[str]
    subscription: Optional[IpoSubscription]


class IpoResponse(BaseModel):
    ipos: List[IpoItem]
    server_time: datetime


class StockUniverseItem(BaseModel):
    symbol: str
    name: str


class StockUniverseResponse(BaseModel):
    stocks: List[StockUniverseItem]
    server_time: datetime


class MarketIndex(BaseModel):
    name: str
    value: float
    change: Optional[float]
    change_pct: Optional[float]


class MarketIndicesResponse(BaseModel):
    indices: List[MarketIndex]
    server_time: datetime


class StockPriceStats(BaseModel):
    ticker: str
    price: Optional[float]
    week52_low: Optional[float]
    week52_avg: Optional[float]
    week52_high: Optional[float]


class TopStockListItem(BaseModel):
    ticker: str
    name: str
    mentions: int
    overall_sentiment: str
    net_score: float


class TopStocksListResponse(BaseModel):
    stocks: List[TopStockListItem]
    server_time: datetime


class ShareholdingQuarter(BaseModel):
    quarter: str
    promoter: Optional[float]
    fii: Optional[float]
    dii: Optional[float]
    public: Optional[float]
    others: Optional[float]


class ShareholdingData(BaseModel):
    ticker: str
    source_url: str
    quarters: List[ShareholdingQuarter]


class IndicatorData(BaseModel):
    ticker: str
    rsi: Optional[float]
    rsi_signal: Optional[str]
    stoch_rsi: Optional[float]
    cci: Optional[float]
    cci_signal: Optional[str]
    mfi: Optional[float]
    mfi_signal: Optional[str]
    macd: Optional[float]
    macd_signal_line: Optional[float]
    macd_histogram: Optional[float]
    macd_signal: Optional[str]
    vwap: Optional[float]
    plus_di: Optional[float]
    minus_di: Optional[float]
    di_signal: Optional[str]


class VerdictData(BaseModel):
    verdict: str
    confidence: int
    reasoning: str
    model: str


class StockAnalysisResponse(BaseModel):
    ticker: str
    name: str
    indicators: Optional[IndicatorData]
    shareholding: Optional[ShareholdingData]
    news: List[StockArticleRef]
    verdict: Optional[VerdictData]
