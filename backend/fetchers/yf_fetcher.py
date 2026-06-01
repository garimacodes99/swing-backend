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
    """Collapses nested yfinance MultiIndex columns down to simple strings."""
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(col).strip().capitalize() for col in df.columns]
    return df


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = _flatten_columns(df)

    if df.index.name != "Date" and "Date" in df.columns:
        df.set_index("Date", inplace=True)

    # Strip timezones to avoid parquet compatibility issues
    df.index = pd.to_datetime(df.index).tz_localize(None)

    # Build a lowercase → actual-name map for flexible column matching
    col_map = {c.lower(): c for c in df.columns}

    # Normalise column names across different yfinance versions
    rename = {}
    for standard, alternatives in [
        ("Close",  ["adj close", "adjclose"]),
        ("Open",   ["open"]),
        ("High",   ["high"]),
        ("Low",    ["low"]),
        ("Volume", ["volume"]),
    ]:
        if standard not in df.columns:
            for alt in alternatives:
                if alt in col_map:
                    rename[col_map[alt]] = standard
                    break

    if rename:
        df = df.rename(columns=rename)
        logger.debug(f"Renamed columns: {rename}")

    required_cols = ["Open", "High", "Low", "Close", "Volume"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise KeyError(
            f"Missing columns after normalisation: {missing}. "
            f"Available: {df.columns.tolist()}"
        )

    df = df[required_cols].copy()
    df[["Open", "High", "Low", "Close"]] = (
        df[["Open", "High", "Low", "Close"]].astype(float)
    )
    df["Volume"] = df["Volume"].fillna(0).astype(int)
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0]

    return df.sort_index()


def _last_expected_trading_date() -> datetime.date:
    """
    Returns the last date on which NSE market data should be available.
    Accounts for weekends and the 4 PM IST daily candle cutoff.
    Does NOT account for public holidays.
    """
    now   = datetime.datetime.now()
    today = now.date()

    # Before 4 PM the current day's candle is not out yet
    if now.hour < 16:
        today -= datetime.timedelta(days=1)

    # Roll back over Saturday (5) and Sunday (6)
    while today.weekday() >= 5:
        today -= datetime.timedelta(days=1)

    return today


def _is_market_data_stale(last_date: pd.Timestamp) -> bool:
    """Returns True if the cache is missing at least one expected trading day."""
    expected = _last_expected_trading_date()
    return last_date.date() < expected


# ==========================================================
# Core single-ticker fetcher
# ==========================================================

def fetch_ohlc(
    ticker: str,
    period: str = BOOTSTRAP_PERIOD,
    interval: str = "1d",
    force_bootstrap: bool = False,
) -> pd.DataFrame | None:
    """
    Fetch OHLCV data for a single NSE ticker.

    Behaviour:
    - No parquet on disk  → full bootstrap (new ticker path)
    - Parquet exists      → validate → incremental update if stale
    - force_bootstrap=True → skip cache check, always re-download full history

    Returns a cleaned DataFrame or None on failure.
    """
    ticker_clean = str(ticker).strip().replace("\xa0", "").upper()
    if not ticker_clean:
        logger.error("Skipping: empty ticker string received.")
        return None

    symbol    = f"{ticker_clean}.NS"
    file_path = os.path.join(DATA_DIR, f"{ticker_clean}.parquet")

    logger.info(f"[{ticker_clean}] START (symbol={symbol})")

    # ------------------------------------------------------------------
    # PATH A: cache exists and bootstrap not forced → validate + incremental
    # ------------------------------------------------------------------
    if os.path.exists(file_path) and not force_bootstrap:
        logger.info(f"[{ticker_clean}] Cache found. Loading…")
        try:
            df = pd.read_parquet(file_path)

            if df is None or df.empty:
                raise ValueError("Cache file is empty.")

            df = df.sort_index()
            df.index = pd.to_datetime(df.index).tz_localize(None)
            last_date = pd.to_datetime(df.index[-1]).normalize()
            logger.info(f"[{ticker_clean}] Last cached date: {last_date.date()}")

            # Detect unadjusted (pre-split) cache — rebuild if suspicious
            ltp       = df["Close"].iloc[-1]
            max_close = df["Close"].max()
            if max_close > ltp * 3:
                raise ValueError(
                    f"Cache looks unadjusted (max={max_close:.2f}, ltp={ltp:.2f}). Rebuilding."
                )

            if not _is_market_data_stale(last_date):
                logger.info(f"[{ticker_clean}] Cache is up-to-date. Skipping fetch.")
                return df

            # Incremental fetch — only missing days
            fetch_start = last_date + timedelta(days=1)
            logger.info(f"[{ticker_clean}] Incremental fetch from {fetch_start.date()}…")
            try:
                new_df = yf.download(
                    symbol,
                    start=fetch_start,
                    interval=interval,
                    auto_adjust=True,
                    progress=False,
                    threads=False,
                    timeout=30,
                )
            except Exception as dl_err:
                logger.warning(
                    f"[{ticker_clean}] Incremental yf.download() raised: {dl_err}. "
                    f"Returning existing cache."
                )
                return df

            if new_df is not None and not new_df.empty:
                new_df = _clean(new_df)
                df = pd.concat([df, new_df])
                df = df[~df.index.duplicated(keep="last")]
                df = df.sort_index().tail(WINDOW_SIZE)
                df.to_parquet(file_path, index=True)
                logger.info(f"[{ticker_clean}] Cache updated → {len(df)} rows")
            else:
                logger.warning(
                    f"[{ticker_clean}] No new rows returned by yfinance "
                    f"(holiday / weekend / API issue). Returning existing cache."
                )

            return df

        except Exception as e:
            logger.warning(
                f"[{ticker_clean}] Cache validation/update failed: {e}. "
                f"Falling through to full bootstrap."
            )
            # Intentionally no return here — falls through to bootstrap below

    # ------------------------------------------------------------------
    # PATH B: no cache (new ticker) OR cache corrupt OR force_bootstrap=True
    # ------------------------------------------------------------------
    logger.info(f"[{ticker_clean}] Bootstrap: downloading {period} history from Yahoo Finance…")
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
            timeout=30,
        )
    except Exception as dl_err:
        logger.error(f"[{ticker_clean}] Bootstrap yf.download() raised: {dl_err}")
        return None

    if df is None or df.empty:
        logger.error(
            f"[{ticker_clean}] Bootstrap returned no data. "
            f"Verify the NSE symbol is correct: '{symbol}'"
        )
        return None

    logger.info(f"[{ticker_clean}] Raw bootstrap rows: {len(df)}. Cleaning…")
    try:
        df = _clean(df)
    except Exception as clean_err:
        logger.error(f"[{ticker_clean}] Cleaning failed: {clean_err}")
        return None

    if len(df) < 50:
        logger.error(
            f"[{ticker_clean}] Only {len(df)} clean rows — too few to be useful. "
            f"Skipping save. Check if '{symbol}' is a valid NSE symbol."
        )
        return None

    df = df.tail(WINDOW_SIZE)
    df.to_parquet(file_path, index=True)
    logger.info(f"[{ticker_clean}] Bootstrap complete: {len(df)} rows saved → {file_path}")
    return df


# ==========================================================
# Universe-level fetcher (used by run_close_analysis)
# ==========================================================

def fetch_universe(
    tickers: list[str],
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV for a list of NSE tickers.

    - New tickers (no parquet on disk) → full bootstrap automatically
    - Existing tickers                 → incremental update only if stale
    - Failed tickers                   → omitted from result, reason in logs

    Returns: dict mapping ticker → cleaned DataFrame
    """
    results:     dict[str, pd.DataFrame] = {}
    new_tickers: list[str] = []
    old_tickers: list[str] = []

    # Pre-classify tickers so new ones are clearly announced in logs
    for t in tickers:
        t_clean = str(t).strip().replace("\xa0", "").upper()
        if not t_clean:
            continue
        file_path = os.path.join(DATA_DIR, f"{t_clean}.parquet")
        if os.path.exists(file_path):
            old_tickers.append(t_clean)
        else:
            new_tickers.append(t_clean)

    total = len(new_tickers) + len(old_tickers)

    if new_tickers:
        logger.info(
            f"NEW tickers detected (no cache, will bootstrap): {new_tickers}"
        )
    logger.info(
        f"Existing tickers (incremental if stale): {len(old_tickers)} | "
        f"Total universe: {total}"
    )

    # Process new tickers first so failures surface early in logs
    for ticker in new_tickers + old_tickers:
        df = fetch_ohlc(ticker, interval=interval)
        if df is not None and not df.empty:
            results[ticker] = df
        else:
            logger.warning(
                f"[{ticker}] EXCLUDED from analysis — fetch returned no data. "
                f"Check logs above for the exact reason."
            )

    logger.info(
        f"Universe fetch complete: {len(results)}/{total} symbols loaded successfully."
    )
    if len(results) < total:
        failed = set(new_tickers + old_tickers) - set(results.keys())
        logger.warning(f"Failed tickers: {sorted(failed)}")

    return results