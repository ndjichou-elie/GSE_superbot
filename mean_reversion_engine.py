# === mean_reversion_engine.py (RSI Mean Reversion Strategy) ===
import MetaTrader5 as mt5
import pandas as pd
from indicators import calculate_rsi, calculate_atr
from config import STRATEGY_PARAMS
from log import log

def compute_mean_reversion_signal(symbol, timeframe=mt5.TIMEFRAME_M15):
    """
    Mean reversion strategy based on RSI extremes.
    Buy when RSI < 30 (oversold).
    Sell when RSI > 70 (overbought).
    """

    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 500)
    if rates is None or len(rates) < 50:
        log(f"[MEANREV] ❌ Not enough data for {symbol}")
        return {"action": "hold"}

    df = pd.DataFrame(rates)
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)

    rsi = calculate_rsi(df['close'], STRATEGY_PARAMS["rsi_period"])
    atr = calculate_atr(df['high'], df['low'], df['close'], STRATEGY_PARAMS["atr_period"])

    latest_price = df['close'].iloc[-1]
    latest_rsi = rsi.iloc[-1]

    if latest_rsi < 30:
        # Oversold → Buy
        sl = latest_price - atr.iloc[-1] * STRATEGY_PARAMS["atr_multiplier_sl"]
        tp = latest_price + atr.iloc[-1] * STRATEGY_PARAMS["atr_multiplier_tp"]
        log(f"[MEANREV] ✅ Oversold detected → BUY {symbol}")
        return {"action": "buy", "sl": sl, "tp": tp, "strategy": "mean_reversion"}

    elif latest_rsi > 70:
        # Overbought → Sell
        sl = latest_price + atr.iloc[-1] * STRATEGY_PARAMS["atr_multiplier_sl"]
        tp = latest_price - atr.iloc[-1] * STRATEGY_PARAMS["atr_multiplier_tp"]
        log(f"[MEANREV] ✅ Overbought detected → SELL {symbol}")
        return {"action": "sell", "sl": sl, "tp": tp, "strategy": "mean_reversion"}

    else:
        return {"action": "hold", "strategy": "mean_reversion"}
