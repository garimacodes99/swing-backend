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
WINDOW_SIZE     = 300          # trading sessions to keep in cache
BOOTSTRAP_PERIOD = "2y"        # ~500 sessions on bootstrap (must be > WINDOW_SIZE)
MAX_CACHE_GAP_DAYS = 4         # FIX 2: gaps ≤ 4 calendar days = weekend/holiday, skip fetch

# ==========================================================
# Helpers
# ==========================================================
def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse MultiIndex columns that yfinance sometimes returns."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only OHLCV, cast types, drop bad rows."""
    df = _flatten_columns(df)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df[["Open", "High", "Low", "Close"]] = (
        df[["Open", "High", "Low", "Close"]].astype(float)
    )
    df["Volume"] = df["Volume"].fillna(0).astype(int)
    df = df.dropna(subset=["Close"])           # drop rows with no close
    df = df[df["Close"] > 0]                   # drop zero-price rows
    return df.sort_index()


# ==========================================================
# Core Fetcher
# ==========================================================
def fetch_ohlc(ticker: str, period: str = BOOTSTRAP_PERIOD, interval: str = "1d"):
    """
    Returns a cleaned OHLCV DataFrame (up to WINDOW_SIZE rows) for `ticker`.

    Key design decisions
    --------------------
    FIX 1 – auto_adjust=True (CRITICAL)
        Tells yfinance to return split/bonus-adjusted Close prices.
        Without this, a 1:1 bonus issue leaves pre-bonus candles at 2×
        the current price inside the 252-day window, producing a
        phantom Weighted Avg well above the stock's actual traded range.
        Both the bootstrap AND incremental fetch must use the same
        setting so the stored series stays on a consistent price scale.

    FIX 2 – Smart cache staleness check
        NSE is closed on weekends and public holidays.  The old check
        `last_date >= today` fires a useless API call every Saturday,
        Sunday, and Monday morning (before market opens).  Instead we
        allow a gap of up to MAX_CACHE_GAP_DAYS calendar days before
        treating the cache as stale.

    FIX 3 – Delete stale cache on corporate-action mismatch
        If the parquet on disk was written with auto_adjust=False and
        the new code uses auto_adjust=True the series will be a
        corrupted mix.  We detect this by checking whether any Close
        in the stored data is more than 3× the latest Close (a clear
        sign of unadjusted pre-bonus prices) and nuke the cache so it
        rebuilds cleanly.
    """
    symbol    = f"{ticker}.NS"
    file_path = os.path.join(DATA_DIR, f"{ticker}.parquet")
    today     = pd.Timestamp.today().normalize()

    logger.info(f"[{ticker}] START")

    # ───────────────────────── LOAD CACHE ─────────────────────────
    if os.path.exists(file_path):
        logger.info(f"[{ticker}] Loading local cache")
        try:
            df = pd.read_parquet(file_path)

            if df is None or df.empty or df.index is None:
                raise ValueError("Empty cache file")

            df = df.sort_index()
            last_date = pd.to_datetime(df.index[-1]).normalize()
            logger.info(f"[{ticker}] Last cached date: {last_date.date()}")

            # FIX 3: Detect unadjusted cache (pre-bonus prices >> current price)
            ltp = df["Close"].iloc[-1]
            max_close = df["Close"].max()
            if max_close > ltp * 3:
                raise ValueError(
                    f"Cache looks unadjusted — max ₹{max_close:.0f} vs LTP ₹{ltp:.0f}. "
                    "Rebuilding with adjusted prices."
                )

            # FIX 2: Skip fetch if gap is just a weekend / public holiday
            gap_days = (today - last_date).days
            if gap_days <= MAX_CACHE_GAP_DAYS:
                logger.info(
                    f"[{ticker}] Cache fresh (gap={gap_days}d ≤ {MAX_CACHE_GAP_DAYS}d) — skipping fetch"
                )
                return df

            # ─────────────── INCREMENTAL FETCH ───────────────
            logger.info(f"[{ticker}] Fetching incremental data (gap={gap_days}d)")
            new_df = yf.download(
                symbol,
                start=last_date + timedelta(days=1),
                interval=interval,
                auto_adjust=True,      # FIX 1: adjusted prices
                progress=False,
                threads=False,
                timeout=30,
            )

            if new_df is not None and not new_df.empty:
                new_df = _clean(new_df)
                df = pd.concat([df, new_df])
                df = df[~df.index.duplicated(keep="last")]
                df = df.sort_index().tail(WINDOW_SIZE)
                df.to_parquet(file_path)
                logger.info(f"[{ticker}] Cache updated → {len(df)} rows")
            else:
                logger.info(f"[{ticker}] No new data from Yahoo (market closed?)")

            return df

        except Exception as e:
            logger.warning(f"[{ticker}] Cache invalid — rebuilding. Reason: {e}")
            try:
                os.remove(file_path)
            except OSError:
                pass
            # fall through to bootstrap

    # ───────────────────────── BOOTSTRAP ──────────────────────────
    logger.info(f"[{ticker}] Bootstrapping from Yahoo Finance")

    df = yf.download(
        symbol,
        period=BOOTSTRAP_PERIOD,
        interval=interval,
        auto_adjust=True,          # FIX 1: adjusted prices
        progress=False,
        threads=False,
        timeout=30,
    )

    if df is None or df.empty:
        logger.error(f"[{ticker}] Yahoo fetch failed — no data returned")
        return None

    df = _clean(df)

    if len(df) < 50:               # relaxed from WINDOW_SIZE — some stocks are newer
        logger.error(f"[{ticker}] Insufficient history ({len(df)} rows < 50)")
        return None

    df = df.tail(WINDOW_SIZE)
    df.to_parquet(file_path)

    logger.info(f"[{ticker}] Bootstrap complete → {len(df)} rows")
    return df