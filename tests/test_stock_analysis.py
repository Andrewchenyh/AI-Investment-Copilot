import pandas as pd
import pytest

from analysis.stock_analysis import TechnicalIndicators


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