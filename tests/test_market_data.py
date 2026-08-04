import pandas as pd

from tools.market_data import (
    MARKET_DATA_TIMEOUT_SECONDS,
    MarketDataEngine,
)


def test_price_history_uses_explicit_market_data_timeout(mocker) -> None:
    ticker = mocker.Mock()
    ticker.history.return_value = pd.DataFrame(
        {"Close": [100.0]},
        index=pd.DatetimeIndex(
            [pd.Timestamp("2026-07-31")],
            name="Date",
        ),
    )
    ticker_constructor = mocker.patch(
        "tools.market_data.yf.Ticker",
        return_value=ticker,
    )

    result = MarketDataEngine().get_price_history(
        ticker="ORCL",
        period="5d",
        interval="1d",
    )

    ticker_constructor.assert_called_once_with("ORCL")
    ticker.history.assert_called_once_with(
        period="5d",
        interval="1d",
        timeout=MARKET_DATA_TIMEOUT_SECONDS,
    )
    assert result["Date"].iloc[-1] == pd.Timestamp("2026-07-31")
    assert result["Close"].iloc[-1] == 100.0
