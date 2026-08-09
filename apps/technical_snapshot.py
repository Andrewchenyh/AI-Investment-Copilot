import math
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import ValidationError

from tools.technical_analysis_tools import (
    TechnicalAnalysisOutput,
)


@dataclass(frozen=True)
class TechnicalSnapshot:
    ticker: str
    as_of: str
    close: float
    observation_count: int
    sma_20: float
    sma_50: float
    ema_20: float
    rsi_14: float
    macd_line: float
    macd_signal: float
    macd_histogram: float
    bollinger_middle: float
    bollinger_upper: float
    bollinger_lower: float
    lookback_period: str
    interval: str
    source: str


def _latest_successful_technical_observation(
    trace: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for item in reversed(trace):
        if (
            item.get("tool_name")
            != "analyze_technical_indicators"
        ):
            continue

        if item.get("success") is not True:
            continue

        observation = item.get("observation")
        if isinstance(observation, dict):
            return observation

    return None


def build_technical_snapshot(
    trace: list[dict[str, Any]],
) -> TechnicalSnapshot | None:
    observation = (
        _latest_successful_technical_observation(
            trace
        )
    )
    if observation is None:
        return None

    try:
        output = TechnicalAnalysisOutput.model_validate(
            observation
        )
        date.fromisoformat(output.as_of)
    except (ValidationError, ValueError):
        return None

    numeric_values = (
        output.close,
        output.moving_averages.sma_20,
        output.moving_averages.sma_50,
        output.moving_averages.ema_20,
        output.rsi_14,
        output.macd.line,
        output.macd.signal,
        output.macd.histogram,
        output.bollinger_bands.middle,
        output.bollinger_bands.upper,
        output.bollinger_bands.lower,
    )

    if not all(
        math.isfinite(value)
        for value in numeric_values
    ):
        return None

    price_levels = (
        output.close,
        output.moving_averages.sma_20,
        output.moving_averages.sma_50,
        output.moving_averages.ema_20,
        output.bollinger_bands.middle,
        output.bollinger_bands.upper,
        output.bollinger_bands.lower,
    )

    if any(value <= 0 for value in price_levels):
        return None

    if not (
        output.bollinger_bands.lower
        <= output.bollinger_bands.middle
        <= output.bollinger_bands.upper
    ):
        return None

    if output.observation_count <= 0:
        return None

    return TechnicalSnapshot(
        ticker=output.ticker,
        as_of=output.as_of,
        close=output.close,
        observation_count=output.observation_count,
        sma_20=output.moving_averages.sma_20,
        sma_50=output.moving_averages.sma_50,
        ema_20=output.moving_averages.ema_20,
        rsi_14=output.rsi_14,
        macd_line=output.macd.line,
        macd_signal=output.macd.signal,
        macd_histogram=output.macd.histogram,
        bollinger_middle=(
            output.bollinger_bands.middle
        ),
        bollinger_upper=output.bollinger_bands.upper,
        bollinger_lower=output.bollinger_bands.lower,
        lookback_period=output.lookback_period,
        interval=output.interval,
        source=output.source,
    )