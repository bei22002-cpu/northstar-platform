"""Frustration detection via regex — inspired by Claude Code's userPromptKeywords.ts.

Detects user frustration from message text and returns a sentiment signal
that the system prompt can use to adjust tone.  Uses fast regex matching
(no LLM call) so it adds zero latency.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import NamedTuple


class Sentiment(Enum):
    """Coarse sentiment bucket."""

    NEUTRAL = "neutral"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    URGENT = "urgent"


class SentimentResult(NamedTuple):
    sentiment: Sentiment
    matched_keyword: str | None
    tone_instruction: str


# ---------------------------------------------------------------------------
# Regex patterns — ordered by specificity
# ---------------------------------------------------------------------------

_FRUSTRATED_RE = re.compile(
    r"\b("
    r"wtf|wth|ffs|omfg|shit(?:ty|tiest)?|dumbass|horrible|awful|"
    r"piss(?:ed|ing)?\s*off|piece\s+of\s+(?:shit|crap|junk)|"
    r"what\s+the\s+(?:fuck|hell)|"
    r"fuck(?:ing?)?\s*(?:broken|useless|terrible|awful|horrible)?|"
    r"fuck\s*you|screw\s+(?:this|you)|so\s+frustrating|"
    r"this\s+sucks|damn\s*it|"
    r"hate\s+(?:this|it|you)|useless|garbage|trash|"
    r"worst|terrible|pathetic|ridiculous|unbelievable|"
    r"stop\s+(?:doing\s+that|breaking|messing)|"
    r"you\s+(?:broke|ruined|messed\s+up)|"
    r"nothing\s+works|still\s+(?:broken|not\s+working)|"
    r"waste\s+of\s+time"
    r")\b",
    re.IGNORECASE,
)

_CONFUSED_RE = re.compile(
    r"\b("
    r"i\s+don'?t\s+understand|what\s+(?:does\s+that\s+mean|is\s+(?:this|that))|"
    r"confused|makes?\s+no\s+sense|huh\??|what\??|"
    r"i'?m\s+lost|help\s+me\s+understand|"
    r"can\s+you\s+explain|why\s+(?:is|did|does)|"
    r"that\s+doesn'?t\s+(?:make\s+sense|work|help)"
    r")\b",
    re.IGNORECASE,
)

_URGENT_RE = re.compile(
    r"\b("
    r"asap|urgent(?:ly)?|immediately|right\s+now|hurry|"
    r"emergency|critical|deadline|time\s+sensitive|"
    r"need\s+this\s+(?:now|done|fast|quick)|"
    r"production\s+(?:is\s+)?down|outage|breaking|"
    r"customers?\s+(?:are\s+)?(?:affected|impacted|complaining)"
    r")\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Tone injection strings — appended to the system prompt when triggered
# ---------------------------------------------------------------------------

_TONE_MAP: dict[Sentiment, str] = {
    Sentiment.FRUSTRATED: (
        "\n\n[TONE ADJUSTMENT — the user seems frustrated. "
        "Be extra empathetic and concise. Acknowledge the frustration briefly, "
        "then focus on solving the problem quickly. Avoid long explanations. "
        "Do NOT be defensive or dismissive. Prioritize actionable fixes.]"
    ),
    Sentiment.CONFUSED: (
        "\n\n[TONE ADJUSTMENT — the user seems confused. "
        "Break your response into small, clear steps. Use simple language. "
        "Add brief explanations for technical terms. Offer to clarify further.]"
    ),
    Sentiment.URGENT: (
        "\n\n[TONE ADJUSTMENT — the user's request is urgent. "
        "Prioritize speed and directness. Skip pleasantries. "
        "Give the most critical fix first, then details. "
        "If multiple approaches exist, recommend the fastest one.]"
    ),
    Sentiment.NEUTRAL: "",
}

# Track consecutive frustrated messages for escalation
_frustration_streak: int = 0
MAX_FRUSTRATION_STREAK = 3


def detect_sentiment(text: str) -> SentimentResult:
    """Classify *text* into a sentiment bucket using regex matching.

    Returns a ``SentimentResult`` with the sentiment, the matched keyword
    (if any), and a tone instruction string to append to the system prompt.
    """
    global _frustration_streak

    # Check frustrated first (strongest signal)
    m = _FRUSTRATED_RE.search(text)
    if m:
        _frustration_streak += 1
        tone = _TONE_MAP[Sentiment.FRUSTRATED]
        if _frustration_streak >= MAX_FRUSTRATION_STREAK:
            tone += (
                "\n[ESCALATION — the user has been frustrated for "
                f"{_frustration_streak} consecutive messages. "
                "Consider asking if they'd like to try a completely different "
                "approach, or if there's something else going on.]"
            )
        return SentimentResult(Sentiment.FRUSTRATED, m.group(0), tone)

    # Reset frustration streak on non-frustrated messages
    _frustration_streak = 0

    m = _URGENT_RE.search(text)
    if m:
        return SentimentResult(Sentiment.URGENT, m.group(0), _TONE_MAP[Sentiment.URGENT])

    m = _CONFUSED_RE.search(text)
    if m:
        return SentimentResult(Sentiment.CONFUSED, m.group(0), _TONE_MAP[Sentiment.CONFUSED])

    return SentimentResult(Sentiment.NEUTRAL, None, _TONE_MAP[Sentiment.NEUTRAL])
