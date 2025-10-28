# === prediction_engine.py (with Adaptive Weights + Sentiment) ===
import MetaTrader5 as mt5
from config import BOT_SETTINGS
from learning_engine import adapt_weights
from news_engine import sentiment_score  # NEW ✅

# --- Helper functions ---
def _get_rates(symbol, bars=60, tfname=None):
    tfname = tfname or BOT_SETTINGS.get("timeframe", "M15")
    tf = getattr(mt5, f"TIMEFRAME_{tfname}", mt5.TIMEFRAME_M15)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
    if rates is None or len(rates) == 0:
        return []
    return list(rates)

def _simple_atr_pct(rates, period=14):
    if len(rates) < period + 1:
        return 0.0
    tr = []
    for i in range(1, len(rates)):
        h = rates[i]['high']; l = rates[i]['low']; pc = rates[i-1]['close']
        tr.append(max(h - l, abs(h - pc), abs(l - pc)))
    atr = sum(tr[-period:]) / period
    price = rates[-1]['close']
    return (atr / price) * 100.0 if price else 0.0

def _linreg_slope(vals):
    n = len(vals)
    if n < 3: return 0.0
    sx = n*(n-1)/2.0
    sxx = (n-1)*n*(2*n-1)/6.0
    sy = sum(vals)
    sxy = sum(i*v for i, v in enumerate(vals))
    denom = (n*sxx - sx*sx)
    if denom == 0: return 0.0
    return (n*sxy - sx*sy) / denom

# --- Main prediction function ---
def predict_short_term(symbol, direction, lookback=20):
    """
    Returns (confidence, details)
    - confidence ∈ [0,1]
    - details = dict of sub-metrics
    """
    rates = _get_rates(symbol, bars=max(60, lookback + 5))
    if len(rates) < lookback + 2:
        return 0.0, {"reason": "not_enough_bars"}

    closes = [r["close"] for r in rates]
    last = closes[-lookback:]

    # 1) Directional win ratio
    moves = [last[i] - last[i-1] for i in range(1, len(last))]
    if direction == "buy":
        wins = sum(1 for m in moves if m > 0)
    else:
        wins = sum(1 for m in moves if m < 0)
    win_ratio = wins / max(1, len(moves))

    # 2) Momentum slope
    slope = _linreg_slope(last)
    avg_abs_move = (sum(abs(m) for m in moves) / max(1, len(moves)))
    norm_slope = (slope / avg_abs_move) if avg_abs_move > 0 else 0.0
    if direction == "sell":
        norm_slope *= -1

    # 3) Breakout bias
    mean_recent = sum(last[:-1]) / max(1, len(last)-1)
    bias = (last[-1] - mean_recent) / (avg_abs_move if avg_abs_move else 1e-9)
    if direction == "sell":
        bias *= -1

    # 4) ATR % sanity
    atr_pct = _simple_atr_pct(rates, period=14)
    min_atr_pct = BOT_SETTINGS.get("min_atr_pct", 0.02)
    vol_ok = 1.0 if atr_pct >= min_atr_pct else 0.0

    # --- Use adaptive weights from learner ---
    weights = adapt_weights()

    slope_term = max(0.0, min(1.0, 0.5 + 0.5*norm_slope))
    bias_term  = max(0.0, min(1.0, 0.5 + 0.5*bias))

    # --- NEW: Sentiment Factor ---
    sentiment = sentiment_score(symbol)
    sentiment_term = 0.5 + (sentiment / 2)  # map [-1,1] → [0,1]
    if direction == "sell":
        sentiment_term = 1 - sentiment_term

    confidence = (
        weights["win_ratio"] * win_ratio +
        weights["slope_term"] * slope_term +
        weights["bias_term"]  * bias_term +
        weights["vol_ok"]     * vol_ok +
        0.10 * sentiment_term   # fixed contribution from news
    )

    details = {
        "win_ratio": round(win_ratio, 3),
        "slope_term": round(slope_term, 3),
        "bias_term": round(bias_term, 3),
        "atr_pct": round(atr_pct, 4),
        "vol_ok": bool(vol_ok),
        "sentiment": round(sentiment, 3),
        "weights": weights,
        "confidence": round(confidence, 3)
    }
    return max(0.0, min(1.0, confidence)), details
