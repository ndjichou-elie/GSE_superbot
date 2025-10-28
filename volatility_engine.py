# === volatility_engine.py (BTC-friendly, no MT5 helper deps) ===
from config import BOT_SETTINGS
from log import log
from indicators import atr

def _last_spread_points(df):
    # MT5 copy_rates returns 'spread' column in points for many brokers
    try:
        return float(df["spread"].iloc[-1])
    except Exception:
        return None

def _last_close(df):
    try:
        return float(df["close"].iloc[-1])
    except Exception:
        return None

def _atr_points(df, period: int = 14):
    # Convert ATR (price units) to "points" scale if spread is in points.
    # We’ll normalize by price and assume "points" ≈ broker point size.
    try:
        h = df["high"].astype(float).values
        l = df["low"].astype(float).values
        c = df["close"].astype(float).values
        a = atr(h, l, c, period=period)
        if a is None or len(a) == 0:
            return None
        return float(a[-1])
    except Exception:
        return None

def spread_ok(symbol: str, df) -> bool:
    """
    Returns True if current spread is acceptable relative to ATR.
    """
    max_pct = float(BOT_SETTINGS.get("max_spread_pct_of_atr", 0.30))  # e.g., 0.60 for BTC
    spread = _last_spread_points(df)
    price  = _last_close(df)
    atr_val= _atr_points(df, period=BOT_SETTINGS.get("atr_period", 14))

    if spread is None or price is None or atr_val is None or atr_val <= 0:
        # If we cannot measure, don't block but log once in a while upstream.
        return True

    # Normalize spread to price units if needed: many crypto brokers store spread in points.
    # Using a rough normalization: percent_of_atr = (spread / atr_val)
    pct_of_atr = spread / atr_val

    if pct_of_atr > max_pct:
        # Keep logs light; caller loops frequently.
        # Example: "[SOR] Spread too high: 0.45 > 0.60 of ATR"
        log(f"[SOR] Spread too high: {pct_of_atr:.2f} > {max_pct:.2f} of ATR → skip")
        return False
    return True
