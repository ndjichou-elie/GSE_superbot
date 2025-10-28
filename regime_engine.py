# === regime_engine.py (pure NumPy ADX/ATR; detect_regime + adjust_sl_tp) ===
import numpy as np
from indicators import adx as _adx, atr as _atr
from log import log

def _last(arr_or_series):
    try:
        return float(arr_or_series.iloc[-1])
    except Exception:
        return float(arr_or_series[-1])

def detect_regime(df):
    """
    Detects a simple market regime from the provided M5 DataFrame:
      - 'trending' if ADX >= 25
      - otherwise 'ranging'
      And a volatility overlay:
      - 'high_vol' if ATR% >= 2.0% (ATR / close)
      - else 'low_vol'
    Returns one of: 'trending', 'ranging', 'high_vol', 'low_vol'
    (We choose the dominant signal: trending/ranging prioritized, else vol)
    """
    try:
        high = df["high"].astype(float).values
        low  = df["low"].astype(float).values
        close= df["close"].astype(float).values
        if len(close) < 100:
            log("[REGIME] ❌ Not enough data; defaulting to 'ranging'")
            return "ranging"

        # Compute indicators
        adx_vals = _adx(high, low, close, period=14)
        atr_vals = _atr(high, low, close, period=14)

        if adx_vals.size == 0 or atr_vals.size == 0 or str(adx_vals[-1]) == "nan" or str(atr_vals[-1]) == "nan":
            return "ranging"

        last_adx = float(adx_vals[-1])
        last_atr = float(atr_vals[-1])
        last_px  = float(close[-1])

        atr_pct = (last_atr / last_px) if last_px > 0 else 0.0

        trending = last_adx >= 25.0
        high_vol = atr_pct >= 0.02  # 2% of price

        if trending:
            regime = "trending"
        else:
            regime = "ranging"

        # If not clearly trending and volatility extreme, return vol regime
        if not trending:
            regime = "high_vol" if high_vol else "low_vol"

        log(f"[REGIME] 📊 ADX={last_adx:.1f}, ATR%={atr_pct*100:.2f}% → regime={regime}")
        return regime
    except Exception as e:
        log(f"[REGIME] ⚠️ error during detection: {e}")
        return "ranging"

def adjust_sl_tp(df, sl, tp, regime):
    """
    Scales SL/TP once based on regime.
    We compute distance from last close and apply multipliers, then rebuild levels.

    Rules (conservative):
      - trending:    widen TP x1.25, keep SL x1.00  (let winners run)
      - ranging:     tighten TP x0.80, SL x0.90     (take profit quicker)
      - high_vol:    widen both  x1.40              (avoid stop-outs)
      - low_vol:     tighten both x0.90             (avoid dead money)
    """
    try:
        close = _last(df["close"])
        # Infer direction by where TP sits vs price
        is_buy  = tp > close  # typical for buys
        is_sell = not is_buy

        # current distances
        dist_sl = abs(close - sl)
        dist_tp = abs(tp - close)

        # multipliers
        if regime == "trending":
            m_sl, m_tp = 1.00, 1.25
        elif regime == "ranging":
            m_sl, m_tp = 0.90, 0.80
        elif regime == "high_vol":
            m_sl, m_tp = 1.40, 1.40
        elif regime == "low_vol":
            m_sl, m_tp = 0.90, 0.90
        else:
            m_sl, m_tp = 1.00, 1.00

        new_sl_dist = max(1e-8, dist_sl * m_sl)
        new_tp_dist = max(1e-8, dist_tp * m_tp)

        if is_buy:
            new_sl = close - new_sl_dist
            new_tp = close + new_tp_dist
        else:  # sell
            new_sl = close + new_sl_dist
            new_tp = close - new_tp_dist

        log(f"[REGIME] 🎯 Adjusted SL/TP (regime={regime}) → SL={new_sl:.5f}, TP={new_tp:.5f}")
        return new_sl, new_tp
    except Exception as e:
        log(f"[REGIME] ⚠️ error adjusting SL/TP: {e}")
        # Fallback: return originals unmodified
        return sl, tp
