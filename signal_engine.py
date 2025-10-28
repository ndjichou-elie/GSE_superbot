# === signal_engine.py ===
import numpy as np
import pandas as pd

from indicators import ema, rsi, adx, atr
from config import STRATEGY_PARAMS, BOT_SETTINGS
from trends_engine import higher_timeframe_trend

def _volume_ok(df: pd.DataFrame) -> bool:
    """
    Volume filter was too strict for BTC. We default it to True.
    If you want it back later, implement your spike logic here.
    """
    return True

def _htf_ok(symbol: str, df: pd.DataFrame, direction: str) -> bool:
    try:
        htf = STRATEGY_PARAMS.get("htf_timeframe", "H1")
        trend = higher_timeframe_trend(symbol, htf)
        if trend is None:
            return True  # don't block if unavailable
        if direction == "BUY":
            return trend in ("UP", "RANGING_UP")
        else:
            return trend in ("DOWN", "RANGING_DOWN")
    except Exception:
        return True

def _latest(values, n=1):
    return values[-n]

def generate_signal(symbol: str, df: pd.DataFrame):
    """
    Return dict with: direction ("BUY"/"SELL"), sl, tp
    or None when no entry.
    """
    if df is None or len(df) < 60:
        return None

    ep = STRATEGY_PARAMS
    ef = int(ep.get("ema_fast", 20))
    es = int(ep.get("ema_slow", 50))
    rper = int(ep.get("rsi_period", 14))
    adx_per = int(ep.get("adx_period", 14))
    atr_per = int(ep.get("atr_period", 14))

    close = df["close"].values

    ema_fast = ema(close, ef)
    ema_slow = ema(close, es)
    rsi_v = rsi(close, rper)
    adx_v = adx(df["high"].values, df["low"].values, close, adx_per)
    atr_v = atr(df["high"].values, df["low"].values, close, atr_per)

    # Not enough history?
    if len(ema_fast) < 2 or len(ema_slow) < 2 or len(rsi_v) < 2 or len(adx_v) < 2 or len(atr_v) < 2:
        return None

    last_close = _latest(close)
    last_ema_fast = _latest(ema_fast)
    last_ema_slow = _latest(ema_slow)
    last_rsi = _latest(rsi_v)
    last_adx = _latest(adx_v)
    last_atr = _latest(atr_v)

    # ------------------------------
    # RELAXED BTC ENTRY CONDITIONS
    # ------------------------------
    # Old: RSI >55 / <45 and volume spike required
    # New: classic momentum cross with RSI>50 / <50, volume optional
    bullish = last_ema_fast > last_ema_slow and last_rsi > 50 and last_adx >= 15
    bearish = last_ema_fast < last_ema_slow and last_rsi < 50 and last_adx >= 15
    vol_ok = _volume_ok(df)

    direction = None
    if bullish and vol_ok and _htf_ok(symbol, df, "BUY"):
        direction = "BUY"
    elif bearish and vol_ok and _htf_ok(symbol, df, "SELL"):
        direction = "SELL"

    if direction is None:
        return None

    # SL/TP using ATR multipliers (regime_engine may adjust once)
    tp_mult = float(ep.get("tp_atr_mult", 2.0))
    sl_mult = float(ep.get("sl_atr_mult", 1.2))
    if direction == "BUY":
        sl = last_close - sl_mult * last_atr
        tp = last_close + tp_mult * last_atr
    else:
        sl = last_close + sl_mult * last_atr
        tp = last_close - tp_mult * last_atr

    return {
        "symbol": symbol,
        "direction": direction,
        "sl": float(sl),
        "tp": float(tp),
        "price": float(last_close),
    }
