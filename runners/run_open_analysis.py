"""
OPEN ANALYSIS
-------------
Runs swing analysis in MARKET-OPEN CONTEXT
(using DAILY data, not intraday).

Run command (from project root):
python -m runners.run_open_analysis
"""

from pathlib import Path
import pandas as pd
from datetime import date

from fetchers.yf_fetcher import fetch_ohlc
from logic.swing_logic import compute_swing_score

# ==========================================================
# Ensure output folder exists
# ==========================================================
Path("output/open").mkdir(parents=True, exist_ok=True)

# ==========================================================
# Config
# ==========================================================
TODAY = date.today().isoformat()
UNIVERSE_FILE = "universe/stock_universe.csv"

# ==========================================================
# Main runner
# ==========================================================
def main():
    universe = pd.read_csv(UNIVERSE_FILE)["Ticker"].astype(str)
    total = len(universe)

    print(f"\n[OPEN ANALYSIS] Date: {TODAY}")
    print(f"Total stocks to process: {total}\n")

    rows = []

    for i, ticker in enumerate(universe, start=1):
        print(f"[{i}/{total}] Processing {ticker}")

        try:
            df = fetch_ohlc(
                ticker=ticker,
                period="1y",      # required for SMA 200
                interval="1d"     # daily data only
            )
        except Exception as e:
            print(f"   ❌ Fetch error for {ticker}: {e}")
            continue

        if df is None or df.empty:
            print(f"   ⚠ Skipped {ticker} (no data)")
            continue

        try:
            row = compute_swing_score(df)
        except Exception as e:
            print(f"   ❌ Logic error for {ticker}: {e}")
            continue

        row["Ticker"] = ticker
        row["Date"] = TODAY
        row["Session"] = "OPEN"

        rows.append(row)

    # ======================================================
    # Save output
    # ======================================================
    if not rows:
        print("\n❌ No valid stocks processed. CSV not created.")
        return

    final_df = pd.DataFrame(rows)

    output_path = f"output/open/swing_open_{TODAY}.csv"
    final_df.to_csv(output_path, index=False)

    print(f"\n✅ OPEN analysis completed")
    print(f"Saved file: {output_path}")
    print(f"Stocks written: {len(final_df)}")

# ==========================================================
# Entry point
# ==========================================================
if __name__ == "__main__":
    main()
