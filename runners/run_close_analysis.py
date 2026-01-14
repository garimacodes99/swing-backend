"""
MARKET CLOSE ANALYSIS
--------------------
Runs swing analysis using the latest available DAILY candle
(auto-detected from market data).

Design guarantees:
- No hardcoded dates
- No silent exits
- Deterministic run date
- Fixed CSV schema & column order
- Progress logging
- Ticker always in column 1

Run:
python -m runners.run_close_analysis
"""

from pathlib import Path
import pandas as pd

from fetchers.yf_fetcher import fetch_ohlc
from logic.swing_logic import compute_swing_score

# ==========================================================
# Config
# ==========================================================
UNIVERSE_FILE = "universe/stock_universe.csv"
OUTPUT_DIR = Path("output/close")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# Canonical CSV Schema (ORDER MATTERS)
# ==========================================================
COLUMN_ORDER = [
    "Ticker",
    "Date",
    "Session",

    "Close",
    "SMA_50",
    "SMA_200",

    "RSI_14",

    "ATR_14",
    "ATR_PCT",

    "Trend_Regime",
    "Extension_Status",

    "Swing_Eligibility",
    "Swing_Score",
    "Swing_Label",
]

# ==========================================================
# Main Runner
# ==========================================================
def main():
    universe = pd.read_csv(UNIVERSE_FILE)["Ticker"].astype(str).tolist()
    total = len(universe)

    print("\n[MARKET CLOSE ANALYSIS]")
    print(f"Total tickers: {total}")

    # ------------------------------------------------------
    # STEP 1: Detect latest available trading date
    # ------------------------------------------------------
    run_date = None

    for ticker in universe:
        df = fetch_ohlc(ticker, period="1y", interval="1d")
        if df is not None and not df.empty:
            run_date = df.index[-1].strftime("%Y-%m-%d")
            break

    if run_date is None:
        print("❌ Could not determine latest trading date from data")
        return

    print(f"Detected trading date: {run_date}\n")

    # ------------------------------------------------------
    # STEP 2: Run close analysis with progress logging
    # ------------------------------------------------------
    rows = []
    processed = 0
    skipped = 0

    for idx, ticker in enumerate(universe, start=1):

        # progress log every 50 tickers
        if idx % 50 == 0:
            print(f"Progress: {idx} / {total}")

        df = fetch_ohlc(ticker, period="1y", interval="1d")

        if df is None or df.empty:
            skipped += 1
            continue

        if run_date not in df.index.astype(str):
            skipped += 1
            continue

        df = df.loc[:run_date]

        try:
            row = compute_swing_score(df)
        except Exception:
            skipped += 1
            continue

        row["Ticker"] = ticker
        row["Date"] = run_date
        row["Session"] = "CLOSE"

        rows.append(row)
        processed += 1

    # ------------------------------------------------------
    # STEP 3: Save output with enforced column order
    # ------------------------------------------------------
    print("\n[SUMMARY]")
    print(f"Processed: {processed}")
    print(f"Skipped  : {skipped}")

    if not rows:
        print("❌ No valid rows generated. File not saved.")
        return

    final_df = pd.DataFrame(rows)

    # enforce schema + column priority
    final_df = final_df.reindex(columns=COLUMN_ORDER, fill_value=None)

    output_path = OUTPUT_DIR / f"swing_close_{run_date}.csv"
    final_df.to_csv(output_path, index=False)

    print(f"\n✅ Saved: {output_path}")
    print("✅ Market close analysis completed successfully\n")

# ==========================================================
# Entry Point
# ==========================================================
if __name__ == "__main__":
    main()
