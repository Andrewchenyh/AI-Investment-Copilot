import pandas as pd
from pydantic import BaseModel, Field, field_validator

from analysis.stock_analysis import add_all_indicators
from tools.market_data import MarketDataEngine

LOOKBACK_PERIOD = "1y"
INTERVAL = "1d"
MINIMUM_OBSERVATIONS = 50

INDICATOR_CONFIG: dict[str, list[int] | None] = {
    "sma_windows": [20, 50],
    "ema_windows": [20],
    "rsi_windows": [14],
    "bb_windows": [20],
}


class TechnicalAnalysisInput(BaseModel):
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Stock ticker symbol, for example MSFT or AAPL.",
    )

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, value: str) -> str:
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("ticker must not be blank")
        return normalized


class MovingAverageSnapshot(BaseModel):
    sma_20: float
    sma_50: float
    ema_20: float


class MacdSnapshot(BaseModel):
    line: float
    signal: float
    histogram: float


class BollingerBandSnapshot(BaseModel):
    middle: float
    upper: float
    lower: float


class TechnicalAnalysisOutput(BaseModel):
    ticker: str
    as_of: str = Field(
        ...,
        description="Date of the latest observation in YYYY-MM-DD format.",
    )
    close: float
    observation_count: int
    moving_averages: MovingAverageSnapshot
    rsi_14: float = Field(..., ge=0, le=100)
    macd: MacdSnapshot
    bollinger_bands: BollingerBandSnapshot
    lookback_period: str = LOOKBACK_PERIOD
    interval: str = INTERVAL
    source: str = "yfinance"


def analyze_technical_indicators_tool(
    args: TechnicalAnalysisInput,
) -> TechnicalAnalysisOutput:
    engine = MarketDataEngine()
    price_history = engine.get_price_history(
        ticker=args.ticker,
        period=LOOKBACK_PERIOD,
        interval=INTERVAL,
    )

    if price_history.empty:
        raise ValueError(
            f"No price data found for ticker '{args.ticker}'."
        )

    if len(price_history) < MINIMUM_OBSERVATIONS:
        raise ValueError(
            f"At least {MINIMUM_OBSERVATIONS} daily observations are required "
            f"for technical analysis of ticker '{args.ticker}'; "
            f"found {len(price_history)}."
        )

    analyzed = add_all_indicators(
        price_history,
        config=INDICATOR_CONFIG,
    )
    latest = analyzed.iloc[-1]

    return TechnicalAnalysisOutput(
        ticker=args.ticker,
        as_of=pd.Timestamp(latest["Date"]).date().isoformat(),
        close=float(latest["Close"]),
        observation_count=len(analyzed),
        moving_averages=MovingAverageSnapshot(
            sma_20=float(latest["SMA_20"]),
            sma_50=float(latest["SMA_50"]),
            ema_20=float(latest["EMA_20"]),
        ),
        rsi_14=float(latest["RSI_14"]),
        macd=MacdSnapshot(
            line=float(latest["MACD"]),
            signal=float(latest["Signal"]),
            histogram=float(latest["Histogram"]),
        ),
        bollinger_bands=BollingerBandSnapshot(
            middle=float(latest["BB_20_Middle"]),
            upper=float(latest["BB_20_Upper"]),
            lower=float(latest["BB_20_Lower"]),
        ),
    )