import pytest

from apps.grounded_evidence import build_grounded_evidence


def successful_tool_result(
    tool_name: str,
    observation: dict,
) -> dict:
    return {
        "tool_name": tool_name,
        "success": True,
        "observation": observation,
    }


def test_current_price_evidence_includes_freshness_and_source() -> None:
    trace = [
        successful_tool_result(
            "get_current_price",
            {
                "ticker": "ORCL",
                "price": 172.345,
                "as_of": "2026-08-06",
                "price_type": "latest_daily_close",
                "source": "yfinance",
            },
        )
    ]

    assert build_grounded_evidence(trace) == [
        {
            "Metric": "ORCL latest close",
            "Value": "$172.34",
            "Evidence": (
                "yfinance · as of 2026-08-06 · latest daily close"
            ),
        }
    ]


def test_volatility_evidence_includes_lookback_and_date() -> None:
    trace = [
        successful_tool_result(
            "get_historical_volatility",
            {
                "ticker": "ORCL",
                "lookback_days": 30,
                "annualized_volatility": 0.2749,
                "as_of": "2026-08-06",
                "source": "yfinance",
            },
        )
    ]

    assert build_grounded_evidence(trace) == [
        {
            "Metric": "ORCL historical volatility",
            "Value": "27.49%",
            "Evidence": (
                "30-day lookback · as of 2026-08-06 · yfinance"
            ),
        }
    ]


def test_options_chain_evidence_includes_expiration() -> None:
    trace = [
        successful_tool_result(
            "get_options_chain",
            {
                "contract_count": 8,
                "option_type": "put",
                "expiration": "2026-09-18",
                "source": "yfinance",
            },
        )
    ]

    assert build_grounded_evidence(trace) == [
        {
            "Metric": "Options chain",
            "Value": "8 put contracts",
            "Evidence": "Expiration 2026-09-18 · yfinance",
        }
    ]


def test_csp_evidence_surfaces_risk_provenance_and_warning() -> None:
    warning = (
        "The bid-ask spread exceeds 20% of the midpoint, "
        "so the midpoint may not be executable."
    )
    trace = [
        successful_tool_result(
            "analyze_cash_secured_put",
            {
                "spot_price": 185.25,
                "spot_price_as_of": "2026-08-06",
                "spot_price_type": "latest_daily_close",
                "strike": 180.0,
                "premium": 3.30,
                "premium_source": "bid_ask_midpoint",
                "premium_quote_status": "wide",
                "premium_warning": warning,
                "break_even_price": 176.70,
                "cash_required_dollars": 18_000.0,
                "max_profit_dollars": 330.0,
                "max_loss_dollars": 17_670.0,
                "simple_return": 0.018333,
                "annualized_return": 0.223056,
                "collateral_basis": (
                    "strike_times_contract_size_before_premium"
                ),
                "return_basis": "premium_over_gross_strike_collateral",
                "annualization_method": "simple_non_compounded_365_day",
                "limitations": [
                    "Fees are excluded.",
                    "Assignment risk applies.",
                    "Dividend risk applies.",
                    "Market prices can change.",
                ],
                "source": "yfinance",
            },
        )
    ]

    rows = build_grounded_evidence(trace)
    rows_by_metric = {row["Metric"]: row for row in rows}

    assert rows_by_metric["Premium per share"] == {
        "Metric": "Premium per share",
        "Value": "$3.30",
        "Evidence": "Source: bid ask midpoint · Quote: wide",
    }
    assert rows_by_metric["Maximum profit"]["Value"] == "$330.00"
    assert rows_by_metric["Maximum loss"]["Value"] == "$17,670.00"
    assert rows_by_metric["Simple return"]["Value"] == "1.83%"
    assert rows_by_metric["Annualized return"]["Value"] == "22.31%"
    assert rows_by_metric["Quote warning"]["Value"] == warning
    assert rows_by_metric["Model limitations"]["Value"] == "4 disclosed"


@pytest.mark.parametrize(
    "invalid_value",
    [None, True, float("nan"), float("inf"), "172.34"],
)
def test_missing_or_invalid_price_never_becomes_zero(
    invalid_value: object,
) -> None:
    trace = [
        successful_tool_result(
            "get_current_price",
            {
                "ticker": "ORCL",
                "price": invalid_value,
                "as_of": "2026-08-06",
                "price_type": "latest_daily_close",
                "source": "yfinance",
            },
        )
    ]

    rows = build_grounded_evidence(trace)

    assert rows[0]["Value"] == "Unavailable"
    assert rows[0]["Value"] != "$0.00"


def test_failed_tool_result_does_not_create_evidence() -> None:
    trace = [
        {
            "tool_name": "get_current_price",
            "success": False,
            "observation": {
                "ticker": "ORCL",
                "price": 0,
            },
        }
    ]

    assert build_grounded_evidence(trace) == []


def test_non_tool_and_unknown_tool_events_are_ignored() -> None:
    trace = [
        {"step": 1, "thought": "Inspecting data."},
        successful_tool_result(
            "unknown_tool",
            {"value": 42},
        ),
    ]

    assert build_grounded_evidence(trace) == []
