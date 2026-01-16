import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

OPEN_FILE = OUTPUT_DIR / "open" / "swing_open_latest.json"
CLOSE_FILE = OUTPUT_DIR / "close" / "swing_close_latest.json"
FINAL_DIR = OUTPUT_DIR / "final"
FINAL_DIR.mkdir(exist_ok=True)

FINAL_FILE = FINAL_DIR / "swing_snapshot_latest.json"


def load_json(path):
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize(row):
    return {
        "ticker": row.get("Ticker"),
        "date": row.get("Entry_Date"),
        "session": row.get("Session"),

        "entry_close": row.get("Entry_Close"),

        "rsi": row.get("RSI_14"),
        "atr": row.get("ATR_14"),
        "atr_pct": row.get("ATR_PCT"),

        "sma_50": row.get("SMA_50"),
        "sma_200": row.get("SMA_200"),

        "trend_status": row.get("Trend_Status"),
        "volatility_class": row.get("Volatility_Class"),

        "past_1m_pct": row.get("Past_1M_%"),
        "past_3m_pct": row.get("Past_3M_%"),
        "past_6m_pct": row.get("Past_6M_%"),

        "swing_score": row.get("Swing_Score"),
        "swing_label": row.get("Swing_Label"),
    }


def main():
    open_rows = load_json(OPEN_FILE)
    close_rows = load_json(CLOSE_FILE)

    final_rows = []

    for row in open_rows + close_rows:
        final_rows.append(normalize(row))

    with open(FINAL_FILE, "w", encoding="utf-8") as f:
        json.dump(final_rows, f, indent=2)

    print("FINAL SNAPSHOT CREATED")
    print(f"Rows written: {len(final_rows)}")
    print(f"File: {FINAL_FILE}")


if __name__ == "__main__":
    main()
