from dataclasses import FrozenInstanceError

import pytest

from apps.technical_snapshot import (
    TechnicalSnapshot,
    build_technical_snapshot,
)


def technical_observation(
    **overrides: object,
) -> dict:
    observation = {
        "ticker": "AAPL",
        "as_of": "2026-08-07",
        "close": 229.35,
        "observation_count": 251,
        "moving_averages": {
            "sma_20": 221.10,
            "sma_50": 214.25,
            "ema_20": 223.40,
        },
        "rsi_14": 58.75,
        "macd": {
            "line": 3.20,
            "signal": 2.65,
            "histogram": 0.55,
        },
        "bollinger_bands": {
            "middle": 221.10,
            "upper": 235.80,
            "lower": 206.40,
        },
        "lookback_period": "1y",
        "interval": "1d",
        "source": "yfinance",
    }
    observation.update(overrides)
    return observation


def successful_technical_result(
    **overrides: object,
) -> dict:
    return {
        "tool_name": "analyze_technical_indicators",
        "success": True,
        "observation": technical_observation(
            **overrides
        ),
    }


def test_build_technical_snapshot_maps_valid_observation() -> None:
    snapshot = build_technical_snapshot(
        [successful_technical_result()]
    )

    assert snapshot == TechnicalSnapshot(
        ticker="AAPL",
        as_of="2026-08-07",
        close=229.35,
        observation_count=251,
        sma_20=221.10,
        sma_50=214.25,
        ema_20=223.40,
        rsi_14=58.75,
        macd_line=3.20,
        macd_signal=2.65,
        macd_histogram=0.55,
        bollinger_middle=221.10,
        bollinger_upper=235.80,
        bollinger_lower=206.40,
        lookback_period="1y",
        interval="1d",
        source="yfinance",
    )


def test_build_technical_snapshot_uses_latest_successful_result() -> None:
    trace = [
        successful_technical_result(close=210.0),
        successful_technical_result(close=229.35),
        {
            "tool_name": "analyze_technical_indicators",
            "success": False,
            "observation": technical_observation(
                close=250.0
            ),
        },
    ]

    snapshot = build_technical_snapshot(trace)

    assert snapshot is not None
    assert snapshot.close == 229.35


def test_build_technical_snapshot_returns_none_without_successful_result(
) -> None:
    trace = [
        {"step": 1, "thought": "Inspecting data."},
        {
            "tool_name": "analyze_technical_indicators",
            "success": False,
            "observation": technical_observation(),
        },
        {
            "tool_name": "get_current_price",
            "success": True,
            "observation": {"ticker": "AAPL"},
        },
    ]

    assert build_technical_snapshot(trace) is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"as_of": "not-a-date"},
        {"close": float("nan")},
        {
            "moving_averages": {
                "sma_20": float("inf"),
                "sma_50": 214.25,
                "ema_20": 223.40,
            }
        },
        {"close": 0.0},
        {"rsi_14": 101.0},
        {
            "bollinger_bands": {
                "middle": 221.10,
                "upper": 206.40,
                "lower": 235.80,
            }
        },
        {"observation_count": 0},
        {"moving_averages": None},
    ],
)
def test_build_technical_snapshot_rejects_invalid_observation(
    overrides: dict,
) -> None:
    trace = [successful_technical_result(**overrides)]

    assert build_technical_snapshot(trace) is None


def test_build_technical_snapshot_does_not_fall_back_from_malformed_latest(
) -> None:
    trace = [
        successful_technical_result(close=210.0),
        successful_technical_result(close=float("nan")),
    ]

    assert build_technical_snapshot(trace) is None


def test_technical_snapshot_is_immutable() -> None:
    snapshot = build_technical_snapshot(
        [successful_technical_result()]
    )

    assert snapshot is not None
    with pytest.raises(FrozenInstanceError):
        setattr(snapshot, "close", 250.0)
