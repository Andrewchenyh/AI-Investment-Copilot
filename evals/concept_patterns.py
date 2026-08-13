from __future__ import annotations

import re
from typing import Final


ANSWER_CONCEPT_PATTERN_TEXT: Final[
    dict[str, tuple[str, ...]]
] = {
    "spot_price": (
        r"\bcurrent\s+price\b",
        r"\b(?:current\s+)?"
        r"(?:spot|share|stock|underlying|market)\s+price\b",
        r"\b(?:closed|trades?|trading)\s+at\b",
    ),
    "strike": (
        r"\bstrike(?:\s+price)?\b",
        r"\bexercise\s+price\b",
    ),
    "expiration": (
        r"\bexpiration\b",
        r"\bexpiry\b",
        r"\bexpires?\b",
        r"\bexpiring\b",
        r"\b\d{4}-\d{2}-\d{2}\s+"
        r"\$?[\d,]+(?:\.\d+)?[-\s]+"
        r"strike\s+put\b",
        r"\bexp\.?\s+\d{4}-\d{2}-\d{2}\b",
    ),
    "selected_dte": (
        r"\b\d+\s*[-–—]?\s*days?\s+to\s+expiration\b",
        r"\b\d+\s*DTE\b",
        r"\bover\s+\d+\s+days?\b",
    ),
    "premium": (
        r"\bpremiums?\b",
        r"\bcredit(?:\s+received)?\b",
    ),
    "break_even": (
        r"\bbreak[\s‐‑‒–—-]?even"
        r"(?:\s+price)?\b",
    ),
    "cash_required": (
        r"\b(?:cash|capital)\s+"
        r"(?:required|requirement|collateral)\b",
        r"\brequires?\s+\$?[\d,]+(?:\.\d+)?\s+"
        r"in\s+(?:cash|collateral)\b",
        r"\brequired\s+to\s+collateralize\b",
        r"\bcollateral\s+(?:required|requirement)\b",
    ),
    "rsi_14": (
        r"\bRSI\s*(?:[-–]\s*)?"
        r"(?:\(\s*)?14(?:\s*\))?",
        r"\b14[-\s](?:day|period)\s+RSI\b",
    ),
    "sma_50": (
        r"\bSMA\s*(?:[-–]\s*)?"
        r"(?:\(\s*)?50(?:\s*\))?",
        r"\b50[-\s](?:day|period)\s+"
        r"(?:simple\s+)?moving\s+average\b",
        r"\b50[-\s](?:day|period)\s+SMA\b",
    ),
    "volatility_measure": (
        r"\b(?:historical|realized|annualized)\s+"
        r"volatility\b",
    ),
    "lookback_period": (
        r"\blookback\b",
        r"\b30[-\s](?:trading[-\s])?days?\b",
    ),
    "comparison": (
        r"\bcompar(?:e|ed|ing|ison)\b",
        r"\bversus\b",
        r"\bvs\.?\b",
        r"\bbetter\b",
        r"\bprefer(?:red)?\b",
    ),
    "data_unavailable": (
        r"\b(?:no|without)\s+"
        r"(?:\w+\s+){0,3}data\s+"
        r"(?:is\s+|was\s+)?"
        r"(?:available|found)\b",
        r"\bunable\s+to\s+(?:retrieve|fetch|find)\b",
        r"\b(?:could\s+not|couldn't)\s+"
        r"(?:retrieve|fetch|find)\s+"
        r"(?:\w+\s+){0,3}"
        r"(?:price|market)?\s*data\b",
        r"\bno\s+(?:(?:price|market)\s+)?data\s+"
        r"could\s+be\s+(?:retrieved|fetched|found)\b",
        r"\bno\s+(?:(?:price|market)\s+)?data"
        r",\s+(?:including|such\s+as)\s+"
        r"[^,.!?\n]{1,120},\s+"
        r"(?:is|was)\s+(?:available|found)\b",
    ),
}


ANSWER_CONCEPT_PATTERNS: Final[
    dict[str, tuple[re.Pattern[str], ...]]
] = {
    concept_name: tuple(
        re.compile(pattern, flags=re.IGNORECASE)
        for pattern in patterns
    )
    for concept_name, patterns
    in ANSWER_CONCEPT_PATTERN_TEXT.items()
}