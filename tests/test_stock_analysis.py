import pandas as pd
import pytest

from analysis.stock_analysis import TechnicalIndicators, add_all_indicators


DEFAULT_INDICATOR_COLUMNS = {
    "SMA_20",
    "EMA_20",
    "RSI_14",
    "MACD",
    "Signal",
    "Histogram",
    "BB_20_Middle",
    "BB_20_Upper",
    "BB_20_Lower",
}


def make_price_df(prices: list[float]) -> pd.DataFrame:
    return pd.DataFrame({"Close": prices})


def test_sma() -> None:
    df = make_price_df([1, 2, 3, 4, 5])

    result = TechnicalIndicators.sma(df, window=3)

    assert result.iloc[0:2].isna().all()
    assert result.iloc[2] == 2
    assert result.iloc[3] == 3
    assert result.iloc[4] == 4


def test_ema_constant_series() -> None:
    df = make_price_df([10, 10, 10, 10, 10])

    result = TechnicalIndicators.ema(df, window=3)

    assert result.tolist() == [10, 10, 10, 10, 10]


def test_bollinger_bands_constant_series() -> None:
    df = make_price_df([10] * 25)

    result = TechnicalIndicators.bollinger_bands(df, window=20)

    last_row = result.iloc[-1]
    assert last_row["BB_20_Middle"] == 10
    assert last_row["BB_20_Upper"] == 10
    assert last_row["BB_20_Lower"] == 10


def test_macd_constant_series() -> None:
    df = make_price_df([10] * 40)

    result = TechnicalIndicators.macd(df)

    assert result["MACD"].iloc[-1] == pytest.approx(0)
    assert result["Signal"].iloc[-1] == pytest.approx(0)
    assert result["Histogram"].iloc[-1] == pytest.approx(0)


def test_rsi_flat_series_returns_50_after_warmup() -> None:
    df = make_price_df([10] * 20)

    result = TechnicalIndicators.rsi(df, window=14)

    assert result.iloc[:14].isna().all()
    assert result.iloc[14:].eq(50).all()


def test_rsi_all_gains_returns_100_after_warmup() -> None:
    df = make_price_df(list(range(1, 21)))

    result = TechnicalIndicators.rsi(df, window=14)

    assert result.iloc[:14].isna().all()
    assert result.iloc[14:].eq(100).all()


def test_rsi_all_losses_returns_0_after_warmup() -> None:
    df = make_price_df(list(range(20, 0, -1)))

    result = TechnicalIndicators.rsi(df, window=14)

    assert result.iloc[:14].isna().all()
    assert result.iloc[14:].eq(0).all()


def test_add_all_indicators_uses_defaults_when_config_is_omitted() -> None:
    df = make_price_df(list(range(1, 41)))

    result = add_all_indicators(df)

    assert DEFAULT_INDICATOR_COLUMNS <= set(result.columns)
    assert list(df.columns) == ["Close"]


def test_add_all_indicators_uses_defaults_for_none_windows() -> None:
    df = make_price_df(list(range(1, 41)))
    config = {
        "sma_windows": None,
        "ema_windows": None,
        "rsi_windows": None,
        "bb_windows": None,
    }

    result = add_all_indicators(df, config) # type: ignore

    assert DEFAULT_INDICATOR_COLUMNS <= set(result.columns)


def test_add_all_indicators_empty_lists_disable_optional_families() -> None:
    df = make_price_df(list(range(1, 41)))
    config = {
        "sma_windows": [],
        "ema_windows": [],
        "rsi_windows": [],
        "bb_windows": [],
    }

    result = add_all_indicators(df, config) # type: ignore

    assert list(result.columns) == ["Close", "MACD", "Signal", "Histogram"]
