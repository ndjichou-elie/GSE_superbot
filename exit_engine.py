# === exit_engine.py (No-TA-Lib, with check_exit wrapper) ===
import MetaTrader5 as mt5
import numpy as np
import pandas as pd
from log import log

# -----------------------------
# Lightweight indicators
# -----------------------------
def _ema(series, period: int):
    series = np.asarray(series, dtype=float)
    if len(series) < max(2, period):
        return np.array([])
    k = 2.0 / (period + 1.0)
    out = np.empty_like(series, dtype=float)
    sma = np.nanmean(series[:period])
    out[:period-1] = np.nan
    out[period-1] = sma
    ema_prev = sma
    for i in range(period, len(series)):
        ema_prev = series[i] * k + ema_prev * (1.0 - k)
        out[i] = ema_prev
    return out

def _rsi(series, period: int = 14):
    series = np.asarray(series, dtype=float)
    if len(series) < period + 1:
        return np.array([])
    deltas = np.diff(series)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.empty(len(series)); avg_gain[:] = np.nan
    avg_loss = np.empty(len(series)); avg_loss[:] = np.nan

    avg_gain[period] = gains[:period].mean()
    avg_loss[period] = losses[:period].mean()

    for i in range(period+1, len(series)):
        avg_gain[i] = (avg_gain[i-1]*(period-1) + gains[i-1]) / period
        avg_loss[i]  = (avg_loss[i-1]*(period-1) + losses[i-1]) / period

    rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=(avg_loss!=0))
    rsi = 100.0 - (100.0 / (1.0 + rs))

    out = np.empty(len(series)); out[:] = np.nan
    out[period:] = rsi[period:]
    return out

def _macd(series, fast=12, slow=26, signal=9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    if ema_fast.size == 0 or ema_slow.size == 0:
        return np.array([]), np.array([]), np.array([])
    macd = ema_fast - ema_slow
    sig  = _ema(macd, signal)
    hist = macd - sig
    return macd, sig, hist

# -----------------------------
# Exit decisions
# -----------------------------
def should_exit(symbol, trade_action, lookback=100):
    """
    Decide if we should close or partially close an open trade.
    Returns: "hold" | "partial" | "exit"
    """
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, lookback)
    if rates is None or len(rates) < 50:
        log(f"[EXIT] ❌ Not enough data for {symbol}")
        return "hold"

    df = pd.DataFrame(rates)
    close = df["close"].astype(float).values

    rsi = _rsi(close, 14)
    macd, macd_signal, _ = _macd(close, 12, 26, 9)
    if rsi.size == 0 or macd.size == 0 or macd_signal.size == 0:
        return "hold"

    last_rsi = rsi[-1]
    last_macd = macd[-1]
    last_signal = macd_signal[-1]

    if trade_action == "buy":
        if last_rsi > 70 and last_macd < last_signal:
            log(f"[EXIT] 🚪 Exit BUY {symbol} (overbought & MACD cross)")
            return "exit"
        elif last_rsi > 65:
            log(f"[EXIT] ⚠️ Partial exit BUY {symbol} (RSI={last_rsi:.1f})")
            return "partial"

    elif trade_action == "sell":
        if last_rsi < 30 and last_macd > last_signal:
            log(f"[EXIT] 🚪 Exit SELL {symbol} (oversold & MACD cross)")
            return "exit"
        elif last_rsi < 35:
            log(f"[EXIT] ⚠️ Partial exit SELL {symbol} (RSI={last_rsi:.1f})")
            return "partial"

    return "hold"

def close_trade(symbol, action, partial=False):
    """
    Close or partially close a trade.
    """
    positions = mt5.positions_get(symbol=symbol)
    if not positions:
        log(f"[EXIT] No open positions for {symbol}")
        return

    for pos in positions:
        lot = pos.volume
        close_lot = lot * 0.5 if partial else lot

        price = (
            mt5.symbol_info_tick(symbol).bid if pos.type == mt5.ORDER_TYPE_BUY
            else mt5.symbol_info_tick(symbol).ask
        )

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": close_lot,
            "type": mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "price": price,
            "position": pos.ticket,
            "deviation": 20,
            "magic": 123456,
            "comment": f"ExitEngine ({'partial' if partial else 'full'})",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            log(f"[EXIT] ✅ {'Partial' if partial else 'Full'} exit {symbol} {action.upper()} @ {price}")
        else:
            log(f"[EXIT] ❌ Failed to close trade on {symbol}, retcode={getattr(result,'retcode',None)}")

# -----------------------------
# Compatibility wrapper
# -----------------------------
def check_exit(symbol, df=None, open_positions=None):
    """
    Wrapper to match older orchestrator signature.
    - Inspects live MT5 positions for `symbol`
    - Calls should_exit(...) per position direction
    - Executes partial/full closes via close_trade(...)
    """
    positions = mt5.positions_get(symbol=symbol) or []
    for pos in positions:
        action = "buy" if pos.type == mt5.ORDER_TYPE_BUY else "sell"
        decision = should_exit(symbol, action)
        if decision == "exit":
            close_trade(symbol, action, partial=False)
        elif decision == "partial":
            close_trade(symbol, action, partial=True)
    return True
