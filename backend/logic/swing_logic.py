import pandas as pd
import numpy as np

def calculate_time_weighted_avg(df):
    """
    Calculates price weighted by recency.
    FORCED ALIGNMENT: Ensures today's price ALWAYS gets the max weight.
    """
    # 1. Prepare data (Ensure oldest-to-newest for calculation)
    # If the index is already sorted, this just ensures we are looking at the right tail
    df_val = df.sort_index(ascending=True).dropna(subset=['Adj Close']).tail(252).copy()
    total_rows = len(df_val)
    
    if total_rows < 20: 
        return None
    
    # 2. Extract prices as a numpy array
    prices = df_val['Adj Close'].values
    
    # 3. Create Weights: 0 to 1 squared
    # np.arange(total_rows) creates [0, 1, 2, ... 251]
    # This ensures the HIGHEST index (Today) gets the HIGHEST weight.
    indices = np.arange(total_rows)
    weights = (indices / (total_rows - 1)) ** 2
    
    # 4. Math: Sum(Price * Weight) / Sum(Weights)
    weighted_sum = np.sum(prices * weights)
    sum_of_weights = np.sum(weights)
    
    raw_weighted_avg = weighted_sum / sum_of_weights
    
    # DEBUG: Uncomment the line below if you want to see the math in your console
    # print(f"DEBUG: LTP={prices[-1]}, W_AVG={raw_weighted_avg}, WEIGHT_LAST={weights[-1]}")
    
    return round(float(raw_weighted_avg), 2)

def compute_swing_score(df: pd.DataFrame) -> dict:
    if df.empty or len(df) < 20:
        return {"Error": "Insufficient data"}

    # Ensure we use Adjusted prices for everything to match the chart
    if 'Adj Close' not in df.columns:
        df['Adj Close'] = df['Close']

    # 1. RSI on Adjusted Close
    delta = df["Adj Close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi_val = 100 - (100 / (1 + rs.iloc[-1]))
    
    # 2. Weighted Average
    weighted_avg = calculate_time_weighted_avg(df)
    
    # 3. LTP (Must be Adjusted to match Weighted Avg)
    ltp = df["Adj Close"].iloc[-1]
    
    dist_pct = None
    if weighted_avg and weighted_avg != 0:
        # If LTP > Weighted Avg, distance is positive (Stock is RISING)
        # If LTP < Weighted Avg, distance is negative (Stock is FALLING)
        dist_pct = round(((ltp - weighted_avg) / weighted_avg) * 100, 2)

    return {
        "Ticker_LTP": round(float(ltp), 2),
        "RSI_14": round(float(rsi_val), 2) if pd.notna(rsi_val) else None,
        "Weighted_Avg": weighted_avg,
        "Dist_Weighted_Avg_PCT": dist_pct
    }