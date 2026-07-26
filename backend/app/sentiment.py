"""Bullish / bearish sentiment scoring for finance news headlines.

Uses VADER (general-purpose lexicon sentiment analyzer) with an extra
finance-specific lexicon layered on top, since words like "surge", "beat
estimates", or "downgrade" carry strong market meaning that VADER's default
lexicon doesn't weight correctly.
"""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

# Extra finance-specific words/phrases with hand-tuned VADER-style scores (-4..4).
_FINANCE_LEXICON = {
    "surge": 3.0, "surges": 3.0, "surged": 3.0, "soar": 3.2, "soars": 3.2, "soared": 3.2,
    "rally": 2.8, "rallies": 2.8, "rallied": 2.8, "jump": 2.2, "jumps": 2.2, "jumped": 2.2,
    "beat estimates": 3.0, "beats estimates": 3.0, "beat expectations": 3.0,
    "tops estimates": 2.8, "record high": 3.0, "all-time high": 3.0, "upgrade": 2.5,
    "upgraded": 2.5, "outperform": 2.2, "bullish": 3.0, "buy rating": 2.0,
    "raises guidance": 2.6, "raised guidance": 2.6, "strong earnings": 2.5,
    "beats revenue": 2.4, "gains": 1.8, "gain": 1.8, "climbs": 1.8, "climbed": 1.8,
    "plunge": -3.2, "plunges": -3.2, "plunged": -3.2, "crash": -3.5, "crashes": -3.5,
    "crashed": -3.5, "tumble": -2.8, "tumbles": -2.8, "tumbled": -2.8, "slump": -2.6,
    "slumps": -2.6, "slumped": -2.6, "sink": -2.2, "sinks": -2.2, "sank": -2.2,
    "sell-off": -2.8, "selloff": -2.8, "miss estimates": -3.0, "misses estimates": -3.0,
    "misses expectations": -3.0, "downgrade": -2.5, "downgraded": -2.5,
    "underperform": -2.2, "bearish": -3.0, "sell rating": -2.0, "cuts guidance": -2.6,
    "cut guidance": -2.6, "lowers guidance": -2.6, "weak earnings": -2.5,
    "layoffs": -2.2, "lawsuit": -1.8, "investigation": -1.8, "recall": -1.8,
    "bankruptcy": -3.5, "losses": -2.0, "loss": -1.8, "decline": -1.6, "declines": -1.6,
    "declined": -1.6, "falls": -1.6, "fell": -1.6, "drops": -1.8, "dropped": -1.8,
}
_analyzer.lexicon.update(_FINANCE_LEXICON)

BULLISH_THRESHOLD = 0.2
BEARISH_THRESHOLD = -0.2


def score_text(text: str) -> float:
    """Return a VADER compound sentiment score in [-1, 1] for the given text."""
    if not text:
        return 0.0
    return _analyzer.polarity_scores(text)["compound"]


def classify(score: float) -> str:
    if score >= BULLISH_THRESHOLD:
        return "bullish"
    if score <= BEARISH_THRESHOLD:
        return "bearish"
    return "neutral"
