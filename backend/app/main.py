import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from .auth import logout as auth_logout
from .auth import request_otp, validate_session, verify_otp
from .cache import dividends_cache, ipo_cache, results_cache, stock_universe_cache
from .models import (
    DividendsResponse,
    IpoResponse,
    LatestResponse,
    NewsResponse,
    OtpRequest,
    OtpRequestResponse,
    OtpVerifyRequest,
    OtpVerifyResponse,
    ResultAnalysis,
    ResultsResponse,
    SessionCheckResponse,
    StocksResponse,
    StockUniverseResponse,
    TranslateRequest,
    TranslateResponse,
)
from .results import analyze_result_company, attach_related_news
from .scheduler import (
    DIVIDENDS_REFRESH_SECONDS,
    IPO_REFRESH_SECONDS,
    NEWS_REFRESH_SECONDS,
    RESULTS_REFRESH_SECONDS,
    STOCK_UNIVERSE_REFRESH_SECONDS,
    refresh_dividends,
    refresh_ipo,
    refresh_news,
    refresh_results,
    refresh_stock_universe,
    start_scheduler,
    stop_scheduler,
)
from .search import search_news
from .stocks_analysis import aggregate_stock_sentiment
from .store import now_utc, store
from .translate import translate_text

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("main")

COOKIE_NAME = "session_token"

# The frontend now runs on a different domain than the backend (Vercel),
# so the session cookie is genuinely cross-site. Vercel sets VERCEL=1 on
# every deployed function, so this switches automatically: SameSite=None
# + Secure in production (required for a cross-site cookie to be sent at
# all), SameSite=Lax + not-Secure for plain-http local dev (Secure cookies
# are silently rejected by browsers over http://localhost).
IS_DEPLOYED = bool(os.environ.get("VERCEL"))

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,https://marketnews-seven.vercel.app",
    ).split(",")
    if origin.strip()
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="Market News API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _set_session_cookie(response: Response, token: str):
    # No max_age/expires -> browser-session cookie (cleared when the
    # browser/tab closes); SESSION_TTL_HOURS is just a server-side backstop
    # for a tab left open longer than that.
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="none" if IS_DEPLOYED else "lax",
        secure=IS_DEPLOYED,
        path="/",
    )


def _ensure_news_fresh(force: bool = False):
    # Serverless containers each keep their own in-memory store, and the
    # background scheduler thread isn't guaranteed to get CPU time between
    # requests - so on a cold/fresh container the store can otherwise stay
    # empty forever. Refreshing synchronously here (only when actually
    # stale, or when the user explicitly hit the refresh button) makes that
    # particular request slower, but guarantees data instead of silently
    # serving nothing / stale.
    if force or store.is_stale(NEWS_REFRESH_SECONDS + 30):
        refresh_news()


def _ensure_dividends_fresh(force: bool = False):
    if force or dividends_cache.is_stale(DIVIDENDS_REFRESH_SECONDS + 60):
        refresh_dividends()


def _ensure_ipo_fresh(force: bool = False):
    if force or ipo_cache.is_stale(IPO_REFRESH_SECONDS + 60):
        refresh_ipo()


def _ensure_results_fresh(force: bool = False):
    if force or results_cache.is_stale(RESULTS_REFRESH_SECONDS + 60):
        refresh_results()


def _ensure_stock_universe_fresh(force: bool = False):
    if force or stock_universe_cache.is_stale(STOCK_UNIVERSE_REFRESH_SECONDS + 300):
        refresh_stock_universe()


def require_auth(request: Request) -> str:
    """FastAPI dependency: every data endpoint depends on this, so none of
    them are reachable without a valid session cookie. The token itself
    lives only in an HttpOnly cookie - JS on the page can never read it,
    and every request implicitly carries it rather than the frontend
    having to attach an Authorization header by hand.
    """
    token = request.cookies.get(COOKIE_NAME)
    email = validate_session(token)
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return email


@app.get("/api/health")
def health():
    return {"status": "ok", "articles_in_store": store.count()}


@app.post("/api/auth/request-otp", response_model=OtpRequestResponse)
def auth_request_otp(req: OtpRequest):
    return OtpRequestResponse(**request_otp(req.email))


@app.post("/api/auth/verify-otp", response_model=OtpVerifyResponse)
def auth_verify_otp(req: OtpVerifyRequest, response: Response):
    result = verify_otp(req.email, req.code)
    if result["ok"]:
        _set_session_cookie(response, result.pop("token"))
    return OtpVerifyResponse(**result)


@app.get("/api/auth/session", response_model=SessionCheckResponse)
def auth_session(request: Request):
    email = validate_session(request.cookies.get(COOKIE_NAME))
    return SessionCheckResponse(valid=email is not None, email=email)


@app.post("/api/auth/logout")
def auth_logout_endpoint(request: Request, response: Response):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        auth_logout(token)
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        samesite="none" if IS_DEPLOYED else "lax",
        secure=IS_DEPLOYED,
    )
    return {"ok": True}


@app.get("/api/news", response_model=NewsResponse)
def get_news(
    limit: int = Query(50, ge=1, le=200),
    sentiment: str = Query(None, description="Filter: bullish | bearish | neutral"),
    ticker: str = Query(None, description="Filter by related stock ticker"),
    force: bool = Query(False, description="Bypass cache staleness check and refetch now"),
    _email: str = Depends(require_auth),
):
    _ensure_news_fresh(force)
    articles = store.all_sorted()
    if sentiment:
        articles = [a for a in articles if a.sentiment_label == sentiment.lower()]
    if ticker:
        ticker = ticker.upper()
        articles = [a for a in articles if any(s.ticker == ticker for s in a.related_stocks)]
    articles = articles[:limit]
    return NewsResponse(articles=articles, server_time=now_utc(), total=len(articles))


@app.get("/api/news/latest", response_model=LatestResponse)
def get_latest_news(
    since: datetime = Query(..., description="ISO timestamp; returns articles fetched after this time"),
    _email: str = Depends(require_auth),
):
    _ensure_news_fresh()
    articles = store.fetched_after(since)
    return LatestResponse(articles=articles, server_time=now_utc())


@app.get("/api/news/search", response_model=NewsResponse)
async def search(
    q: str = Query(..., min_length=1, description="Stock/company name or ticker to search for"),
    limit: int = Query(40, ge=1, le=100),
    _email: str = Depends(require_auth),
):
    articles = await run_in_threadpool(search_news, q, limit)
    return NewsResponse(articles=articles, server_time=now_utc(), total=len(articles))


@app.get("/api/stocks", response_model=StocksResponse)
def get_stocks(
    limit: int = Query(50, ge=1, le=200),
    force: bool = Query(False, description="Bypass cache staleness check and refetch now"),
    _email: str = Depends(require_auth),
):
    _ensure_news_fresh(force)
    stocks = aggregate_stock_sentiment(limit=limit)
    return StocksResponse(stocks=stocks, server_time=now_utc())


@app.get("/api/stocks/universe", response_model=StockUniverseResponse)
def get_stock_universe(force: bool = Query(False), _email: str = Depends(require_auth)):
    _ensure_stock_universe_fresh(force)
    stocks, _ = stock_universe_cache.get()
    return StockUniverseResponse(stocks=stocks, server_time=now_utc())


@app.get("/api/dividends/upcoming", response_model=DividendsResponse)
def get_upcoming_dividends(
    days: int = Query(4, ge=1, le=4),
    force: bool = Query(False, description="Bypass cache staleness check and refetch now"),
    _email: str = Depends(require_auth),
):
    _ensure_dividends_fresh(force)
    dividends, _ = dividends_cache.get()
    dividends = [d for d in dividends if d["days_away"] <= days]
    return DividendsResponse(dividends=dividends, server_time=now_utc())


@app.get("/api/ipo", response_model=IpoResponse)
def get_ipo(force: bool = Query(False), _email: str = Depends(require_auth)):
    _ensure_ipo_fresh(force)
    ipos, _ = ipo_cache.get()
    return IpoResponse(ipos=ipos, server_time=now_utc())


@app.get("/api/results", response_model=ResultsResponse)
def get_results(
    days: int = Query(4, ge=1, le=4),
    q: str = Query(None, description="Filter by company name or ticker"),
    force: bool = Query(False, description="Bypass cache staleness check and refetch now"),
    _email: str = Depends(require_auth),
):
    _ensure_results_fresh(force)
    results, _ = results_cache.get()
    cutoff_date = (date.today() - timedelta(days=days)).isoformat()
    results = [r for r in results if r["published"][:10] >= cutoff_date]
    if q:
        q_lower = q.lower()
        q_upper = q.upper()
        results = [
            r for r in results
            if q_lower in r["company"].lower()
            or any(s["ticker"] == q_upper for s in r["related_stocks"])
        ]
    results = attach_related_news(results)
    return ResultsResponse(results=results, server_time=now_utc())


@app.get("/api/results/analyze", response_model=ResultAnalysis)
async def analyze_result(
    company: str = Query(..., min_length=1, description="Company name to analyze, e.g. 'Reliance Industries Ltd'"),
    _email: str = Depends(require_auth),
):
    analysis = await run_in_threadpool(analyze_result_company, company)
    return ResultAnalysis(**analysis)


@app.post("/api/translate", response_model=TranslateResponse)
async def translate(req: TranslateRequest, _email: str = Depends(require_auth)):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")
    try:
        translated = await run_in_threadpool(translate_text, req.text, req.target_lang)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Translation service error: {e}")
    return TranslateResponse(original=req.text, translated=translated, target_lang=req.target_lang)
