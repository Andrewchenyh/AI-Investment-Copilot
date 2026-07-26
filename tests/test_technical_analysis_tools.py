import pandas as pd
import pytest

from tools.technical_analysis_tools import (
    TechnicalAnalysisInput,
    analyze_technical_indicators_tool,
)


def test_analyze_technical_indicators_returns_compact_snapshot(mocker) -> None:
    price_history = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=60, freq="B"),
            "Close": [100.0] * 60,
        }
    )
    engine = mocker.patch(
        "tools.technical_analysis_tools.MarketDataEngine"
    ).return_value
    engine.get_price_history.return_value = price_history

    result = analyze_technical_indicators_tool(
        TechnicalAnalysisInput(ticker=" aapl ")
    )

    assert result.ticker == "AAPL"
    assert result.as_of == price_history["Date"].iloc[-1].date().isoformat()
    assert result.close == pytest.approx(100)
    assert result.observation_count == 60

    assert result.moving_averages.sma_20 == pytest.approx(100)
    assert result.moving_averages.sma_50 == pytest.approx(100)
    assert result.moving_averages.ema_20 == pytest.approx(100)

    assert result.rsi_14 == pytest.approx(50)

    assert result.macd.line == pytest.approx(0)
    assert result.macd.signal == pytest.approx(0)
    assert result.macd.histogram == pytest.approx(0)

    assert result.bollinger_bands.middle == pytest.approx(100)
    assert result.bollinger_bands.upper == pytest.approx(100)
    assert result.bollinger_bands.lower == pytest.approx(100)

    engine.get_price_history.assert_called_once_with(
        ticker="AAPL",
        period="1y",
        interval="1d",
    )


def test_analyze_technical_indicators_raises_when_no_price_data(mocker) -> None:
    engine = mocker.patch(
        "tools.technical_analysis_tools.MarketDataEngine"
    ).return_value
    engine.get_price_history.return_value = pd.DataFrame()

    with pytest.raises(
        ValueError,
        match=r"^No price data found for ticker 'AAPL'\.$",
    ):
        analyze_technical_indicators_tool(TechnicalAnalysisInput(ticker="AAPL"))

    engine.get_price_history.assert_called_once_with(
        ticker="AAPL",
        period="1y",
        interval="1d",
    )


def test_analyze_technical_indicators_raises_for_insufficient_history(mocker,) -> None:
    price_history = pd.DataFrame(
        {
            "Date": pd.date_range("2026-01-01", periods=49, freq="B"),
            "Close": [100.0] * 49,
        }
    )
    engine = mocker.patch(
        "tools.technical_analysis_tools.MarketDataEngine"
    ).return_value
    engine.get_price_history.return_value = price_history

    with pytest.raises(
        ValueError,
        match=r"^At least 50 daily observations are required",
    ):
        analyze_technical_indicators_tool(TechnicalAnalysisInput(ticker="AAPL"))

    engine.get_price_history.assert_called_once_with(
        ticker="AAPL",
        period="1y",
        interval="1d",
    )
