import yfinance as yf
import pandas as pd

def fetch_ohlc(ticker: str, period="1y", interval="1d"):
    """
    Fetch OHLC data from yfinance for NSE stocks.

    ticker: stock symbol WITHOUT .NS
    """

    symbol = ticker + ".NS"

    df = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False
    )

    if df is None or df.empty or len(df) < 200:
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df[["Open", "High", "Low", "Close"]].astype(float)

    return df
