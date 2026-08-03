"""
market_data.py

Core stock data engine for the AI Stock Copilot.

Responsibilities:
- Fetch stock data
- Retrieve company information
- Compute basic financial metrics
- Provide cleaned data for downstream analysis
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
import pandas as pd
import yfinance as yf


@dataclass(frozen=True)
class DailyCloseSnapshot:
    price: float
    as_of: str


def extract_latest_daily_close(
    price_history: pd.DataFrame,
    ticker: str,
) -> DailyCloseSnapshot:
    if price_history.empty:
        raise ValueError(
            f"No price data found for ticker '{ticker}'."
        )

    required_columns = {"Date", "Close"}
    missing_columns = sorted(
        required_columns - set(price_history.columns)
    )
    if missing_columns:
        missing_list = ", ".join(missing_columns)
        raise ValueError(
            f"Price data for ticker '{ticker}' is missing required "
            f"columns: {missing_list}."
        )

    latest_row = price_history.iloc[-1]

    try:
        price = float(latest_row["Close"])
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"Latest closing price for ticker '{ticker}' is invalid."
        ) from exc

    if not np.isfinite(price) or price <= 0:
        raise ValueError(
            f"Latest closing price for ticker '{ticker}' must be "
            "finite and positive."
        )

    as_of_timestamp = pd.to_datetime(
        latest_row["Date"],
        errors="coerce",
    )
    if pd.isna(as_of_timestamp):
        raise ValueError(
            f"Latest price date for ticker '{ticker}' is invalid."
        )

    return DailyCloseSnapshot(
        price=price,
        as_of=as_of_timestamp.date().isoformat(),
    )


class MarketDataEngine:
    """
    Core class for retrieving and processing market data.
    """

    def __init__(self):
        pass

    @lru_cache(maxsize=100)
    def get_stock_info(self, ticker: str) -> dict:
        """
        Retrieve company metadata from Yahoo Finance.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            return {
                "ticker": ticker.upper(),
                "company_name": info.get("longName", "N/A"),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": info.get("marketCap", "N/A"),
                "pe_ratio": info.get("trailingPE", "N/A"),
                "forward_pe": info.get("forwardPE", "N/A"),
                "profit_margin": info.get("profitMargins", "N/A"),
                "revenue_growth": info.get("revenueGrowth", "N/A"),
            }
        except Exception as e:
            print(f"Error fetching info for {ticker}: {e}")
            return {"ticker": ticker, "error": "Data unavailable"}


    # --------------------------------------------------
    # Historical Price Data
    # --------------------------------------------------

    def get_price_history(
        self,
        ticker: str,
        period: str = "1y",
        interval: str = "1d"
    ) -> pd.DataFrame:
        """
        Retrieve historical price data.
        """


        stock = yf.Ticker(ticker)
        df = stock.history(
            period=period,
            interval=interval
        )
        if df.empty:
            return pd.DataFrame()

        df = df.reset_index()
        df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)

        if df["Close"].isnull().any():
            df["Close"] = df["Close"].ffill()

        return df


    def get_option_expirations(self, ticker: str) -> list[str]:
        """
        Retrieve available option expiration dates for a ticker.
        """
        stock = yf.Ticker(ticker)
        expirations = stock.options
        return list(expirations)

    def get_options_chain(self, ticker: str, expiration: str) -> dict:
        """
        Retrieve the option chain for a ticker and expiration date.

        Returns a dictionary with 'calls' and 'puts' DataFrames.
        """
        stock = yf.Ticker(ticker)
        chain = stock.option_chain(expiration)

        calls = chain.calls.copy()
        puts = chain.puts.copy()

        return {
            "calls": calls,
            "puts": puts,
        }
    # --------------------------------------------------
    # Return Calculations
    # --------------------------------------------------

    def compute_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute daily returns from closing prices.
        """

        df = df.copy()

        if df.empty:
            return pd.DataFrame()

        df["return"] = df["Close"].pct_change()

        return df

    # --------------------------------------------------
    # Volatility
    # --------------------------------------------------

    def compute_volatility(self, df: pd.DataFrame) -> float:
        """
        Compute annualized volatility.
        """
        if df.empty:
            return 0.00
        returns = df["Close"].pct_change().dropna()

        volatility = returns.std() * np.sqrt(252)

        return float(volatility)


    # --------------------------------------------------
    # Complete Data Pipeline
    # --------------------------------------------------

    def get_full_stock_data(self, ticker: str) -> dict:
        """
        Full pipeline for retrieving and processing stock data.
        """

        info = self.get_stock_info(ticker)

        prices = self.get_price_history(ticker)

        prices = self.compute_returns(prices)

        volatility = self.compute_volatility(prices)

        result = {
            "info": info,
            "price_data": prices,
            "volatility": volatility,
        }

        return result


# --------------------------------------------------
# Simple test run
# --------------------------------------------------

if __name__ == "__main__":

    engine = MarketDataEngine()

    ticker = "AAPL"

    data = engine.get_full_stock_data(ticker)

    print("\nStock Info:")
    print(data["info"])

    print("\nVolatility:")
    print(data["volatility"])

    print("\nPrice Data Preview:")
    print(data["price_data"].tail(10))
