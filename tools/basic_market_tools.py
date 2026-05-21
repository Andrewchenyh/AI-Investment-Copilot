from pydantic import BaseModel, Field

from tools.market_data import MarketDataEngine


class CurrentPriceInput(BaseModel):
    ticker: str = Field(
        ...,
        description="Stock ticker symbol, for example MSFT or AAPL."
    )


class CurrentPriceOutput(BaseModel):
    ticker: str
    price: float
    currency: str = "USD"
    source: str = "yfinance"


def get_current_price_tool(args: CurrentPriceInput) -> CurrentPriceOutput:
    """
    Fetch the most recent available closing price for a stock ticker.

    This is an agent-facing tool wrapper. It uses MarketDataEngine underneath,
    but returns a clean structured payload for the ReAct loop.
    """
    engine = MarketDataEngine()
    price_history = engine.get_price_history(
        ticker=args.ticker,
        period="5d",
        interval="1d",
    )

    if price_history.empty:
        raise ValueError(f"No price data found for ticker '{args.ticker}'.")

    latest_close = float(price_history["Close"].iloc[-1])

    return CurrentPriceOutput(
        ticker=args.ticker.upper(),
        price=latest_close,
        currency="USD",
        source="yfinance",
    )
    
class HistoricalVolatilityInput(BaseModel):
    ticker: str = Field(
        ...,
        description="Stock ticker symbol, for example MSFT or AAPL."
    )
    lookback_days: int = Field(
        default=30,
        ge=5,
        le=252,
        description="Number of recent trading days to use for realized volatility."
    )


class HistoricalVolatilityOutput(BaseModel):
    ticker: str
    lookback_days: int
    annualized_volatility: float
    observation_count: int
    source: str = "yfinance"


def get_historical_volatility_tool(
    args: HistoricalVolatilityInput,
) -> HistoricalVolatilityOutput:
    """
    Compute realized annualized volatility from recent daily closing prices.

    The tool uses daily returns over the requested lookback window and annualizes
    the standard deviation using sqrt(252).
    """
    engine = MarketDataEngine()

    # Pull a slightly wider range than the requested lookback so we have enough
    # rows after non-trading days and return calculation.
    period_days = max(args.lookback_days * 2, 30)
    period = f"{period_days}d"

    price_history = engine.get_price_history(
        ticker=args.ticker,
        period=period,
        interval="1d",
    )

    if price_history.empty:
        raise ValueError(f"No price data found for ticker '{args.ticker}'.")

    recent_prices = price_history.tail(args.lookback_days).copy()

    if len(recent_prices) < 2:
        raise ValueError(
            f"Not enough price history to compute volatility for ticker '{args.ticker}'."
        )

    volatility = engine.compute_volatility(recent_prices)

    return HistoricalVolatilityOutput(
        ticker=args.ticker.upper(),
        lookback_days=args.lookback_days,
        annualized_volatility=volatility,
        observation_count=len(recent_prices),
        source="yfinance",
    )