"""Optional LLM-based bullish/bearish classification via Groq's free API
(Llama 3), layered on top of the VADER scoring in sentiment.py.

Zero-config by default: if GROQ_API_KEY isn't set, classify_with_llm()
returns None immediately (no network call) and callers fall back to VADER,
so the app keeps working exactly as before with no API keys needed. Any
request failure, timeout, or malformed response also falls back to None
rather than raising, so a flaky/rate-limited free API never breaks ingest.
"""
import json
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("llm_sentiment")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

_SYSTEM_PROMPT = (
    "You are a financial news sentiment classifier for Indian stock market "
    "headlines. Given a headline and summary, decide whether it is bullish "
    "(positive for the stock/market), bearish (negative), or neutral. "
    "Respond with ONLY a JSON object, no other text: "
    '{"label": "bullish"|"bearish"|"neutral", "score": <float from -1.0 (most bearish) to 1.0 (most bullish)>}'
)


def classify_with_llm(text: str) -> tuple[str, float] | None:
    """Return (label, score) from Groq, or None if unconfigured/unavailable."""
    if not GROQ_API_KEY or not text:
        return None
    try:
        resp = httpx.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            json={
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": text[:1000]},
                ],
                "temperature": 0,
                "max_tokens": 50,
                "response_format": {"type": "json_object"},
            },
            timeout=8.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        label = str(parsed["label"]).lower().strip()
        if label not in ("bullish", "bearish", "neutral"):
            return None
        score = max(-1.0, min(1.0, float(parsed["score"])))
        return label, score
    except Exception:
        logger.warning("Groq sentiment classification failed, falling back to VADER", exc_info=True)
        return None
