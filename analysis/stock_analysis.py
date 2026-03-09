"""
technical_indicators.py

Technical indicator calculations for the Stock Copilot project.
Implements common indicators used in quantitative trading analysis.

Indicators included:
- Simple Moving Average (SMA)
- Exponential Moving Average (EMA)
- Relative Strength Index (RSI)
- MACD
- Bollinger Bands
"""

import pandas as pd


class TechnicalIndicators:
    """
    Collection of technical indicator calculations.
    All methods expect a pandas DataFrame containing a 'Close' column.
    """

    @staticmethod
    def sma(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        Simple Moving Average (SMA)

        Parameters
        ----------
        df : DataFrame
            DataFrame with a 'Close' column
        window : int
            Rolling window size

        Returns
        -------
        Series
        """
        return df["Close"].rolling(window=window).mean()

    @staticmethod
    def ema(df: pd.DataFrame, window: int = 20) -> pd.Series:
        """
        Exponential Moving Average (EMA)

        Gives more weight to recent prices.
        """
        return df["Close"].ewm(span=window, adjust=False).mean()

    @staticmethod
    def rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
        """
        Relative Strength Index (RSI)

        Measures momentum on a scale from 0–100.
        Typically:
        - >70 = overbought
        - <30 = oversold
        """
        delta = df["Close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()

        rs = avg_gain / avg_loss

        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(
        df: pd.DataFrame,
        short_window: int = 12,
        long_window: int = 26,
        signal_window: int = 9,
    ) -> pd.DataFrame:
        """
        Moving Average Convergence Divergence (MACD)

        Returns
        -------
        DataFrame with:
        - MACD line
        - Signal line
        - Histogram
        """

        ema_short = df["Close"].ewm(span=short_window, adjust=False).mean()
        ema_long = df["Close"].ewm(span=long_window, adjust=False).mean()

        macd_line = ema_short - ema_long
        signal_line = macd_line.ewm(span=signal_window, adjust=False).mean()
        histogram = macd_line - signal_line

        return pd.DataFrame({
            "MACD": macd_line,
            "Signal": signal_line,
            "Histogram": histogram
        })

    @staticmethod
    def bollinger_bands(
        df: pd.DataFrame,
        window: int = 20,
        num_std: int = 2
    ) -> pd.DataFrame:
        """
        Bollinger Bands

        Upper and lower volatility bands around a moving average.

        Returns
        -------
        DataFrame with:
        - Middle Band (SMA)
        - Upper Band
        - Lower Band
        """

        sma = df["Close"].rolling(window=window).mean()
        std = df["Close"].rolling(window=window).std()

        upper_band = sma + (std * num_std)
        lower_band = sma - (std * num_std)

        return pd.DataFrame({
            "BB_Middle": sma,
            "BB_Upper": upper_band,
            "BB_Lower": lower_band
        })


def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convenience function to append all indicators to a dataframe.

    Parameters
    ----------
    df : DataFrame

    Returns
    -------
    DataFrame with indicators added
    """

    indicators = TechnicalIndicators()

    df["SMA_20"] = indicators.sma(df, 20)
    df["EMA_20"] = indicators.ema(df, 20)
    df["RSI_14"] = indicators.rsi(df, 14)

    macd_df = indicators.macd(df)
    bb_df = indicators.bollinger_bands(df)

    df = pd.concat([df, macd_df, bb_df], axis=1)

    return df