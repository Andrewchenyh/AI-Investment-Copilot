"""
market_data.py

Core stock data engine for the AI Stock Copilot.

Responsibilities:
- Fetch stock data
- Retrieve company information
- Compute basic financial metrics
- Provide cleaned data for downstream analysis
"""

import yfinance as yf
import pandas as pd
import numpy as np
from functools import lru_cache

class MarketDataEngine:
    """
    Core class for retrieving and processing market data.
    """

    def __init__(self):
        pass

    # --------------------------------------------------
    # Stock Metadata
    # --------------------------------------------------
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
    
