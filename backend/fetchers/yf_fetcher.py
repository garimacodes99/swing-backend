import os
import datetime
from datetime import timedelta
import logging

import pytz
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
IST              = pytz.timezone("Asia/Kolkata")

# ==========================================================
# Helpers
# ==========================================================

def _now_ist() -> datetime.datetime:
    """Current datetime in IST — used everywhere instead of datetime.now()."""
    return datetime.datetime.now(IST)


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
    Uses IST timezone correctly.
    Accounts for weekends and the 3:30 PM IST NSE market close.
    Does NOT account for public holidays.
    """
    now   = _now_ist()
    today = now.date()

    # NSE closes at 3:30 PM IST
    # Before 3:30 PM → today's candle is not confirmed yet, expect yesterday's
    market_close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if now < market_close_time:
        today -= datetime.timedelta(days=1)

    # Roll back over Saturday (5) and Sunday (6)
    while today.weekday() >= 5:
        today -= datetime.timedelta(days=1)

    return today


def _is_market_data_stale(last_date: pd.Timestamp) -> bool:
    """Returns True if the cache is missing at least one expected trading day."""
    expected = _last_expected_trading_date()
    return last_date.date() < expected


def _is_market_open() -> bool:
    """
    Returns True if NSE market is currently open.
    NSE timings: Monday–Friday, 9:15 AM – 3:30 PM IST.
    Does NOT account for public holidays.
    """
    now = _now_ist()

    # Weekend
    if now.weekday() >= 5:
        return False

    market_open  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)

    return market_open <= now <= market_close


# ==========================================================
# Live price helpers
# ==========================================================

def fetch_live_price(ticker: str) -> float | None:
    """
    Fetch the last traded price for a single NSE ticker right now.
    Works whether market is open or closed (returns LTP).
    """
    ticker_clean = str(ticker).strip().replace("\xa0", "").upper()
    symbol = f"{ticker_clean}.NS"

    try:
        tick  = yf.Ticker(symbol)
        price = tick.fast_info.last_price
        if price and float(price) > 0:
            logger.info(f"[{ticker_clean}] Live price fetched: {price:.2f}")
            return float(price)
        else:
            logger.warning(f"[{ticker_clean}] fast_info returned no valid price.")
            return None
    except Exception as e:
        logger.error(f"[{ticker_clean}] fetch_live_price() failed: {e}")
        return None


def _build_todays_row(ticker_clean: str) -> pd.DataFrame | None:
    """
    Build today's OHLCV row using intraday 1-minute data.
    - Open  → first candle's open of the day
    - High  → highest high so far today
    - Low   → lowest low so far today
    - Close → last candle's close (= current price right now)
    - Volume→ cumulative volume so far today

    If market is closed and today is a trading day, returns today's
    confirmed EOD candle via 1d download instead.
    """
    symbol = f"{ticker_clean}.NS"
    today  = datetime.date.today()

    # Weekend — no row needed
    if datetime.date.today().weekday() >= 5:
        return None

    try:
        if _is_market_open():
            # Market open → use 1m intraday to get live OHLCV
            logger.info(f"[{ticker_clean}] Market open — fetching 1m intraday for live row…")
            intraday = yf.download(
                symbol,
                start=today,
                interval="1m",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=30,
            )

            if intraday is None or intraday.empty:
                logger.warning(f"[{ticker_clean}] 1m intraday returned empty.")
                return None

            intraday = _flatten_columns(intraday)
            intraday.index = pd.to_datetime(intraday.index).tz_localize(None)

            row = pd.DataFrame([{
                "Open":   float(intraday["Open"].iloc[0]),    # day open
                "High":   float(intraday["High"].max()),       # day high so far
                "Low":    float(intraday["Low"].min()),        # day low so far
                "Close":  float(intraday["Close"].iloc[-1]),  # current price
                "Volume": int(intraday["Volume"].sum()),       # volume so far
            }], index=[pd.Timestamp(today)])

        else:
            # Market closed → fetch today's confirmed 1d candle
            logger.info(f"[{ticker_clean}] Market closed — fetching confirmed EOD candle…")
            eod = yf.download(
                symbol,
                start=today,
                end=today + timedelta(days=1),
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=False,
                timeout=30,
            )

            if eod is None or eod.empty:
                logger.warning(f"[{ticker_clean}] EOD 1d fetch returned empty.")
                return None

            eod = _clean(eod)
            row = eod.tail(1)

        logger.info(
            f"[{ticker_clean}] Today's row → "
            f"O:{row['Open'].iloc[0]:.2f}  "
            f"H:{row['High'].iloc[0]:.2f}  "
            f"L:{row['Low'].iloc[0]:.2f}  "
            f"C:{row['Close'].iloc[0]:.2f}  "
            f"V:{row['Volume'].iloc[0]:,}  "
            f"[{'LIVE' if _is_market_open() else 'EOD'}]"
        )
        return row

    except Exception as e:
        logger.warning(f"[{ticker_clean}] _build_todays_row() failed: {e}")
        return None


def _attach_live_row(ticker_clean: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach today's live/EOD row to the historical DataFrame.
    Saves updated DataFrame (including live row) back to parquet.

    - If today's row already exists in df → replace it with fresh data
    - If today's row is new → append it
    - Parquet is overwritten every run so price stays fresh
    """
    today     = pd.Timestamp(datetime.date.today())
    file_path = os.path.join(DATA_DIR, f"{ticker_clean}.parquet")

    # Weekend — nothing to do
    if today.weekday() >= 5:
        logger.info(f"[{ticker_clean}] Weekend — skipping live row attachment.")
        return df

    live_row = _build_todays_row(ticker_clean)
    if live_row is None:
        logger.warning(f"[{ticker_clean}] No live row built — returning df unchanged.")
        return df

    # Drop existing today row (if any) and append fresh one
    if today in df.index:
        df = df.drop(index=today)
        logger.info(f"[{ticker_clean}] Replaced existing today's row with fresh data.")
    else:
        logger.info(f"[{ticker_clean}] Appending fresh today's row.")

    df = pd.concat([df, live_row]).sort_index()
    df = df.tail(WINDOW_SIZE)  # keep window size in check

    # Save to parquet — overwrites previous live row on every run
    try:
        df.to_parquet(file_path, index=True)
        logger.info(
            f"[{ticker_clean}] Parquet updated with live row — "
            f"Close: {live_row['Close'].iloc[0]:.2f} | "
            f"IST Time: {_now_ist().strftime('%H:%M:%S')}"
        )
    except Exception as e:
        logger.error(f"[{ticker_clean}] Failed to save live row to parquet: {e}")

    return df


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
    - No parquet on disk   → full bootstrap (new ticker path)
    - Parquet exists       → validate → incremental update if stale
    - force_bootstrap=True → skip cache, always re-download full history
    - Always attaches today's live/EOD row at the end before returning
      so calculations always use the freshest available price.

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
                logger.info(f"[{ticker_clean}] Historical cache is up-to-date.")
                # Still attach live row — price may have moved since last run
                return _attach_live_row(ticker_clean, df)

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
                    f"Attaching live row to existing cache."
                )
                return _attach_live_row(ticker_clean, df)

            if new_df is not None and not new_df.empty:
                new_df = _clean(new_df)
                df = pd.concat([df, new_df])
                df = df[~df.index.duplicated(keep="last")]
                df = df.sort_index().tail(WINDOW_SIZE)
                df.to_parquet(file_path, index=True)
                logger.info(f"[{ticker_clean}] Historical cache updated → {len(df)} rows")
            else:
                logger.warning(
                    f"[{ticker_clean}] No new historical rows from yfinance "
                    f"(holiday / weekend / API issue). Attaching live row."
                )

            # Always attach live row after incremental update
            return _attach_live_row(ticker_clean, df)

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

    # Attach live row after bootstrap too
    return _attach_live_row(ticker_clean, df)


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
    - Every ticker                     → live row attached & saved to parquet
    - Failed tickers                   → omitted from result, reason in logs

    Returns: dict mapping ticker → cleaned DataFrame with fresh live row
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
        f"Total universe: {total} | "
        f"Market open: {_is_market_open()} | "
        f"IST time: {_now_ist().strftime('%H:%M:%S')}"
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