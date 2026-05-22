import os
import sys
import shutil
import logging
import pandas as pd

from pathlib import Path
from datetime import datetime

# ==========================================================
# FIX IMPORT PATHS
# ==========================================================

current_dir = Path(__file__).resolve().parent
root_dir = current_dir.parent

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# ==========================================================
# INTERNAL IMPORTS
# ==========================================================

from fetchers.yf_fetcher import fetch_ohlc
from logic.swing_logic import compute_swing_score
from utils.update_index import update_index

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

log = logging.getLogger(__name__)

# ==========================================================
# PATHS
# ==========================================================

UNIVERSE_FILE = "universe/stock_universe.csv"

# Backend output directory
OUTPUT_DIR = Path("output/close")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Frontend data directory
FRONTEND_CLOSE_DIR = Path("frontend/public/data/close")
FRONTEND_CLOSE_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# COLUMN ORDER
# ==========================================================

COLUMN_ORDER = [
    "Ticker",
    "LTP",
    "RSI 14",
    "Weighted Avg",
    "Distance %",
    "Google Finance"
]

# ==========================================================
# MAIN
# ==========================================================

def main():

    # ======================================================
    # CHECK UNIVERSE FILE
    # ======================================================

    if not os.path.exists(UNIVERSE_FILE):
        log.error(f"❌ Universe file missing: {UNIVERSE_FILE}")
        return

    # ======================================================
    # LOAD STOCK LIST
    # ======================================================

    universe = pd.read_csv(UNIVERSE_FILE)["Ticker"].tolist()

    # ======================================================
    # FILE NAME
    # ======================================================

    run_date = datetime.now().strftime("%Y-%m-%d")

    save_filename = f"swing_close_{run_date}.json"

    full_output_path = OUTPUT_DIR / save_filename

    # ======================================================
    # PROCESS STOCKS
    # ======================================================

    final_rows = []

    log.info(f"\n🚀 Running Close Analysis for {len(universe)} tickers...\n")

    for ticker in universe:

        try:

            ticker = ticker.strip()

            # ==================================================
            # FETCH MARKET DATA
            # ==================================================

            df = fetch_ohlc(ticker)

            if df is None or df.empty:
                log.warning(f"⚠️ No data for {ticker}")
                continue

            # ==================================================
            # COMPUTE SWING LOGIC
            # ==================================================

            logic_output = compute_swing_score(df)

            if "Error" in logic_output:
                log.warning(f"⚠️ Logic error for {ticker}: {logic_output['Error']}")
                continue

            # ==================================================
            # EXTRACT VALUES
            # ==================================================

            ltp = logic_output.get("Ticker_LTP")

            dist = logic_output.get("Dist_Weighted_Avg_PCT")

            final_rows.append({
                "Ticker": ticker,
                "LTP": ltp,
                "RSI 14": logic_output.get("RSI_14"),
                "Weighted Avg": logic_output.get("Weighted_Avg"),
                "Distance %": f"{dist:+.2f}%" if dist is not None else "0.00%",
                "Google Finance": f"https://www.google.com/finance/quote/{ticker}:NSE"
            })

        except Exception as e:

            log.error(f"❌ Error processing {ticker}: {e}")

    # ======================================================
    # NO DATA CHECK
    # ======================================================

    if not final_rows:
        log.error("❌ No data processed. JSON file not created.")
        return

    # ======================================================
    # CREATE DATAFRAME
    # ======================================================

    summary_df = pd.DataFrame(final_rows)

    summary_df = summary_df.reindex(columns=COLUMN_ORDER)

    # ======================================================
    # SAVE JSON TO BACKEND
    # ======================================================

    summary_df.to_json(
        full_output_path,
        orient="records",
        indent=2
    )

    log.info(f"\n✅ Backend JSON saved:")
    log.info(full_output_path)

    # ======================================================
    # COPY TO FRONTEND
    # ======================================================

    frontend_json_path = FRONTEND_CLOSE_DIR / save_filename

    shutil.copy(full_output_path, frontend_json_path)

    log.info(f"\n✅ Copied to frontend:")
    log.info(frontend_json_path)

    # ======================================================
    # UPDATE INDEX
    # ======================================================

    update_index(run_date)

    # ======================================================
    # CONSOLE PREVIEW
    # ======================================================

    print("\n" + "-" * 120)

    print(summary_df.to_string(index=False))

    print("-" * 120)

    # ======================================================
    # FINAL SUCCESS MESSAGE
    # ======================================================

    log.info("\n🎯 Pipeline Completed Successfully")
    log.info("Backend + Frontend synced automatically\n")

# ==========================================================
# RUN
# ==========================================================

if __name__ == "__main__":
    main()