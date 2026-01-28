"""
MARKET CLOSE ANALYSIS
--------------------
Generates a clean swing dashboard snapshot using latest available DAILY candle.
"""

from pathlib import Path
import pandas as pd
import logging
import sys
from datetime import datetime

from fetchers.yf_fetcher import fetch_ohlc
from logic.swing_logic import compute_swing_score
from utils.update_index import update_index

# ==========================================================
# Logging
# ==========================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-6s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

# ==========================================================
# Config
# ==========================================================
UNIVERSE_FILE = "universe/stock_universe.csv"
OUTPUT_DIR = Path("output/close")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================================
# FINAL DASHBOARD SCHEMA
# ==========================================================
COLUMN_ORDER = [
    "Ticker",
    "LTP",
    "Volume",

    "RSI_14",
    "RSI_Zone",

    "ATR_PCT",
    "Volatility_Class",

    "SMA_200",
    "Dist_SMA200_PCT",
    "Trend_Regime",

    "Return_3M_PCT",
    "Return_6M_PCT",
    "Return_1Y_PCT",

    "High_52W",
    "Low_52W",

    "Swing_Score",
    "Swing_Label",
]

# ==========================================================
# Helpers
# ==========================================================
def round2(x):
    return round(float(x), 2) if pd.notna(x) else None


def compute_return_pct(df, lookback):
    if df is None or len(df) <= lookback:
        return None
    past = df["Close"].iloc[-(lookback + 1)]
    curr = df["Close"].iloc[-1]
    if pd.isna(past) or past <= 0:
        return None
    return round2(((curr - past) / past) * 100)


def compute_52w_high_low(df, lookback=252):
    if df is None or len(df) < lookback:
        return None, None
    w = df.tail(lookback)
    return round2(w["High"].max()), round2(w["Low"].min())


def rsi_zone(rsi):
    if rsi < 30:
        return "OVERSOLD"
    elif rsi < 45:
        return "WEAK"
    elif rsi <= 65:
        return "HEALTHY"
    else:
        return "OVERBOUGHT"


def volatility_class(atr):
    if atr < 3:
        return "LOW_VOL"
    elif atr <= 5:
        return "MID_VOL"
    else:
        return "HIGH_VOL"

# ==========================================================
# Main
# ==========================================================
def main():

    universe = pd.read_csv(UNIVERSE_FILE)["Ticker"].astype(str).tolist()
    log.info(f"START | Market Close Analysis | Tickers={len(universe)}")

    run_date = datetime.now().strftime("%Y-%m-%d")

    rows = []
    processed = skipped = failed = 0

    for ticker in universe:
        try:
            df = fetch_ohlc(ticker)

            if df is None or df.empty:
                skipped += 1
                continue

            df = df.dropna()

            swing = compute_swing_score(df)

            ltp = round2(df["Close"].iloc[-1])
            rsi = round2(swing["RSI_14"])
            atr = round2(swing["ATR_PCT"])
            sma200 = round2(swing["SMA_200"])

            dist_sma = round2(((ltp - sma200) / sma200) * 100) if sma200 else None
            high_52w, low_52w = compute_52w_high_low(df)

            row = {
                "Ticker": ticker,
                "LTP": ltp,
                "Volume": int(df["Volume"].iloc[-1]),

                "RSI_14": rsi,
                "RSI_Zone": rsi_zone(rsi),

                "ATR_PCT": atr,
                "Volatility_Class": volatility_class(atr),

                "SMA_200": sma200,
                "Dist_SMA200_PCT": dist_sma,
                "Trend_Regime": swing["Trend_Regime"],

                "Return_3M_PCT": compute_return_pct(df, 63),
                "Return_6M_PCT": compute_return_pct(df, 126),
                "Return_1Y_PCT": compute_return_pct(df, 252),

                "High_52W": high_52w,
                "Low_52W": low_52w,

                "Swing_Score": round2(swing["Swing_Score"]),
                "Swing_Label": swing["Swing_Label"],
            }

            rows.append(row)
            processed += 1

        except Exception as e:
            failed += 1
            log.error(f"FAIL | {ticker} | {e}")

    if not rows:
        log.error("No rows generated")
        return

    final_df = pd.DataFrame(rows).reindex(columns=COLUMN_ORDER)

    csv_path = OUTPUT_DIR / f"swing_close_{run_date}.csv"
    json_path = OUTPUT_DIR / f"swing_close_{run_date}.json"

    final_df.to_csv(csv_path, index=False)
    final_df.to_json(json_path, orient="records", indent=2)

    update_index(run_date)

    log.info(f"DONE | Processed={processed} Skipped={skipped} Failed={failed}")
    log.info(f"Saved CSV  → {csv_path}")
    log.info(f"Saved JSON → {json_path}")

# ==========================================================
if __name__ == "__main__":
    main()
