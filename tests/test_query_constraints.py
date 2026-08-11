import pytest

from agents.query_constraints import (
    enforce_explicit_csp_strike,
    extract_explicit_csp_strike,
    find_csp_tickers_without_analysis_attempt,
)


@pytest.mark.parametrize(
    ("query", "expected_strike"),
    [
        (
            "Is it a good time to write a 1000 cash-secured put on SNDK?",
            1000.0,
        ),
        (
            "Analyze a $1,000 cash secured put on SNDK.",
            1000.0,
        ),
        (
            "Is an ORCL $170 put attractive?",
            170.0,
        ),
        (
            "Review the 170-strike put on ORCL.",
            170.0,
        ),
        (
            "Review a put with a strike of $170.50 on ORCL.",
            170.50,
        ),
        (
            "Could I write the SNDK put at 1,000?",
            1000.0,
        ),
    ],
)
def test_extract_explicit_csp_strike(
    query: str,
    expected_strike: float,
) -> None:
    assert extract_explicit_csp_strike(query) == expected_strike


@pytest.mark.parametrize(
    "query",
    [
        "Is it a good time to write a cash-secured put on ORCL?",
        "Find an ORCL put with 30 to 60 days to expiration.",
        "Review the ORCL put expiring 2026-09-04.",
        "I have $10,000 available to secure an ORCL put.",
        "What can I earn if I write 10 cash-secured puts?",
        "Analyze AAPL using RSI 14 and a 50-day moving average.",
        "",
    ],
)
def test_extract_explicit_csp_strike_avoids_unrelated_numbers(
    query: str,
) -> None:
    assert extract_explicit_csp_strike(query) is None


def test_extract_explicit_csp_strike_ignores_zero_strike() -> None:
    assert extract_explicit_csp_strike(
        "Review a 0 strike put on ORCL."
    ) is None


def test_enforce_explicit_strike_overrides_options_chain_target() -> None:
    original_args = {
        "ticker": "SNDK",
        "target_strike": 1130,
        "limit": 10,
    }

    constrained_args = enforce_explicit_csp_strike(
        tool_name="get_options_chain",
        tool_args=original_args,
        explicit_strike=1000.0,
    )

    assert constrained_args == {
        "ticker": "SNDK",
        "target_strike": 1000.0,
        "limit": 10,
    }
    assert original_args["target_strike"] == 1130


def test_enforce_explicit_strike_removes_potentially_mismatched_premium(
) -> None:
    constrained_args = enforce_explicit_csp_strike(
        tool_name="analyze_cash_secured_put",
        tool_args={
            "ticker": "SNDK",
            "strike": 1130,
            "expiration": "2026-09-04",
            "premium": 80,
        },
        explicit_strike=1000.0,
    )

    assert constrained_args == {
        "ticker": "SNDK",
        "strike": 1000.0,
        "expiration": "2026-09-04",
    }


def test_enforce_explicit_strike_leaves_unrelated_tool_unchanged() -> None:
    original_args = {"ticker": "SNDK"}

    constrained_args = enforce_explicit_csp_strike(
        tool_name="get_current_price",
        tool_args=original_args,
        explicit_strike=1000.0,
    )

    assert constrained_args == original_args
    assert constrained_args is not original_args


def test_enforce_explicit_strike_does_nothing_without_constraint() -> None:
    original_args = {
        "ticker": "SNDK",
        "target_strike": 1130,
    }

    constrained_args = enforce_explicit_csp_strike(
        tool_name="get_options_chain",
        tool_args=original_args,
        explicit_strike=None,
    )

    assert constrained_args == original_args
    assert constrained_args is not original_args


def test_find_csp_tickers_returns_successful_chain_without_analysis() -> None:
    trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "msft"},
            "success": True,
        }
    ]

    pending_tickers = find_csp_tickers_without_analysis_attempt(
        "Should I write a cash-secured put on MSFT?",
        trace,
    )

    assert pending_tickers == ["MSFT"]


def test_find_csp_tickers_handles_comparison_independently() -> None:
    trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "ORCL"},
            "success": True,
        },
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "MSFT"},
            "success": True,
        },
        {
            "tool_name": "analyze_cash_secured_put",
            "tool_args": {"ticker": "orcl"},
            "success": True,
        },
    ]

    pending_tickers = find_csp_tickers_without_analysis_attempt(
        "Compare ORCL and MSFT cash-secured puts.",
        trace,
    )

    assert pending_tickers == ["MSFT"]


def test_find_csp_tickers_counts_failed_analysis_as_an_attempt() -> None:
    trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "ORCL"},
            "success": True,
        },
        {
            "tool_name": "analyze_cash_secured_put",
            "tool_args": {"ticker": "ORCL"},
            "success": False,
        },
    ]

    pending_tickers = find_csp_tickers_without_analysis_attempt(
        "Analyze an ORCL CSP.",
        trace,
    )

    assert pending_tickers == []


def test_find_csp_tickers_ignores_failed_chain_lookup() -> None:
    trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "FAKEFAKE"},
            "success": False,
        }
    ]

    pending_tickers = find_csp_tickers_without_analysis_attempt(
        "Analyze a cash-secured put on FAKEFAKE.",
        trace,
    )

    assert pending_tickers == []


def test_find_csp_tickers_does_not_apply_to_non_csp_query() -> None:
    trace = [
        {
            "tool_name": "get_options_chain",
            "tool_args": {"ticker": "ORCL"},
            "success": True,
        }
    ]

    pending_tickers = find_csp_tickers_without_analysis_attempt(
        "Show me ORCL's options chain.",
        trace,
    )

    assert pending_tickers == []
