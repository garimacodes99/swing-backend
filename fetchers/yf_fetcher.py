import os
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
WINDOW_SIZE = 300                 # stored trading sessions
BOOTSTRAP_PERIOD = "2y"           # ~500 sessions (must be > WINDOW_SIZE)

# ==========================================================
# Core Fetcher
# ==========================================================
def fetch_ohlc(ticker: str, period=BOOTSTRAP_PERIOD, interval="1d"):
    symbol = f"{ticker}.NS"
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    today = pd.Timestamp.today().normalize()

    logger.info(f"[{ticker}] START")

    # ================= LOAD LOCAL CACHE =================
    if os.path.exists(file_path):
        logger.info(f"[{ticker}] Loading local cache")

        try:
            df = pd.read_parquet(file_path)

            if df is None or df.empty or df.index is None:
                raise ValueError("Invalid local cache")

            df = df.sort_index()
            last_date = pd.to_datetime(df.index[-1])
            logger.info(f"[{ticker}] Last cached date: {last_date.date()}")

            if last_date >= today:
                logger.info(f"[{ticker}] Cache up-to-date")
                return df

            # ================= INCREMENTAL FETCH =================
            logger.info(f"[{ticker}] Fetching incremental data")
            new_df = yf.download(
                symbol,
                start=last_date + timedelta(days=1),
                interval=interval,
                auto_adjust=False,
                progress=False,
                threads=False,
                timeout=30,
            )

            if new_df is not None and not new_df.empty:
                if isinstance(new_df.columns, pd.MultiIndex):
                    new_df.columns = new_df.columns.get_level_values(0)

                new_df = new_df[["Open", "High", "Low", "Close", "Volume"]]
                new_df = new_df.sort_index()

                new_df[["Open", "High", "Low", "Close"]] = (
                    new_df[["Open", "High", "Low", "Close"]].astype(float)
                )
                new_df["Volume"] = new_df["Volume"].fillna(0).astype(int)

                df = pd.concat([df, new_df])
                df = df[~df.index.duplicated(keep="last")]
                df = df.tail(WINDOW_SIZE)

                df.to_parquet(file_path)
                logger.info(f"[{ticker}] Cache updated")

            else:
                logger.info(f"[{ticker}] No new data available")

            return df

        except Exception as e:
            logger.warning(f"[{ticker}] Cache invalid — rebuilding ({e})")
            try:
                os.remove(file_path)
            except OSError:
                pass
            # fall through to bootstrap

    # ================= BOOTSTRAP FETCH =================
    logger.info(f"[{ticker}] Bootstrapping from Yahoo")

    df = yf.download(
        symbol,
        period=BOOTSTRAP_PERIOD,
        interval=interval,
        auto_adjust=False,
        progress=False,
        threads=False,
        timeout=30,
    )

    if df is None or df.empty:
        logger.error(f"[{ticker}] Yahoo fetch failed or no data")
        return None

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.sort_index()

    if len(df) < WINDOW_SIZE:
        logger.error(f"[{ticker}] Insufficient history ({len(df)} rows)")
        return None

    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df[["Open", "High", "Low", "Close"]] = (
        df[["Open", "High", "Low", "Close"]].astype(float)
    )
    df["Volume"] = df["Volume"].fillna(0).astype(int)

    df = df.tail(WINDOW_SIZE)
    df.to_parquet(file_path)

    logger.info(f"[{ticker}] Bootstrap completed")
    return df
