"""
Deterministic technical-indicator calculations for AI Investment Copilot.

All functions operate on caller-provided pandas data and perform no external
I/O. Market-data retrieval and presentation belong to higher-level modules.
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

        Measures momentum on a scale from 0-100.
        Typically:
        - >70 = overbought
        - <30 = oversold

        Edge cases:
        - flat prices after the warmup window return 50
        - no losses with gains returns 100
        - losses with no gains returns 0
        """
        delta = df["Close"].diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.rolling(window=window).mean()
        avg_loss = loss.rolling(window=window).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        rsi = rsi.mask((avg_gain == 0) & (avg_loss == 0), 50)
        rsi = rsi.mask((avg_gain > 0) & (avg_loss == 0), 100)
        rsi = rsi.mask((avg_gain == 0) & (avg_loss > 0), 0)

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
        window: int = 20
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

        upper_band = sma + (std * 2)
        lower_band = sma - (std * 2)

        return pd.DataFrame({
            f"BB_{window}_Middle": sma,
            f"BB_{window}_Upper": upper_band,
            f"BB_{window}_Lower": lower_band
        })



def add_all_indicators(
    df: pd.DataFrame,
    config: dict[str, list[int] | None] | None = None,
) -> pd.DataFrame:
    """
    Adds technical indicators with configurable parameters.
    """
    df = df.copy()
    indicators = TechnicalIndicators()
    resolved_config = {} if config is None else config

    def windows_for(key: str, default: int) -> list[int]:
        windows = resolved_config.get(key)
        return [default] if windows is None else windows

    # Technical Indicators with single column returns
    for w in windows_for("sma_windows", 20):
        df[f'SMA_{w}'] = indicators.sma(df, w)

    for w in windows_for("ema_windows", 20):
        df[f'EMA_{w}'] = indicators.ema(df, w)

    for w in windows_for("rsi_windows", 14):
        df[f'RSI_{w}'] = indicators.rsi(df, w)

    macd_data = indicators.macd(df)
    df = df.join(macd_data)

    for w in windows_for("bb_windows", 20):
        bb_data = indicators.bollinger_bands(df, w)
        df = df.join(bb_data)

    return df
