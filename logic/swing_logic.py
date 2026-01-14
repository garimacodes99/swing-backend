import pandas as pd
import numpy as np

RSI_PERIOD = 14
ATR_PERIOD = 14

# ---------------- INDICATORS ---------------- #

def compute_rsi(close, period=RSI_PERIOD):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_atr(df, period=ATR_PERIOD):
    tr = pd.concat([
        df["High"] - df["Low"],
        (df["High"] - df["Close"].shift()).abs(),
        (df["Low"] - df["Close"].shift()).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

# ---------------- CORE LOGIC ---------------- #

def compute_swing_score(df: pd.DataFrame) -> pd.Series:
    df = df.copy()

    df["SMA_50"] = df["Close"].rolling(50).mean()
    df["SMA_200"] = df["Close"].rolling(200).mean()
    df["RSI_14"] = compute_rsi(df["Close"])
    df["ATR"] = compute_atr(df)
    df["ATR_Percent"] = (df["ATR"] / df["Close"]) * 100

    idx = df.index[-1]

    close = df.at[idx, "Close"]
    sma50 = df.at[idx, "SMA_50"]
    sma200 = df.at[idx, "SMA_200"]
    rsi = df.at[idx, "RSI_14"]
    atr_pct = df.at[idx, "ATR_Percent"]

    # Volatility
    if atr_pct < 3:
        vol_class = "LOW_VOL"
        eligible = close >= sma200
    elif atr_pct <= 5:
        vol_class = "MID_VOL"
        eligible = close >= 0.98 * sma200
    else:
        vol_class = "HIGH_VOL"
        eligible = (close >= 0.95 * sma200) and (rsi >= 45)

    # Trend regime
    if close > sma200 and sma50 > sma200:
        regime, max_score = "Bull", 25
    elif abs(close - sma200) / sma200 <= 0.03:
        regime, max_score = "Transition", 18
    else:
        regime, max_score = "Recovery", 14

    # Extension
    extension = int(
        (close > sma50 * 1.10) +
        (close > sma200 * 1.20) +
        (rsi > 70) >= 2
    )

    # Consolidation
    recent = df.tail(20)
    range_pct = ((recent["High"].max() - recent["Low"].min()) / close) * 100

    consolidation = int(
        close >= sma200 and
        45 <= rsi <= 65 and
        range_pct <= atr_pct * 1.5
    )

    score = (
        (10 if regime == "Bull" else 6 if regime == "Transition" else 3) +
        (6 if 45 <= rsi <= 65 else 4 if 40 <= rsi <= 70 else 2) +
        (5 if atr_pct < 3 else 3 if atr_pct < 5 else 1) -
        (3 if extension else 0) +
        (3 if consolidation else 0)
    )

    score = min(score, max_score)

    if consolidation and regime in ["Bull", "Transition"] and atr_pct < 4:
        score = max(score, 12)

    label = "BUY" if score >= 18 else "NEUTRAL" if score >= 12 else "FORBIDDEN"

    df.at[idx, "Volatility_Class"] = vol_class
    df.at[idx, "Trend_Status"] = regime
    df.at[idx, "Extension_Status"] = extension
    df.at[idx, "Swing_Eligibility"] = int(eligible)
    df.at[idx, "Swing_Score"] = round(score, 1)
    df.at[idx, "Swing_Label"] = label

    return df.loc[idx]
