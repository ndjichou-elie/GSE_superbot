# === trends_engine.py (Google Trends + HTF Trend helper) ===
from datetime import datetime
from log import log

# Google Trends sentiment
from pytrends.request import TrendReq
pytrends = TrendReq(hl="en-US", tz=0)

KEYWORDS = ["forex", "inflation", "recession", "interest rates", "stock market crash"]
CACHE = {"time": None, "data": {}}

def fetch_trends(keywords=KEYWORDS, timeframe="now 7-d", geo=""):
    """Fetch Google Trends interest and cache 10 minutes."""
    global CACHE
    now = datetime.utcnow()
    if CACHE["time"] and (now - CACHE["time"]).seconds < 600:
        return CACHE["data"]
    try:
        pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo, gprop="")
        df = pytrends.interest_over_time()
        if df.empty:
            log("[TRENDS] ❌ No trends data returned")
            return {}
        latest = df.iloc[-1].to_dict()
        CACHE = {"time": now, "data": latest}
        log(f"[TRENDS] 📊 Latest trends: {latest}")
        return latest
    except Exception as e:
        log(f"[TRENDS] ❌ Error fetching trends: {e}")
        return {}

def sentiment_from_trends():
    """
    Compute sentiment score ∈ [-1, 1].
    NOTE: 'stock market crash' should be bearish, not bullish.
    """
    data = fetch_trends()
    if not data:
        return 0.0

    bullish_terms = ["forex"]                      # removed "stock market crash" from bullish
    bearish_terms = ["inflation", "recession", "stock market crash"]

    bullish_score = sum(data.get(k, 0) for k in bullish_terms)
    bearish_score = sum(data.get(k, 0) for k in bearish_terms)

    if bullish_score + bearish_score == 0:
        return 0.0

    score = (bullish_score - bearish_score) / (bullish_score + bearish_score)

    if score > 0:
        log(f"[TRENDS] 🟢 Bullish sentiment detected (score={score:.2f})")
    elif score < 0:
        log(f"[TRENDS] 🔴 Bearish sentiment detected (score={score:.2f})")
    else:
        log(f"[TRENDS] ⚪ Neutral sentiment detected (score={score:.2f})")

    return score


# ================================
# NEW: Higher timeframe trend helper
# ================================
# Uses our own indicators (no TA-Lib) and mt5_connector.get_rates
from indicators import ema, rsi
from mt5_connector import get_rates

def higher_timeframe_trend(symbol: str, timeframe_str: str = "H1"):
    """
    Returns: "UP", "DOWN", or "NEUTRAL" based on EMA200 + RSI(14) on the given HTF.
    - Fetches ~500 bars, requires >= 220 bars to be safe.
    """
    try:
        df = get_rates(symbol, timeframe_str, lookback=500)
        if df is None or len(df) < 220:
            log(f"[HTF] ❌ Not enough HTF data for {symbol} ({timeframe_str})")
            return None

        closes = df["close"].astype(float).values

        ema200 = ema(closes, 200)
        if ema200.size == 0 or str(ema200[-1]) == "nan":
            return None

        r = rsi(closes, 14)
        if r.size == 0 or str(r[-1]) == "nan":
            return None

        if closes[-1] > ema200[-1] and r[-1] > 50:
            return "UP"
        elif closes[-1] < ema200[-1] and r[-1] < 50:
            return "DOWN"
        else:
            return "NEUTRAL"

    except Exception as e:
        log(f"[HTF] ⚠️ Error computing HTF trend for {symbol}: {e}")
        return None
