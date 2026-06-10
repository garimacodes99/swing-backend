# run_close_analysis_supabase.py
# PostgreSQL Direct Connection Version (Approach 2)

import logging
import sys
from datetime import datetime
from pathlib import Path
import pandas as pd

# -------------------------------------------------------------------
# PATH CONFIGURATION
# -------------------------------------------------------------------

BACKEND_DIR  = Path(__file__).resolve().parents[0]
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

UNIVERSE_FILE = BACKEND_DIR / "universe" / "stock_universe.csv"

# -------------------------------------------------------------------
# INTERNAL IMPORTS
# -------------------------------------------------------------------

from fetchers.yf_fetcher import fetch_universe
from logic.swing_logic import compute_swing_score
from supabase_client import get_db  # PostgreSQL version

# -------------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def load_universe() -> list[str]:
    """Read tickers from the CSV universe file."""
    if not UNIVERSE_FILE.exists():
        raise FileNotFoundError(f"Universe file not found: {UNIVERSE_FILE}")

    df = pd.read_csv(UNIVERSE_FILE)

    if "Ticker" not in df.columns:
        raise KeyError(
            f"'Ticker' column not found in {UNIVERSE_FILE}. "
            f"Found columns: {df.columns.tolist()}"
        )

    tickers = (
        df["Ticker"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.replace("\xa0", "", regex=False)
    )

    valid = [t for t in tickers if t]
    logger.info(f"Universe loaded: {len(valid)} tickers")
    return valid


def build_metric_row(company_id: int, ticker: str, date: str, ohlcv_row: dict, logic_output: dict) -> dict:
    """Convert swing_logic output to database row"""
    dist = logic_output.get("Dist_Weighted_Avg_PCT")
    
    return {
        "company_id": company_id,
        "run_date": date,
        "ticker": ticker,
        
        # OHLCV
        "open": ohlcv_row.get("open"),
        "high": ohlcv_row.get("high"),
        "low": ohlcv_row.get("low"),
        "close": ohlcv_row.get("close"),
        "adj_close": ohlcv_row.get("adj_close"),
        "volume": ohlcv_row.get("volume"),
        
        # COMPUTED METRICS
        "ltp": logic_output.get("Ticker_LTP"),
        "trend_status": logic_output.get("Trend_Status"),
        "sma_50": logic_output.get("SMA50"),
        "sma_200": logic_output.get("SMA200"),
        
        "rsi_14": logic_output.get("RSI_14"),
        "momentum_status": logic_output.get("Momentum_Status"),
        
        "weighted_avg": logic_output.get("Weighted_Avg"),
        "distance_pct": dist,
        "distance_status": logic_output.get("Weighted_Avg_Status"),
        
        "current_volume": logic_output.get("Current_Volume"),
        "avg_volume_20d": logic_output.get("Avg_Volume_20D"),
        "relative_volume": logic_output.get("Relative_Volume"),
        "volume_strength": logic_output.get("Volume_Strength"),
        
        "swing_score": logic_output.get("Swing_Score"),
        "setup_type": logic_output.get("Setup_Type"),
    }


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def main() -> None:

    # ── Step 1: Initialize database ─────────────────────────────
    logger.info("=" * 60)
    logger.info("Initializing PostgreSQL connection…")
    
    try:
        db = get_db()
        logger.info("✅ Database connected")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return

    # ── Step 2: Load universe ──────────────────────────────────
    run_date = datetime.now().strftime("%Y-%m-%d")
    
    logger.info(f"Reading universe from: {UNIVERSE_FILE}")
    universe = load_universe()
    logger.info(f"Universe size: {len(universe)} tickers")

    # ── Step 3: Sync companies to database ──────────────────────
    logger.info("=" * 60)
    logger.info("Syncing companies to database…")

    try:
        score_file = BACKEND_DIR / "universe" / "final_score list.csv"
        tags_file  = BACKEND_DIR / "universe" / "tags.csv"

        score_df = pd.read_csv(score_file)
        tags_df  = pd.read_csv(tags_file)

        # Normalize column names
        score_df.columns = score_df.columns.str.strip()
        tags_df.columns  = tags_df.columns.str.strip()

        # Build lookup maps
        score_map = dict(zip(
            score_df["Tickers"].str.strip(),
            score_df["Score"]
        ))
        tags_map = dict(zip(
            tags_df["ticker"].str.strip(),
            tags_df["TAG"].str.strip()
        ))

        companies_data = []
        for ticker in universe:
            companies_data.append({
                "ticker":       ticker,
                "health_score": score_map.get(ticker),
                "tags":         tags_map.get(ticker),
            })

        db.upsert_companies(companies_data)
        logger.info(f"✅ Synced {len(companies_data)} companies")

    except Exception as e:
        logger.error(f"❌ Company sync failed: {e}")
        return

    # ── Step 4: Fetch OHLCV data ───────────────────────────────
    logger.info("=" * 60)
    logger.info("Fetching OHLCV data for universe…")
    
    ohlcv_data = fetch_universe(universe)
    
    if not ohlcv_data:
        logger.error("fetch_universe returned no data. Aborting.")
        return

    logger.info(f"Data available for {len(ohlcv_data)}/{len(universe)} tickers.")

    # ── Step 5: Compute metrics ────────────────────────────────
    logger.info("=" * 60)
    logger.info("Computing swing scores…")

    metrics_rows = []
    failed_tickers = []

    for ticker, df in ohlcv_data.items():
        try:
            # Get company_id
            company_id = db.get_company_id(ticker)
            if not company_id:
                logger.warning(f"[{ticker}] Company not found in database")
                failed_tickers.append(ticker)
                continue
            
            # Compute metrics
            logic_output = compute_swing_score(df)
            
            if not isinstance(logic_output, dict):
                logger.warning(f"[{ticker}] Invalid logic output type")
                failed_tickers.append(ticker)
                continue
            
            if logic_output.get("Error"):
                logger.warning(f"[{ticker}] Logic error: {logic_output['Error']}")
                failed_tickers.append(ticker)
                continue
            
            # Get latest OHLCV row
            latest_row = df.iloc[-1] if len(df) > 0 else {}
            
            # Build metric row
            row = build_metric_row(company_id, ticker, run_date, latest_row.to_dict(), logic_output)
            metrics_rows.append(row)

        except Exception as exc:
            logger.error(f"[{ticker}] Exception: {exc}")
            failed_tickers.append(ticker)

    logger.info(
        f"Metrics computed: {len(metrics_rows)} succeeded, "
        f"{len(failed_tickers)} failed"
    )
    if failed_tickers:
        logger.warning(f"Failed: {sorted(failed_tickers)}")

    # ── Step 6: Upsert to database ─────────────────────────────
    if not metrics_rows:
        logger.error("No metrics generated. Aborting.")
        return

    logger.info("=" * 60)
    logger.info(f"Upserting {len(metrics_rows)} metrics to database…")
    
    try:
        db.upsert_daily_metrics(metrics_rows)
        logger.info("✅ Metrics upserted successfully")
    except Exception as e:
        logger.error(f"❌ Upsert failed: {e}")
        return

    # ── Step 7: Summary ────────────────────────────────────────
    logger.info("=" * 60)
    logger.info(f"Pipeline completed: {len(metrics_rows)} metrics for {run_date}")
    logger.info("✅ All done!")


if __name__ == "__main__":
    main()
