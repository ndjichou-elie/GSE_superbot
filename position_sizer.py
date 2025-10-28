# === position_sizer.py (Adaptive Lot Sizing) ===
import MetaTrader5 as mt5
from log import log
from config import STRATEGY_PARAMS
from trade_logger import get_recent_trades
import numpy as np

# ================================
# Get Account Info
# ================================
def _get_balance():
    acc = mt5.account_info()
    if acc is None:
        log("[SIZER] ❌ Failed to fetch account info")
        return 1000  # fallback
    return acc.balance


# ================================
# Recent Performance Factor
# ================================
def _performance_factor():
    trades = get_recent_trades(limit=10)
    if not trades:
        return 1.0  # neutral

    pnls = [t["pnl"] for t in trades if t["pnl"] is not None]
    if not pnls:
        return 1.0

    avg = np.mean(pnls)
    if avg > 0:
        return 1.2  # boost lot size if profitable
    elif avg < 0:
        return 0.8  # reduce lot size if losing
    return 1.0


# ================================
# ATR Volatility Factor
# ================================
def _volatility_factor(atr_value):
    """
    Adjust size based on ATR.
    Higher ATR → smaller position.
    """
    if atr_value is None or atr_value <= 0:
        return 1.0
    return max(0.5, min(1.5, 1.0 / atr_value))


# ================================
# Main Lot Size Calculator
# ================================
def calculate_lot_size(symbol, atr_value=None):
    balance = _get_balance()
    risk_pct = STRATEGY_PARAMS.get("risk_per_trade", 0.01)  # 1% default risk
    base_lot = (balance * risk_pct) / 1000  # rough normalization

    perf_adj = _performance_factor()
    vol_adj = _volatility_factor(atr_value)

    lot_size = base_lot * perf_adj * vol_adj
    lot_size = max(0.01, min(5.0, lot_size))  # clamp between 0.01 and 5.0 lots

    log(f"[SIZER] {symbol} lot={lot_size:.2f} (balance={balance}, perf_adj={perf_adj}, vol_adj={vol_adj})")
    return lot_size
   # --- Compatibility wrapper for strategy_orchestrator ---
def _simple_atr(df, period: int = 14):
    """
    Lightweight ATR (no TA-Lib). Uses classic True Range with previous close.
    Expects columns: 'high','low','close'.
    """
    try:
        import numpy as np
        if df is None or len(df) < period + 2:
            return None
        high = df["high"].astype(float).values
        low = df["low"].astype(float).values
        close = df["close"].astype(float).values
        trs = []
        for i in range(1, len(close)):
            tr = max(
                high[i] - low[i],
                abs(high[i] - close[i - 1]),
                abs(low[i] - close[i - 1]),
            )
            trs.append(tr)
        if len(trs) < period:
            return None
        return float(np.mean(trs[-period:]))
    except Exception:
        return None


def compute_lot(symbol: str, df=None, direction: str | None = None):
    """
    Backwards-compatible function used by strategy_orchestrator.
    - If df is provided, we compute a simple ATR and pass it into the sizer.
    - Otherwise we size without ATR adjustment.
    """
    atr_value = _simple_atr(df) if df is not None else None
    return float(calculate_lot_size(symbol, atr_value=atr_value))
