import pandas as pd
import pytest

from tools.basic_market_tools import (
    CurrentPriceInput,
    HistoricalVolatilityInput,
    get_current_price_tool,
    get_historical_volatility_tool,
)


def test_get_current_price_tool_returns_latest_close(mocker) -> None:
    mock_engine = mocker.patch("tools.basic_market_tools.MarketDataEngine")
    mock_engine.return_value.get_price_history.return_value = pd.DataFrame(
        {
            "Close": [100.0, 105.0, 110.0],
        }
    )

    result = get_current_price_tool(CurrentPriceInput(ticker="orcl"))

    assert result.ticker == "ORCL"
    assert result.price == 110.0
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