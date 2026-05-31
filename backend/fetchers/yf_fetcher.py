import os
import datetime
from datetime import timedelta
import logging

import yfinance as yf
import pandas as pd

# ==========================================================
# Logging
# ==========================================================
logger = logging.getLogger("yf_fetcher")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ==========================================================
# Paths
# ==========================================================
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "utils", "data_store", "ohlcv")
os.makedirs(DATA_DIR, exist_ok=True)

# ==========================================================
# Constants
# ==========================================================
WINDOW_SIZE      = 300
BOOTSTRAP_PERIOD = "2y"

# ==========================================================
# Helpers
# ==========================================================
def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = _flatten_columns(df)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df[["Open", "High", "Low", "Close"]] = (
        df[["Open", "High", "Low", "Close"]].astype(float)
    )
    df["Volume"] = df["Volume"].fillna(0).astype(int)
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0]
    return df.sort_index()

def _is_market_data_stale(last_date: pd.Timestamp) -> bool:
    """Checks if a new Indian market daily candle should be available."""
    now = datetime.datetime.now()
    target_date = now.date()
    
    # Weekend logic
    if now.weekday() == 5: # Saturday
        target_date -= datetime.timedelta(days=1)
    elif now.weekday() == 6: # Sunday
        target_date -= datetime.timedelta(days=2)
    # Market hour logic (before 4 PM)
    elif now.hour < 16:
        target_date -= datetime.timedelta(days=1)
        if target_date.weekday() == 6: # Sunday -> Friday
            target_date -= datetime.timedelta(days=2)

    return last_date.date() < target_date

# ==========================================================
# Core Fetcher
# ==========================================================
def fetch_ohlc(ticker: str, period: str = BOOTSTRAP_PERIOD, interval: str = "1d"):
    symbol    = f"{ticker}.NS"
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")

    logger.info(f"[{ticker}] START")

    if os.path.exists(file_path):
        logger.info(f"[{ticker}] Loading local cache")
        try:
            df = pd.read_parquet(file_path)
            if df is None or df.empty or df.index is None:
                raise ValueError("Empty cache file")

            df = df.sort_index()
            last_date = pd.to_datetime(df.index[-1]).normalize()
            logger.info(f"[{ticker}] Last cached date: {last_date.date()}")

            # Detect unadjusted cache
            ltp = df["Close"].iloc[-1]
            max_close = df["Close"].max()
            if max_close > ltp * 3:
                raise ValueError(f"Cache looks unadjusted. Rebuilding.")

            # Dynamic check (Replacing gap days)
            if not _is_market_data_stale(last_date):
                logger.info(f"[{ticker}] Cache up-to-date. Skipping fetch.")
                return df

            # Incremental fetch
            logger.info(f"[{ticker}] Fetching incremental data...")
            new_df = yf.download(
                symbol,
                start=last_date + timedelta(days=1),
                interval=interval,
                auto_adjust=True,
                progress=False, threads=False, timeout=30,
            )

            if new_df is not None and not new_df.empty:
                new_df = _clean(new_df)
                df = pd.concat([df, new_df])
                df = df[~df.index.duplicated(keep="last")]
                df = df.sort_index().tail(WINDOW_SIZE)
                df.to_parquet(file_path)
                logger.info(f"[{ticker}] Cache updated → {len(df)} rows")
            
            return df

        except Exception as e:
            logger.warning(f"[{ticker}] Cache invalid. Rebuilding. Reason: {e}")
            if os.path.exists(file_path): os.remove(file_path)

    # Bootstrap
    logger.info(f"[{ticker}] Bootstrapping from Yahoo Finance")
    df = yf.download(
        symbol, period=BOOTSTRAP_PERIOD, interval=interval,
        auto_adjust=True, progress=False, threads=False, timeout=30,
    )

    if df is None or df.empty:
        logger.error(f"[{ticker}] Yahoo fetch failed")
        return None

    df = _clean(df)
    if len(df) < 50:
        logger.error(f"[{ticker}] Insufficient history")
        return None

    df = df.tail(WINDOW_SIZE)
    df.to_parquet(file_path)
    return df