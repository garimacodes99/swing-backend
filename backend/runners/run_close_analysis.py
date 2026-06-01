import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# -------------------------------------------------------------------
# PATH CONFIGURATION
# -------------------------------------------------------------------

BACKEND_DIR  = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

UNIVERSE_FILE      = BACKEND_DIR / "universe" / "stock_universe.csv"
BACKEND_OUTPUT_DIR = BACKEND_DIR / "output" / "close"
FRONTEND_OUTPUT_DIR = PROJECT_ROOT / "frontend" / "public" / "close"

BACKEND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# INTERNAL IMPORTS
# -------------------------------------------------------------------

# fetch_universe handles new-ticker bootstrap + incremental updates automatically
from fetchers.yf_fetcher import fetch_universe
from logic.swing_logic import compute_swing_score
from utils.update_index import update_index
from runners.sync_scores import sync_csv_to_json

# -------------------------------------------------------------------
# LOGGING
# -------------------------------------------------------------------

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------------

COLUMN_ORDER = [
    "Ticker",
    "LTP",
    "Trend Status",
    "RSI 14",
    "Momentum Status",
    "Weighted Avg",
    "Distance %",
    "Distance Status",
    "Volume Strength",
    "Swing Score",
    "Setup Type",
    "Google Finance",
]

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
        .str.replace("\xa0", "", regex=False)   # strip hidden non-breaking spaces
    )

    valid = [t for t in tickers if t]
    logger.info(f"Universe loaded: {len(valid)} tickers from {UNIVERSE_FILE}")
    return valid


def build_row(ticker: str, logic_output: dict) -> dict:
    """Convert a swing_logic output dict into a display row."""
    dist = logic_output.get("Dist_Weighted_Avg_PCT")

    return {
        "Ticker": ticker,
        "LTP":    logic_output.get("Ticker_LTP"),

        "Trend Status":    logic_output.get("Trend_Status"),
        "RSI 14":          logic_output.get("RSI_14"),
        "Momentum Status": logic_output.get("Momentum_Status"),

        "Weighted Avg":  logic_output.get("Weighted_Avg"),
        "Distance %": (
            f"{dist:+.2f}%"
            if dist is not None
            else "0.00%"
        ),
        "Distance Status": logic_output.get("Weighted_Avg_Status"),

        "Volume Strength": logic_output.get("Volume_Strength"),
        "Swing Score":     logic_output.get("Swing_Score"),
        "Setup Type":      logic_output.get("Setup_Type"),

        "Google Finance": f"https://www.google.com/finance/quote/{ticker}:NSE",
    }


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def main() -> None:

    # ── Step 1: sync historical scores ──────────────────────────────
    logger.info("=" * 60)
    logger.info("Starting score sync and universe cleanup…")
    sync_csv_to_json()
    logger.info("Score sync completed.")

    # ── Step 2: load ticker universe ────────────────────────────────
    run_date  = datetime.now().strftime("%Y-%m-%d")
    file_name = f"swing_close_{run_date}.json"

    logger.info(f"Reading universe from: {UNIVERSE_FILE}")
    universe = load_universe()
    logger.info(f"Universe size: {len(universe)} tickers")
    

    # ── Step 3: fetch all OHLCV data ────────────────────────────────
    # fetch_universe() automatically:
    #   • bootstraps NEW tickers (no parquet on disk)
    #   • does incremental update for EXISTING tickers if stale
    #   • logs every failure with an exact reason
    logger.info("=" * 60)
    logger.info("Fetching OHLCV data for universe…")
    ohlcv_data: dict[str, pd.DataFrame] = fetch_universe(universe)

    if not ohlcv_data:
        logger.error("fetch_universe returned no data for ANY ticker. Aborting.")
        return

    logger.info(f"Data available for {len(ohlcv_data)}/{len(universe)} tickers.")

    # ── Step 4: compute swing scores ────────────────────────────────
    logger.info("=" * 60)
    logger.info("Running swing score computation…")

    rows: list[dict] = []
    failed_logic: list[str] = []

    for ticker, df in ohlcv_data.items():
        try:
            logic_output = compute_swing_score(df)

            if not isinstance(logic_output, dict):
                logger.warning(f"[{ticker}] Invalid logic output type: {type(logic_output)}")
                failed_logic.append(ticker)
                continue

            if logic_output.get("Error"):
                logger.warning(f"[{ticker}] Logic error: {logic_output['Error']}")
                failed_logic.append(ticker)
                continue

            rows.append(build_row(ticker, logic_output))

        except Exception as exc:
            logger.error(f"[{ticker}] Unhandled exception in compute_swing_score: {exc}")
            failed_logic.append(ticker)

    logger.info(
        f"Swing scores computed: {len(rows)} succeeded, "
        f"{len(failed_logic)} failed."
    )
    if failed_logic:
        logger.warning(f"Logic failures: {sorted(failed_logic)}")

    # ── Step 5: write output ─────────────────────────────────────────
    if not rows:
        logger.error("No rows generated. JSON file was NOT created.")
        return

    summary_df = pd.DataFrame(rows).reindex(columns=COLUMN_ORDER)

    backend_json_path  = BACKEND_OUTPUT_DIR  / file_name
    frontend_json_path = FRONTEND_OUTPUT_DIR / file_name

    summary_df.to_json(backend_json_path, orient="records", indent=2)
    shutil.copy2(backend_json_path, frontend_json_path)

    update_index(run_date)

    logger.info("=" * 60)
    logger.info(f"Backend  JSON → {backend_json_path}")
    logger.info(f"Frontend JSON → {frontend_json_path}")
    logger.info(f"Pipeline completed: {len(rows)} tickers in output.")

    print("\n" + "-" * 120)
    print(summary_df.to_string(index=False))
    print("-" * 120)


if __name__ == "__main__":
    main()