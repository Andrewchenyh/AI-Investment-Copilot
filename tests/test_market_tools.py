import pandas as pd
import pytest

from tools.basic_market_tools import (
    CurrentPriceInput,
    HistoricalVolatilityInput,
    get_current_price_tool,
    get_historical_volatility_tool,
)
from tools.market_data import extract_latest_daily_close


def test_get_current_price_tool_returns_latest_close(mocker) -> None:
    mock_engine = mocker.patch("tools.basic_market_tools.MarketDataEngine")
    mock_engine.return_value.get_price_history.return_value = pd.DataFrame(
        {
            "Date": pd.date_range("2026-07-29", periods=3, freq="B"),
            "Close": [100.0, 105.0, 110.0],
        }
    )

    result = get_current_price_tool(CurrentPriceInput(ticker="orcl"))

    assert result.ticker == "ORCL"
    assert result.price == 110.0
    assert result.as_of == "2026-07-31"
    assert result.price_type == "latest_daily_close"
    assert result.currency == "USD"
    assert result.source == "yfinance"

    mock_engine.return_value.get_price_history.assert_called_once_with(
        ticker="orcl",
        period="5d",
        interval="1d",
    )


def test_get_current_price_tool_raises_when_no_data(mocker) -> None:
    mock_engine = mocker.patch("tools.basic_market_tools.MarketDataEngine")
    mock_engine.return_value.get_price_history.return_value = pd.DataFrame()

    with pytest.raises(ValueError, match="No price data found"):
        get_current_price_tool(CurrentPriceInput(ticker="ORCL"))


def test_get_historical_volatility_tool_returns_computed_volatility(mocker) -> None:
    mock_engine = mocker.patch("tools.basic_market_tools.MarketDataEngine")
    mock_engine.return_value.get_price_history.return_value = pd.DataFrame(
        {
            "Date": pd.date_range("2026-07-27", periods=5, freq="B"),
            "Close": [100.0, 102.0, 101.0, 103.0, 104.0],
        }
    )
    mock_engine.return_value.compute_volatility.return_value = 0.25

    result = get_historical_volatility_tool(
        HistoricalVolatilityInput(ticker="orcl", lookback_days=5)
    )

    assert result.ticker == "ORCL"
    assert result.lookback_days == 5
    assert result.annualized_volatility == 0.25
    assert result.observation_count == 5
    assert result.as_of == "2026-07-31"
    assert result.price_data_type == "daily_close"
    assert result.source == "yfinance"

    mock_engine.return_value.get_price_history.assert_called_once_with(
        ticker="orcl",
        period="30d",
        interval="1d",
    )

    mock_engine.return_value.compute_volatility.assert_called_once_with(mocker.ANY)


def test_get_historical_volatility_tool_raises_when_no_data(mocker) -> None:
    mock_engine = mocker.patch("tools.basic_market_tools.MarketDataEngine")
    mock_engine.return_value.get_price_history.return_value = pd.DataFrame()

    with pytest.raises(ValueError, match="No price data found"):
        get_historical_volatility_tool(
            HistoricalVolatilityInput(ticker="ORCL", lookback_days=30)
        )


def test_latest_daily_close_requires_date_and_close_columns() -> None:
    with pytest.raises(ValueError, match="missing required columns: Date"):
        extract_latest_daily_close(
            pd.DataFrame({"Close": [100.0]}),
            "ORCL",
        )


@pytest.mark.parametrize(
    "invalid_close",
    [None, float("nan"), float("inf"), 0, -1, "invalid"],
)
def test_latest_daily_close_rejects_invalid_price(invalid_close: object) -> None:
    with pytest.raises(ValueError, match="Latest closing price"):
        extract_latest_daily_close(
            pd.DataFrame(
                {
                    "Date": [pd.Timestamp("2026-07-31")],
                    "Close": [invalid_close],
                }
            ),
            "ORCL",
        )


def test_latest_daily_close_rejects_invalid_date() -> None:
    with pytest.raises(ValueError, match="Latest price date"):
        extract_latest_daily_close(
            pd.DataFrame(
                {
                    "Date": ["not-a-date"],
                    "Close": [100.0],
                }
            ),
            "ORCL",
        )
