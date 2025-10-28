# === indicators.py (final) ===
import numpy as np

# -----------------------------
# Exponential Moving Average
# -----------------------------
def ema(series, period: int):
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

# -----------------------------
# Relative Strength Index
# -----------------------------
def rsi(series, period: int = 14):
    series = np.asarray(series, dtype=float)
    if len(series) < period + 1:
        return np.array([])
    deltas = np.diff(series)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.empty_like(series); avg_gain[:] = np.nan
    avg_loss = np.empty_like(series); avg_loss[:] = np.nan
    avg_gain[period] = gains[:period].mean()
    avg_loss[period] = losses[:period].mean()

    for i in range(period+1, len(series)):
        avg_gain[i] = (avg_gain[i-1]*(period-1) + gains[i-1]) / period
        avg_loss[i]  = (avg_loss[i-1]*(period-1) + losses[i-1]) / period

    rs  = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=(avg_loss!=0))
    rsi = 100.0 - (100.0 / (1.0 + rs))

    out = np.empty_like(series); out[:] = np.nan
    out[period:] = rsi[period:]
    return out

# -----------------------------
# True Range helper
# -----------------------------
def _true_range(high, low, close):
    high = np.asarray(high, dtype=float)
    low  = np.asarray(low, dtype=float)
    close= np.asarray(close, dtype=float)
    prev_close = np.roll(close, 1); prev_close[0] = close[0]
    return np.maximum(high - low, np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)))

# -----------------------------
# ATR (Wilder’s)
# -----------------------------
def atr(high, low, close, period: int = 14):
    high = np.asarray(high, dtype=float)
    low  = np.asarray(low, dtype=float)
    close= np.asarray(close, dtype=float)
    if len(close) < period + 1:
        return np.array([])
    tr = _true_range(high, low, close)
    out = np.empty_like(close); out[:] = np.nan
    out[period] = np.mean(tr[1:period+1])  # first ATR = avg TR
    for i in range(period+1, len(close)):
        out[i] = (out[i-1]*(period-1) + tr[i]) / period
    return out

# -----------------------------
# ADX (Wilder’s)
# -----------------------------
def adx(high, low, close, period: int = 14):
    h = np.asarray(high, dtype=float)
    l = np.asarray(low,  dtype=float)
    c = np.asarray(close,dtype=float)
    if len(c) < period*2 + 1:
        return np.array([])

    up_move   = h[1:] - h[:-1]
    down_move = l[:-1] - l[1:]
    plus_dm  = np.where((up_move >  down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    tr  = _true_range(h, l, c)
    atr_vals = np.empty_like(c); atr_vals[:] = np.nan
    atr_vals[period] = np.mean(tr[1:period+1])
    for i in range(period+1, len(c)):
        atr_vals[i] = (atr_vals[i-1]*(period-1) + tr[i]) / period

    plus_di  = 100.0 * (np.convolve(plus_dm, np.ones(period), 'full')[:len(c)-1] / period)  / np.where(atr_vals[1:],  atr_vals[1:],  np.nan)
    minus_di = 100.0 * (np.convolve(minus_dm,np.ones(period), 'full')[:len(c)-1] / period)  / np.where(atr_vals[1:],  atr_vals[1:],  np.nan)

    # pad to align lengths with c
    plus_di_full  = np.empty_like(c); plus_di_full[:]  = np.nan; plus_di_full[1:]  = plus_di
    minus_di_full = np.empty_like(c); minus_di_full[:] = np.nan; minus_di_full[1:] = minus_di

    dx = 100.0 * np.abs(plus_di_full - minus_di_full) / (plus_di_full + minus_di_full)
    out = np.empty_like(c); out[:] = np.nan
    if len(dx[period:period*2]) == period:
        out[period*2-1] = np.nanmean(dx[period:period*2])
        for i in range(period*2, len(c)):
            out[i] = (out[i-1]*(period-1) + dx[i]) / period
    return out

# (Optional) keep old helper names in case other modules call them
def atr_from_arrays(high, low, close, period=14): return atr(high, low, close, period)
def adx_from_arrays(high, low, close, period=14): return adx(high, low, close, period)
def calculate_atr(high, low, close, period=14):   return atr(high, low, close, period)
def calculate_adx(high, low, close, period=14):   return adx(high, low, close, period)
