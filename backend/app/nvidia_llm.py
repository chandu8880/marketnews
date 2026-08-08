"""Bullish/bearish verdict synthesis for the Top Analysis screen, via
NVIDIA's free-tier NIM API (an OpenAI-compatible chat completions
endpoint serving open models like Llama at no cost). Given the structured
technical indicators, shareholding trend, and recent news headlines for a
stock, asks the model to weigh them into a single call with reasoning -
this is explicitly a synthesis/reasoning step over data we already
computed ourselves (indicators.py, shareholding.py), not a source of the
underlying numbers.

Optional: if NVIDIA_API_KEY isn't set, get_verdict() returns None and the
caller shows the raw data without an AI verdict, rather than failing the
whole analysis.
"""
import json
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("nvidia_llm")

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "").strip()
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a stock market analyst assistant for Indian (NSE) equities. "
    "You will be given a stock's technical indicators, its FII/DII/Promoter "
    "shareholding trend over recent quarters, and recent news headlines. "
    "Weigh all of it together and give a single bullish/bearish/neutral call. "
    "Be concise and specific - reference the actual numbers you were given. "
    "This is analysis of public data, not investment advice, and you should "
    "not claim certainty. Respond with ONLY a JSON object, no other text: "
    '{"verdict": "bullish"|"bearish"|"neutral", "confidence": <int 0-100>, '
    '"reasoning": "<2-3 sentences citing specific figures given>"}'
)


def is_configured() -> bool:
    return bool(NVIDIA_API_KEY)


def _build_user_prompt(ticker: str, name: str, indicators: dict, shareholding: dict, news: list):
    lines = [f"Stock: {name} ({ticker})", "", "Technical indicators:"]
    if indicators:
        lines.append(f"- RSI(14): {indicators.get('rsi')} ({indicators.get('rsi_signal')})")
        lines.append(f"- Stochastic RSI: {indicators.get('stoch_rsi')}")
        lines.append(f"- CCI(20): {indicators.get('cci')} ({indicators.get('cci_signal')})")
        lines.append(f"- MFI(14): {indicators.get('mfi')} ({indicators.get('mfi_signal')})")
        lines.append(
            f"- MACD: {indicators.get('macd')}, signal line {indicators.get('macd_signal_line')}, "
            f"histogram {indicators.get('macd_histogram')} ({indicators.get('macd_signal')})"
        )
        lines.append(f"- VWAP: {indicators.get('vwap')}")
        lines.append(
            f"- +DI/-DI(14): {indicators.get('plus_di')}/{indicators.get('minus_di')} "
            f"({indicators.get('di_signal')})"
        )
    else:
        lines.append("- Not available")

    lines.append("")
    lines.append("Shareholding trend (Promoter/FII/DII % by quarter):")
    if shareholding and shareholding.get("quarters"):
        for q in shareholding["quarters"]:
            lines.append(
                f"- {q['quarter']}: Promoter {q.get('promoter')}%, FII {q.get('fii')}%, "
                f"DII {q.get('dii')}%, Public {q.get('public')}%"
            )
    else:
        lines.append("- Not available")

    lines.append("")
    lines.append("Recent news headlines:")
    if news:
        for n in news[:3]:
            lines.append(f"- [{n.get('sentiment_label')}] {n.get('title')}")
    else:
        lines.append("- None found")

    return "\n".join(lines)


def get_verdict(ticker: str, name: str, indicators: dict, shareholding: dict, news: list):
    if not is_configured():
        return None

    prompt = _build_user_prompt(ticker, name, indicators, shareholding, news)
    try:
        resp = httpx.post(
            NVIDIA_URL,
            headers={"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": NVIDIA_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 300,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        verdict = parsed.get("verdict")
        if verdict not in ("bullish", "bearish", "neutral"):
            return None
        return {
            "verdict": verdict,
            "confidence": max(0, min(100, int(parsed.get("confidence", 0)))),
            "reasoning": parsed.get("reasoning", ""),
            "model": NVIDIA_MODEL,
        }
    except Exception:
        logger.exception("NVIDIA verdict generation failed for %s", ticker)
        return None
