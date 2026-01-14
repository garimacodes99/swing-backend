"""
HISTORICAL RANGE ANALYSIS
------------------------
Runs swing analysis date-by-date using DAILY data.

Key principles:
- Trading calendar is DATE-DRIVEN (not inferred from stock data)
- Weekends are skipped deterministically
- Missing stock data affects rows, NOT dates
- One CSV per trading day

Run:
python -m runners.run_historical_range
"""

from pathlib import Path
import pandas as pd

from fetchers.yf_fetcher import fetch_ohlc
from logic.swing_logic import compute_swing_score

# ==========================================================
# Ensure output folder exists
# ==========================================================
OUTPUT_DIR = Path("output/historical")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# Config
# ==========================================================
START_DATE = "2025-12-01"
END_DATE   = "2026-01-13"
UNIVERSE_FILE = "universe/stock_universe.csv"

# ==========================================================
# Main runner
# ==========================================================
def main():
    universe = pd.read_csv(UNIVERSE_FILE)["Ticker"].astype(str).tolist()

    print("\n[HISTORICAL RANGE ANALYSIS]")
    print(f"Date range   : {START_DATE} → {END_DATE}")
    print(f"Total stocks : {len(universe)}\n")

    # ------------------------------------------------------
    # STEP 1: Build trading calendar (weekdays only)
    # ------------------------------------------------------
    print("Building trading calendar from date range...")

    trading_days = pd.date_range(
        start=START_DATE,
        end=END_DATE,
        freq="B"  # Business days (Mon–Fri)
    ).strftime("%Y-%m-%d").tolist()

    if len(trading_days) < 20:
        raise RuntimeError("Trading day count too low — calendar logic broken")

    print(f"Trading days detected: {len(trading_days)}")
    print(f"First day: {trading_days[0]}")
    print(f"Last day : {trading_days[-1]}\n")

    # ------------------------------------------------------
    # STEP 2: Run historical analysis day-by-day
    # ------------------------------------------------------
    for run_date in trading_days:
        rows = []
        print(f"[RUNNING] {run_date}")

        for ticker in universe:
            df = fetch_ohlc(ticker, period="2y", interval="1d")

            if df is None or df.empty:
                continue

            if run_date not in df.index.astype(str):
                continue

            # Slice data up to run_date (no lookahead)
            df = df.loc[:run_date]

            try:
                row = compute_swing_score(df)
            except Exception:
                continue

            row["Ticker"]  = ticker
            row["Date"]    = run_date
            row["Session"] = "HISTORICAL"

            rows.append(row)

        if rows:
            final_df = pd.DataFrame(rows)
            output_path = OUTPUT_DIR / f"swing_historical_{run_date}.csv"
            final_df.to_csv(output_path, index=False)

            print(f"   ✅ Saved {output_path} ({len(final_df)} stocks)")
        else:
            print("   ⚠ No valid rows for this day")

    print("\n✅ Historical range analysis completed successfully")

# ==========================================================
# Entry point
# ==========================================================
if __name__ == "__main__":
    main()
