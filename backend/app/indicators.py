"""Technical indicators (RSI, Stochastic RSI, CCI, MFI, MACD, VWAP, +DI/-DI)
computed from daily OHLCV history pulled from Yahoo Finance's free chart
API. Implemented directly with plain Python (no numpy/pandas/ta-lib) since
these are all standard, well-defined formulas and the data volumes here
(a few hundred daily candles) don't need a vectorized library.
"""
import logging

import httpx

logger = logging.getLogger("indicators")

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
}

_INDEX_SYMBOLS = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN"}


def _yahoo_symbol(ticker: str) -> str:
    return _INDEX_SYMBOLS.get(ticker, f"{ticker}.NS")


def fetch_ohlcv(ticker: str, range_: str = "6mo", interval: str = "1d"):
    """Returns dict of parallel lists {opens, highs, lows, closes, volumes}
    (None entries for any candle missing data already dropped), or None on
    failure.
    """
    try:
        resp = httpx.get(
            YAHOO_CHART_URL.format(symbol=_yahoo_symbol(ticker)),
            params={"range": range_, "interval": interval},
            headers=YAHOO_HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()["chart"]["result"][0]
        quote = result["indicators"]["quote"][0]
    except Exception:
        logger.exception("Failed to fetch OHLCV for %s", ticker)
        return None

    opens, highs, lows, closes, volumes = [], [], [], [], []
    for o, h, l, c, v in zip(
        quote.get("open", []), quote.get("high", []), quote.get("low", []),
        quote.get("close", []), quote.get("volume", []),
    ):
        if None in (o, h, l, c):
            continue
        opens.append(o)
        highs.append(h)
        lows.append(l)
        closes.append(c)
        volumes.append(v or 0)

    if len(closes) < 20:
        logger.warning("Not enough OHLCV candles for %s (%d)", ticker, len(closes))
        return None

    return {"opens": opens, "highs": highs, "lows": lows, "closes": closes, "volumes": volumes}


def _ema_series(values, period):
    """Full EMA series (not just the latest value) - needed as a building
    block for MACD, which is itself the difference of two EMA series.
    """
    if len(values) < period:
        return []
    k = 2 / (period + 1)
    ema = [sum(values[:period]) / period]
    for v in values[period:]:
        ema.append(v * k + ema[-1] * (1 - k))
    return ema


def _wilder_smooth(values, period):
    """Wilder's smoothing (used by RSI, ADX/DI, and their peers) - an EMA
    variant with alpha=1/period instead of the usual 2/(period+1).
    """
    if len(values) < period:
        return []
    smoothed = [sum(values[:period])]
    for v in values[period:]:
        smoothed.append(smoothed[-1] - smoothed[-1] / period + v)
    return smoothed


def compute_rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsi_series = []
    for i in range(period, len(deltas)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rs = avg_gain / avg_loss if avg_loss != 0 else float("inf")
        rsi_series.append(100 - 100 / (1 + rs))
    return rsi_series  # rsi_series[-1] is the latest RSI


def compute_stoch_rsi(closes, rsi_period=14, stoch_period=14):
    rsi_series = compute_rsi(closes, rsi_period)
    if not rsi_series or len(rsi_series) < stoch_period:
        return None
    window = rsi_series[-stoch_period:]
    lo, hi = min(window), max(window)
    if hi == lo:
        return 50.0
    return (rsi_series[-1] - lo) / (hi - lo) * 100


def compute_cci(highs, lows, closes, period=20):
    if len(closes) < period:
        return None
    tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    window = tp[-period:]
    sma = sum(window) / period
    mean_dev = sum(abs(x - sma) for x in window) / period
    if mean_dev == 0:
        return 0.0
    return (tp[-1] - sma) / (0.015 * mean_dev)


def compute_mfi(highs, lows, closes, volumes, period=14):
    if len(closes) < period + 1:
        return None
    tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    raw_flow = [t * v for t, v in zip(tp, volumes)]

    pos_flow, neg_flow = [], []
    for i in range(1, len(tp)):
        if tp[i] > tp[i - 1]:
            pos_flow.append(raw_flow[i])
            neg_flow.append(0)
        elif tp[i] < tp[i - 1]:
            pos_flow.append(0)
            neg_flow.append(raw_flow[i])
        else:
            pos_flow.append(0)
            neg_flow.append(0)

    pos_sum = sum(pos_flow[-period:])
    neg_sum = sum(neg_flow[-period:])
    if neg_sum == 0:
        return 100.0
    money_ratio = pos_sum / neg_sum
    return 100 - 100 / (1 + money_ratio)


def compute_macd(closes, fast=12, slow=26, signal=9):
    if len(closes) < slow + signal:
        return None
    ema_fast = _ema_series(closes, fast)
    ema_slow = _ema_series(closes, slow)
    # Align both series to the same (shorter, slow-EMA-limited) length.
    offset = len(ema_fast) - len(ema_slow)
    macd_line = [f - s for f, s in zip(ema_fast[offset:], ema_slow)]
    if len(macd_line) < signal:
        return None
    signal_line = _ema_series(macd_line, signal)
    macd_latest = macd_line[-1]
    signal_latest = signal_line[-1]
    return {
        "macd": macd_latest,
        "signal": signal_latest,
        "histogram": macd_latest - signal_latest,
    }


def compute_vwap(highs, lows, closes, volumes):
    tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
    total_vol = sum(volumes)
    if total_vol == 0:
        return None
    return sum(t * v for t, v in zip(tp, volumes)) / total_vol


def compute_di_adx(highs, lows, closes, period=14):
    """+DI/-DI (trend direction) plus ADX (trend strength) - the standard
    DMI trio; ADX is always shown alongside DI in every charting platform
    (TradingView, Kite, etc.) since DI alone tells you direction but not
    whether that direction is actually a strong trend or just noise.
    """
    if len(closes) < period * 2:
        return None
    plus_dm, minus_dm, tr = [], [], []
    for i in range(1, len(closes)):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm.append(up_move if (up_move > down_move and up_move > 0) else 0)
        minus_dm.append(down_move if (down_move > up_move and down_move > 0) else 0)
        tr.append(max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        ))

    smoothed_plus = _wilder_smooth(plus_dm, period)
    smoothed_minus = _wilder_smooth(minus_dm, period)
    smoothed_tr = _wilder_smooth(tr, period)
    if not smoothed_tr or smoothed_tr[-1] == 0:
        return None

    # DX at every smoothed point (not just the latest) - ADX is Wilder's
    # smoothing applied to this whole DX series, not to a single value.
    dx_series = []
    for pdm, mdm, t in zip(smoothed_plus, smoothed_minus, smoothed_tr):
        if t == 0:
            dx_series.append(0.0)
            continue
        pdi_i = 100 * pdm / t
        mdi_i = 100 * mdm / t
        denom = pdi_i + mdi_i
        dx_series.append(100 * abs(pdi_i - mdi_i) / denom if denom != 0 else 0.0)

    adx = None
    if len(dx_series) >= period:
        adx = sum(dx_series[:period]) / period
        for dx in dx_series[period:]:
            adx = (adx * (period - 1) + dx) / period

    plus_di = 100 * smoothed_plus[-1] / smoothed_tr[-1]
    minus_di = 100 * smoothed_minus[-1] / smoothed_tr[-1]
    return {"plus_di": plus_di, "minus_di": minus_di, "adx": adx}


def _interpret_rsi(v):
    if v is None:
        return None
    if v >= 70:
        return "overbought"
    if v <= 30:
        return "oversold"
    return "neutral"


def _interpret_cci(v):
    if v is None:
        return None
    if v >= 100:
        return "overbought"
    if v <= -100:
        return "oversold"
    return "neutral"


def _interpret_mfi(v):
    if v is None:
        return None
    if v >= 80:
        return "overbought"
    if v <= 20:
        return "oversold"
    return "neutral"


def _interpret_adx(v):
    # Standard convention: ADX measures trend *strength*, not direction
    # (pair with +DI/-DI for direction) - below 20 means no real trend.
    if v is None:
        return None
    if v >= 25:
        return "strong-trend"
    if v < 20:
        return "weak-trend"
    return "neutral"


def compute_all_indicators(ticker: str):
    data = fetch_ohlcv(ticker)
    if data is None:
        return None

    closes, highs, lows, volumes = data["closes"], data["highs"], data["lows"], data["volumes"]

    rsi_series = compute_rsi(closes)
    rsi = rsi_series[-1] if rsi_series else None
    stoch_rsi = compute_stoch_rsi(closes)
    cci = compute_cci(highs, lows, closes)
    mfi = compute_mfi(highs, lows, closes, volumes)
    macd = compute_macd(closes)
    vwap = compute_vwap(highs, lows, closes, volumes)
    di = compute_di_adx(highs, lows, closes)

    return {
        "ticker": ticker,
        "rsi": round(rsi, 2) if rsi is not None else None,
        "rsi_signal": _interpret_rsi(rsi),
        "stoch_rsi": round(stoch_rsi, 2) if stoch_rsi is not None else None,
        "cci": round(cci, 2) if cci is not None else None,
        "cci_signal": _interpret_cci(cci),
        "mfi": round(mfi, 2) if mfi is not None else None,
        "mfi_signal": _interpret_mfi(mfi),
        "macd": round(macd["macd"], 2) if macd else None,
        "macd_signal_line": round(macd["signal"], 2) if macd else None,
        "macd_histogram": round(macd["histogram"], 2) if macd else None,
        "macd_signal": ("bullish" if macd and macd["histogram"] > 0 else "bearish") if macd else None,
        "vwap": round(vwap, 2) if vwap is not None else None,
        "plus_di": round(di["plus_di"], 2) if di else None,
        "minus_di": round(di["minus_di"], 2) if di else None,
        "di_signal": (("bullish" if di["plus_di"] > di["minus_di"] else "bearish") if di else None),
        "adx": round(di["adx"], 2) if di and di.get("adx") is not None else None,
        "adx_signal": _interpret_adx(di["adx"]) if di and di.get("adx") is not None else None,
    }
