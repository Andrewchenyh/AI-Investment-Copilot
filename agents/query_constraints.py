import re
from typing import Any


_STRIKE_NUMBER = (
    r"(?P<strike>"
    r"(?:\d{1,3}(?:,\d{3})+|\d+)"
    r"(?:\.\d+)?"
    r")"
)

_EXPLICIT_STRIKE_PATTERNS: tuple[
    re.Pattern[str],
    ...,
] = (
    re.compile(
        rf"(?<!\w)\$?\s*{_STRIKE_NUMBER}"
        rf"\s*(?:-|\s)*"
        rf"(?:strike(?:\s+price)?|"
        rf"cash[\s-]+secured\s+put)\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<!\w)\$\s*{_STRIKE_NUMBER}"
        rf"\s*(?:-|\s)*put\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bstrike(?:\s+price)?"
        rf"(?:\s+(?:of|at|is))?"
        rf"\s*\$?\s*{_STRIKE_NUMBER}\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bput\s+at\s+(?:a\s+)?"
        rf"(?:strike(?:\s+of)?\s+)?"
        rf"\$?\s*{_STRIKE_NUMBER}\b",
        re.IGNORECASE,
    ),
)


_CSP_QUERY_PATTERN = re.compile(
    r"\b(?:cash[\s-]+secured\s+puts?|CSPs?)\b",
    re.IGNORECASE,
)


def extract_explicit_csp_strike(
    query: str,
) -> float | None:
    for pattern in _EXPLICIT_STRIKE_PATTERNS:
        match = pattern.search(query)
        if match is None:
            continue

        strike = float(
            match.group("strike").replace(",", "")
        )
        if strike > 0:
            return strike

    return None


def enforce_explicit_csp_strike(
    tool_name: str,
    tool_args: dict[str, Any],
    explicit_strike: float | None,
) -> dict[str, Any]:
    constrained_args = dict(tool_args)

    if explicit_strike is None:
        return constrained_args

    if tool_name == "get_options_chain":
        constrained_args["target_strike"] = (
            explicit_strike
        )

    elif tool_name == "analyze_cash_secured_put":
        constrained_args["strike"] = explicit_strike
        constrained_args.pop("premium", None)

    return constrained_args


def find_csp_tickers_without_analysis_attempt(
    query: str,
    trace: list[dict[str, Any]],
) -> list[str]:
    if _CSP_QUERY_PATTERN.search(query) is None:
        return []

    chain_tickers: set[str] = set()
    analyzed_tickers: set[str] = set()

    for item in trace:
        tool_args = item.get("tool_args")
        if not isinstance(tool_args, dict):
            continue

        ticker = tool_args.get("ticker")
        if not isinstance(ticker, str):
            continue

        normalized_ticker = ticker.strip().upper()
        if not normalized_ticker:
            continue

        if (
            item.get("tool_name") == "get_options_chain"
            and item.get("success") is True
        ):
            chain_tickers.add(normalized_ticker)

        elif (
            item.get("tool_name")
            == "analyze_cash_secured_put"
        ):
            analyzed_tickers.add(normalized_ticker)

    return sorted(
        chain_tickers - analyzed_tickers
    )
