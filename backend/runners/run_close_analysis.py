import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# -------------------------------------------------------------------
# PATH CONFIGURATION
# -------------------------------------------------------------------

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

UNIVERSE_FILE = BACKEND_DIR / "universe" / "stock_universe.csv"
BACKEND_OUTPUT_DIR = BACKEND_DIR / "output" / "close"
FRONTEND_OUTPUT_DIR = PROJECT_ROOT / "frontend" / "public" / "close"

BACKEND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------
# INTERNAL IMPORTS
# -------------------------------------------------------------------

from fetchers.yf_fetcher import fetch_ohlc
from logic.swing_logic import compute_swing_score
from utils.update_index import update_index

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
    "RSI 14",
    "Weighted Avg",
    "Distance %",
    "Google Finance",
]


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def load_universe() -> list[str]:
    if not UNIVERSE_FILE.exists():
        raise FileNotFoundError(f"Universe file not found: {UNIVERSE_FILE}")

    df = pd.read_csv(UNIVERSE_FILE)

    if "Ticker" not in df.columns:
        raise KeyError(f"'Ticker' column not found in {UNIVERSE_FILE}. Found: {df.columns.tolist()}")

    tickers = (
        df["Ticker"]
        .dropna()
        .astype(str)
        .str.strip()
    )

    return [ticker for ticker in tickers if ticker]


def build_row(ticker: str, logic_output: dict) -> dict:
    dist = logic_output.get("Dist_Weighted_Avg_PCT")

    return {
        "Ticker": ticker,
        "LTP": logic_output.get("Ticker_LTP"),
        "RSI 14": logic_output.get("RSI_14"),
        "Weighted Avg": logic_output.get("Weighted_Avg"),
        "Distance %": f"{dist:+.2f}%" if dist is not None else "0.00%",
        "Google Finance": f"https://www.google.com/finance/quote/{ticker}:NSE",
    }


# -------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------

def main() -> None:
    run_date = datetime.now().strftime("%Y-%m-%d")
    file_name = f"swing_close_{run_date}.json"

    logger.info(f"Reading universe from: {UNIVERSE_FILE}")

    universe = load_universe()
    logger.info(f"Running close analysis for {len(universe)} tickers")

    rows: list[dict] = []

    for ticker in universe:
        try:
            df = fetch_ohlc(ticker)

            if df is None or df.empty:
                logger.warning(f"No data for {ticker}")
                continue

            logic_output = compute_swing_score(df)

            if not isinstance(logic_output, dict):
                logger.warning(f"Invalid logic output for {ticker}")
                continue

            if logic_output.get("Error"):
                logger.warning(f"Logic error for {ticker}: {logic_output['Error']}")
                continue

            rows.append(build_row(ticker, logic_output))

        except Exception as exc:
            logger.error(f"Error processing {ticker}: {exc}")

    if not rows:
        logger.error("No rows generated. JSON file was not created.")
        return

    summary_df = pd.DataFrame(rows).reindex(columns=COLUMN_ORDER)

    backend_json_path = BACKEND_OUTPUT_DIR / file_name
    frontend_json_path = FRONTEND_OUTPUT_DIR / file_name

    summary_df.to_json(backend_json_path, orient="records", indent=2)
    shutil.copy2(backend_json_path, frontend_json_path)

    update_index(run_date)

    logger.info(f"Backend JSON saved to: {backend_json_path}")
    logger.info(f"Frontend JSON copied to: {frontend_json_path}")
    logger.info("Pipeline completed successfully")

    print("\n" + "-" * 120)
    print(summary_df.to_string(index=False))
    print("-" * 120)


if __name__ == "__main__":
    main()