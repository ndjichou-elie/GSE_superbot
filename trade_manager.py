# === trade_manager.py (with Confidence-Based Sizing + SOR-lite) ===
import MetaTrader5 as mt5
import time
from log import log
from config import STRATEGY_PARAMS, BOT_SETTINGS


# -------------------------------
# Spread / Latency / Slippage Check (SOR-lite)
# -------------------------------
def _execution_quality_ok(symbol, expected_price, atr=None):
    """
    Ensures execution quality before sending order.
    - Spread must be <= max_spread_pct_of_atr
    - Latency must be <= max_latency_ms
    - Slippage must be within deviation
    """
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        log(f"[SOR] ❌ Could not fetch tick data for {symbol}")
        return False

    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        log(f"[SOR] ❌ No symbol info for {symbol}")
        return False

    # Spread check
    spread = (tick.ask - tick.bid)
    if atr and atr > 0:
        max_spread = BOT_SETTINGS.get("max_spread_pct_of_atr", 0.3) * atr
        if spread > max_spread:
            log(f"[SOR] ⚠️ Spread too high for {symbol}: {spread:.5f} > {max_spread:.5f}")
            return False

    # Latency check
    start = time.time()
    mt5.symbol_info_tick(symbol)  # re-fetch
    latency_ms = (time.time() - start) * 1000
    if latency_ms > BOT_SETTINGS.get("max_latency_ms", 1000):
        log(f"[SOR] ⚠️ Latency too high for {symbol}: {latency_ms:.2f}ms")
        return False

    # Slippage check
    deviation = BOT_SETTINGS.get("order_deviation", 20)
    if abs(expected_price - tick.ask) > deviation * symbol_info.point:
        log(f"[SOR] ⚠️ Slippage too high for {symbol}")
        return False

    return True


# -------------------------------
# Calculate lot size based on balance and confidence
# -------------------------------
def _calculate_lot(symbol, confidence=0.5):
    account_info = mt5.account_info()
    if account_info is None:
        log("[TRADE] ❌ Could not retrieve account info")
        return 0.0

    balance = account_info.balance
    risk_per_trade = STRATEGY_PARAMS.get("risk_per_trade", 0.01)  # 1% risk
    base_lot = STRATEGY_PARAMS.get("base_lot", 0.1)

    # Scale lot size by confidence (0–1)
    if confidence <= 0.4:
        multiplier = 0.5
    elif confidence >= 0.8:
        multiplier = 2.0
    else:
        multiplier = 1.0

    lot = base_lot * multiplier

    # Risk check: prevent oversizing
    max_lot = balance * risk_per_trade / 1000
    min_lot = BOT_SETTINGS.get("min_lot", 0.01)
    lot = min(max(lot, min_lot), BOT_SETTINGS.get("max_lot", 5.0))

    log(f"[TRADE] 📊 Lot size for {symbol} (conf={confidence}) → {lot:.2f}")
    return round(lot, 2)


# -------------------------------
# Execute trade
# -------------------------------
def execute_trade(symbol, signal):
    if "action" not in signal or signal["action"] == "hold":
        log(f"[TRADE] ⏸ No trade taken for {symbol}")
        return

    lot = _calculate_lot(symbol, confidence=signal.get("confidence", 0.5))
    if lot <= 0:
        log(f"[TRADE] ⚠️ Invalid lot size → skipping trade on {symbol}")
        return

    price = mt5.symbol_info_tick(symbol).ask if signal["action"] == "buy" else mt5.symbol_info_tick(symbol).bid
    sl = signal.get("sl")
    tp = signal.get("tp")

    # === SOR-lite checks ===
    if not _execution_quality_ok(symbol, price, atr=signal.get("atr")):
        log(f"[TRADE] ❌ Trade skipped due to poor execution quality → {symbol}")
        return

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if signal["action"] == "buy" else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": BOT_SETTINGS.get("order_deviation", 20),
        "magic": 123456,
        "comment": f"GSE_SuperBot ({signal['action']}, conf={signal.get('confidence',0.5)})",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None:
        log(f"[TRADE] ❌ Failed to send order for {symbol}")
        return

    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log(f"[TRADE] ❌ Order failed for {symbol}, retcode={result.retcode}")
    else:
        log(f"[TRADE] ✅ {signal['action'].upper()} {symbol} @ {price} | SL={sl} | TP={tp} | Lot={lot}")
# --- Compatibility helpers (for orchestrators that call these) ---
def get_open_positions(symbol: str):
    """Return current MT5 positions for a given symbol."""
    return mt5.positions_get(symbol=symbol) or []

def execute_order(symbol: str, direction: str, lot: float, sl: float | None, tp: float | None):
    """
    Bridge to execute_trade using your existing request shape.
    direction: 'BUY' or 'SELL'
    """
    action = "buy" if direction.upper() == "BUY" else "sell"
    signal = {"action": action, "sl": sl, "tp": tp, "confidence": 0.6}
    return execute_trade(symbol, signal), None  # (ok, ticket placeholder)
