import numpy as np
import pandas as pd


# =========================================================
# CONFIGURATION
# =========================================================

SMA_FAST = 50
SMA_SLOW = 200
RSI_PERIOD = 14
AVG_VOLUME_PERIOD = 20


# =========================================================
# WEIGHTED AVERAGE ENGINE
# =========================================================

def calculate_time_weighted_avg(df: pd.DataFrame) -> float | None:
    """
    Calculates recency-weighted average price using adjusted close.
    Most recent candles receive highest weights.
    """

    df_val = (
        df.sort_index(ascending=True)
        .dropna(subset=["Adj Close"])
        .tail(252)
        .copy()
    )

    total_rows = len(df_val)

    if total_rows < 20:
        return None

    prices = df_val["Adj Close"].values

    indices = np.arange(total_rows)

    weights = (indices / (total_rows - 1)) ** 2

    weighted_sum = np.sum(prices * weights)

    sum_of_weights = np.sum(weights)

    weighted_avg = weighted_sum / sum_of_weights

    return round(float(weighted_avg), 2)


# =========================================================
# TREND ENGINE
# =========================================================

def calculate_trend_engine(df: pd.DataFrame) -> dict:
    """
    Determines long-term trend structure.
    """

    df = df.copy()

    df["SMA50"] = df["Adj Close"].rolling(SMA_FAST).mean()

    df["SMA200"] = df["Adj Close"].rolling(SMA_SLOW).mean()

    latest = df.iloc[-1]

    ltp = latest["Adj Close"]

    sma50 = latest["SMA50"]

    sma200 = latest["SMA200"]

    trend_status = "UNKNOWN"

    if pd.notna(sma200):

        if ltp > sma50 > sma200:
            trend_status = "STRONG_BULLISH"

        elif ltp > sma200:
            trend_status = "BULLISH"

        elif ltp < sma200:
            trend_status = "BEARISH"

        else:
            trend_status = "NEUTRAL"

    return {
        "SMA50": round(float(sma50), 2) if pd.notna(sma50) else None,
        "SMA200": round(float(sma200), 2) if pd.notna(sma200) else None,
        "Trend_Status": trend_status,
    }


# =========================================================
# VOLUME ENGINE
# =========================================================

def calculate_volume_engine(df: pd.DataFrame) -> dict:
    """
    Evaluates participation strength using relative volume.
    """

    df = df.copy()

    df["Avg_Volume_20D"] = df["Volume"].rolling(AVG_VOLUME_PERIOD).mean()

    latest = df.iloc[-1]

    current_volume = latest["Volume"]

    avg_volume = latest["Avg_Volume_20D"]

    relative_volume = None

    volume_strength = "UNKNOWN"

    if pd.notna(avg_volume) and avg_volume != 0:

        relative_volume = current_volume / avg_volume

        if relative_volume >= 2:
            volume_strength = "VERY_HIGH"

        elif relative_volume >= 1.5:
            volume_strength = "HIGH"

        elif relative_volume >= 1:
            volume_strength = "NORMAL"

        else:
            volume_strength = "LOW"

    return {
        "Current_Volume": int(current_volume),
        "Avg_Volume_20D": int(avg_volume) if pd.notna(avg_volume) else None,
        "Relative_Volume": round(float(relative_volume), 2)
        if relative_volume
        else None,
        "Volume_Strength": volume_strength,
    }


# =========================================================
# MOMENTUM ENGINE
# =========================================================

def calculate_momentum_engine(df: pd.DataFrame) -> dict:
    """
    Calculates RSI momentum and momentum direction.
    """

    df = df.copy()

    delta = df["Adj Close"].diff()

    gain = delta.clip(lower=0).rolling(RSI_PERIOD).mean()

    loss = (-delta.clip(upper=0)).rolling(RSI_PERIOD).mean()

    rs = gain / loss

    df["RSI"] = 100 - (100 / (1 + rs))

    latest_rsi = df["RSI"].iloc[-1]

    previous_rsi = df["RSI"].iloc[-2]

    momentum_status = "UNKNOWN"

    if pd.notna(latest_rsi):

        if 45 <= latest_rsi <= 60:
            momentum_status = "HEALTHY"

        elif 60 < latest_rsi <= 70:
            momentum_status = "HOT"

        elif latest_rsi > 70:
            momentum_status = "OVERHEATED"

        elif 35 <= latest_rsi < 45:
            momentum_status = "RECOVERY"

        else:
            momentum_status = "WEAK"

    return {
        "RSI_14": round(float(latest_rsi), 2)
        if pd.notna(latest_rsi)
        else None,
        "Momentum_Status": momentum_status,
    }


# =========================================================
# WEIGHTED AVG POSITION ENGINE
# =========================================================

def calculate_weighted_avg_position(
    ltp: float,
    weighted_avg: float | None,
) -> dict:

    if not weighted_avg:
        return {
            "Weighted_Avg": None,
            "Dist_Weighted_Avg_PCT": None,
            "Weighted_Avg_Status": "UNKNOWN",
        }

    dist_pct = ((ltp - weighted_avg) / weighted_avg) * 100

    if -6 <= dist_pct <= -3:
        status = "IDEAL_ACCUMULATION"

    elif -10 <= dist_pct < -6:
        status = "DEEP_PULLBACK"

    elif 0 <= dist_pct <= 5:
        status = "EXTENDED"

    elif dist_pct > 5:
        status = "OVERHEATED"

    else:
        status = "WEAK"

    return {
        "Weighted_Avg": round(float(weighted_avg), 2),
        "Dist_Weighted_Avg_PCT": round(float(dist_pct), 2),
        "Weighted_Avg_Status": status,
    }


# =========================================================
# SCORE ENGINE
# =========================================================

def calculate_composite_score(
    trend_status: str,
    volume_strength: str,
    momentum_status: str,
    weighted_avg_status: str,
) -> int:

    score = 0

    trend_map = {
    "BULLISH": 30,
    "NEUTRAL": 25,
    "STRONG_BULLISH": 10,
    "BEARISH": 0,
}

    volume_map = {
    "NORMAL": 25,
    "HIGH": 10,
    "VERY_HIGH": 5,
    "LOW": 20,
}

    momentum_map = {
    "HEALTHY": 25,
    "HOT": 10,
    "OVERHEATED": 0,
    "RECOVERY": 15,
    "WEAK": 0,
}

    weighted_avg_map = {
    "IDEAL_ACCUMULATION": 35,
    "DEEP_PULLBACK": 20,
    "EXTENDED": 10,
    "OVERHEATED": 0,
    "WEAK": 0,
}

    score += trend_map.get(trend_status, 0)

    score += volume_map.get(volume_strength, 0)

    score += momentum_map.get(momentum_status, 0)

    score += weighted_avg_map.get(weighted_avg_status, 0)

    return int(score)


# =========================================================
# CLASSIFICATION ENGINE
# =========================================================

def classify_setup(score: int) -> str:

    if score >= 80:
        return "HIGH_CONVICTION"

    if score >= 60:
        return "MOMENTUM_SETUP"

    if score >= 40:
        return "WATCHLIST"

    return "WEAK_SETUP"


# =========================================================
# MAIN SWING ENGINE
# =========================================================

def compute_swing_score(df: pd.DataFrame) -> dict:

    if df.empty or len(df) < 200:
        return {"Error": "Insufficient data"}

    if "Adj Close" not in df.columns:
        df["Adj Close"] = df["Close"]

    latest_price = float(df["Adj Close"].iloc[-1])

    # Trend
    trend_data = calculate_trend_engine(df)

    # Volume
    volume_data = calculate_volume_engine(df)

    # Momentum
    momentum_data = calculate_momentum_engine(df)

    # Weighted Avg
    weighted_avg = calculate_time_weighted_avg(df)

    weighted_avg_data = calculate_weighted_avg_position(
        latest_price,
        weighted_avg,
    )

    # Composite Score
    swing_score = calculate_composite_score(
        trend_status=trend_data["Trend_Status"],
        volume_strength=volume_data["Volume_Strength"],
        momentum_status=momentum_data["Momentum_Status"],
        weighted_avg_status=weighted_avg_data["Weighted_Avg_Status"],
    )

    # Classification
    setup_type = classify_setup(swing_score)

    # Final Output
    return {
        "Ticker_LTP": round(latest_price, 2),

        **trend_data,

        **volume_data,

        **momentum_data,

        **weighted_avg_data,

        "Swing_Score": swing_score,

        "Setup_Type": setup_type,
    }