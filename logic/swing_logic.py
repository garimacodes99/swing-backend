import pandas as pd
import numpy as np

RSI_PERIOD = 14
ATR_PERIOD = 14

# ==========================================================
# INDICATORS
# ==========================================================

def compute_rsi(close, period=RSI_PERIOD):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_atr(df, period=ATR_PERIOD):
    tr = pd.concat(
        [
            df["High"] - df["Low"],
            (df["High"] - df["Close"].shift()).abs(),
            (df["Low"] - df["Close"].shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()

# ==========================================================
# CORE SWING LOGIC
# ==========================================================

def compute_swing_score(df: pd.DataFrame) -> dict:
    df = df.copy()

    # Indicators
    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["SMA_200"] = df["Close"].rolling(200).mean()
    df["RSI_14"] = compute_rsi(df["Close"])
    df["ATR"] = compute_atr(df)
    df["ATR_PCT"] = (df["ATR"] / df["Close"]) * 100  # ✅ FIXED

    idx = df.index[-1]

    close = round(float(df.at[idx, "Close"]), 2)
    sma50 = df.at[idx, "SMA_50"]
    sma200 = df.at[idx, "SMA_200"]
    rsi = df.at[idx, "RSI_14"]
    atr_pct = df.at[idx, "ATR_PCT"]

    # Guard: insufficient history
    if pd.isna(sma200) or pd.isna(rsi) or pd.isna(atr_pct):
        return {
            "RSI_14": None,
            "ATR_PCT": None,
            "SMA_200": None,
            "Trend_Regime": "WEAK",
            "Swing_Score": 0,
            "Swing_Label": "FORBIDDEN",
            "Volatility_Class": None,
        }

    # ======================================================
    # Volatility Classification
    # ======================================================
    if atr_pct < 3:
        vol_class = "LOW_VOL"
        eligible = close >= sma200
    elif atr_pct <= 5:
        vol_class = "MID_VOL"
        eligible = close >= 0.98 * sma200
    else:
        vol_class = "HIGH_VOL"
        eligible = close >= 0.95 * sma200 and rsi >= 45

    # ======================================================
    # Trend Regime
    # ======================================================
    if close >= sma200 and close <= sma200 * 1.05:
        trend, max_score = "EARLY", 25
    elif close > sma200 * 1.05 and sma50 > sma200:
        trend, max_score = "MATURE", 18
    else:
        trend, max_score = "WEAK", 14

    # ======================================================
    # Extension & Consolidation
    # ======================================================
    extension = int(
        (close > sma50 * 1.10)
        + (close > sma200 * 1.20)
        + (rsi > 70)
        >= 2
    )

    recent = df.tail(20)
    range_pct = ((recent["High"].max() - recent["Low"].min()) / close) * 100

    consolidation = int(
        close >= sma200
        and 45 <= rsi <= 65
        and range_pct <= atr_pct * 1.5
    )

    # ======================================================
    # RAW SCORE
    # ======================================================
    raw_score = (
        (10 if trend == "EARLY" else 6 if trend == "MATURE" else 3)
        + (6 if 45 <= rsi <= 65 else 4 if 40 <= rsi <= 70 else 2)
        + (5 if atr_pct < 3 else 3 if atr_pct < 5 else 1)
        - (3 if extension else 0)
        + (3 if consolidation else 0)
    )

    raw_score = min(raw_score, max_score)
    score = round((raw_score / max_score) * 100, 1)

    label = (
        "BUY" if score >= 70 else
        "NEUTRAL" if score >= 50 else
        "FORBIDDEN"
    )

    # ======================================================
    # FINAL RETURN (STRICT SCHEMA)
    # ======================================================
    return {
        "RSI_14": round(float(rsi), 2),
        "ATR_PCT": round(float(atr_pct), 2),
        "SMA_200": round(float(sma200), 2),
        "Trend_Regime": trend,
        "Swing_Score": score,
        "Swing_Label": label,
        "Volatility_Class": vol_class,
    }
