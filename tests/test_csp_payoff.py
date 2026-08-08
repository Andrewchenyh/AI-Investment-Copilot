from dataclasses import FrozenInstanceError

import pytest

from apps.csp_payoff import (
    CSPPayoffSeries,
    build_csp_payoff_series,
)


def csp_observation(**overrides: object) -> dict:
    observation = {
        "ticker": "ORCL",
        "expiration": "2026-09-18",
        "spot_price": 185.25,
        "spot_price_as_of": "2026-08-06",
        "strike": 180.0,
        "premium": 3.30,
        "premium_source": "bid_ask_midpoint",
        "premium_quote_status": "normal",
        "premium_warning": None,
        "contract_size": 100,
    }
    observation.update(overrides)
    return observation


def successful_csp_result(**overrides: object) -> dict:
    return {
        "tool_name": "analyze_cash_secured_put",
        "success": True,
        "observation": csp_observation(**overrides),
    }


def payoff_at(
    series: CSPPayoffSeries,
    underlying_price: float,
) -> float:
    index = series.underlying_prices.index(
        underlying_price
    )
    return series.profit_loss_dollars[index]


def test_build_csp_payoff_series_contains_financial_landmarks() -> None:
    series = build_csp_payoff_series(
        [successful_csp_result()]
    )

    assert series is not None
    assert series.ticker == "ORCL"
    assert series.expiration == "2026-09-18"
    assert series.spot_price == 185.25
    assert series.spot_price_as_of == "2026-08-06"
    assert series.strike == 180.0
    assert series.premium == 3.30
    assert series.premium_source == "bid_ask_midpoint"
    assert series.premium_quote_status == "normal"
    assert series.contract_size == 100
    assert series.break_even_price == pytest.approx(176.70)
    assert series.max_profit_dollars == 330.0
    assert series.max_loss_dollars == 17_670.0

    assert series.underlying_prices == tuple(
        sorted(series.underlying_prices)
    )
    assert series.underlying_prices[0] == 0.0
    assert series.underlying_prices[-1] == pytest.approx(
        185.25 * 1.5
    )
    assert series.break_even_price in series.underlying_prices
    assert series.strike in series.underlying_prices
    assert series.spot_price in series.underlying_prices
    assert len(series.underlying_prices) == len(
        series.profit_loss_dollars
    )

    assert payoff_at(series, 0.0) == -17_670.0
    assert payoff_at(
        series,
        series.break_even_price,
    ) == 0.0
    assert payoff_at(series, series.strike) == 330.0
    assert payoff_at(series, series.spot_price) == 330.0


def test_build_csp_payoff_series_uses_latest_successful_result() -> None:
    trace = [
        successful_csp_result(strike=170.0, premium=2.0),
        successful_csp_result(strike=180.0, premium=3.30),
        {
            "tool_name": "analyze_cash_secured_put",
            "success": False,
            "observation": {},
        },
    ]

    series = build_csp_payoff_series(trace)

    assert series is not None
    assert series.strike == 180.0
    assert series.premium == 3.30


def test_build_csp_payoff_series_returns_none_without_successful_csp() -> None:
    trace = [
        {"step": 1, "thought": "Inspecting data."},
        {
            "tool_name": "analyze_cash_secured_put",
            "success": False,
            "observation": csp_observation(),
        },
    ]

    assert build_csp_payoff_series(trace) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"spot_price": None},
        {"spot_price": True},
        {"spot_price": float("inf")},
        {"strike": 0.0},
        {"premium": float("nan")},
        {"premium": 180.0},
        {"contract_size": True},
        {"contract_size": 0},
    ],
)
def test_build_csp_payoff_series_rejects_invalid_observation(
    overrides: dict,
) -> None:
    trace = [successful_csp_result(**overrides)]

    assert build_csp_payoff_series(trace) is None


@pytest.mark.parametrize(
    "point_count",
    [0, 1, True, 2.5],
)
def test_build_csp_payoff_series_rejects_invalid_point_count(
    point_count: object,
) -> None:
    with pytest.raises(
        ValueError,
        match="point_count must be an integer of at least 2",
    ):
        build_csp_payoff_series(
            [successful_csp_result()],
            point_count=point_count,  # type: ignore[arg-type]
        )


def test_build_csp_payoff_series_normalizes_optional_metadata() -> None:
    series = build_csp_payoff_series(
        [
            successful_csp_result(
                ticker="   ",
                expiration=None,
                spot_price_as_of="",
                premium_source=None,
                premium_quote_status=42,
                premium_warning=["not text"],
            )
        ]
    )

    assert series is not None
    assert series.ticker == "Unavailable"
    assert series.expiration == "Unavailable"
    assert series.spot_price_as_of == "Unavailable"
    assert series.premium_source == "Unavailable"
    assert series.premium_quote_status is None
    assert series.premium_warning is None


def test_csp_payoff_series_is_immutable() -> None:
    series = build_csp_payoff_series(
        [successful_csp_result()]
    )

    assert series is not None
    assert isinstance(series.underlying_prices, tuple)
    assert isinstance(series.profit_loss_dollars, tuple)

    with pytest.raises(FrozenInstanceError):
        setattr(series, "strike", 175.0)
