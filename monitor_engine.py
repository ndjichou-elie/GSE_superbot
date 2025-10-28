# === monitor_engine.py (Resilient Version) ===
import MetaTrader5 as mt5
import time
from config import BOT_SETTINGS
from log import log


# -------------------------------
# Health Check
# -------------------------------
def check_health():
    """
    Check if MT5 terminal is connected and responsive.
    - Ensures account info is available
    - Tries ALL configured symbols until one responds
    - Measures latency instead of relying on .ping
    """
    account_info = mt5.account_info()
    if account_info is None:
        log("[HEALTH] ❌ No account info → MT5 not connected")
        return False

    terminal_info = mt5.terminal_info()
    if terminal_info is None or not terminal_info.connected:
        log("[HEALTH] ❌ Terminal not connected to broker")
        return False

    symbols = BOT_SETTINGS.get("symbols", ["EURUSDm"])
    max_latency = BOT_SETTINGS.get("max_latency_ms", 1000)

    for sym in symbols:
        start = time.time()
        rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_M1, 0, 1)
        elapsed_ms = (time.time() - start) * 1000

        if rates is not None and len(rates) > 0:
            if elapsed_ms > max_latency:
                log(f"[HEALTH] ⚠️ Latency high on {sym}: {elapsed_ms:.0f}ms > {max_latency}ms")
            else:
                log(f"[HEALTH] ✅ {sym} OK: {elapsed_ms:.0f}ms")
            return True  # ✅ Success → exit immediately

    # If ALL symbols failed:
    log("[HEALTH] ❌ Failed to pull test data for ALL symbols → connection unstable")
    return False


# -------------------------------
# Performance Summary
# -------------------------------
def performance_summary(days=1):
    """
    Placeholder for daily/weekly/monthly performance summaries.
    Later → pull from trade log DB or broker history.
    """
    log(f"[REPORT] Performance summary (last {days} days) not yet implemented.")


# -------------------------------
# Alerts
# -------------------------------
def check_alerts():
    """
    Placeholder for rule-based alerts (e.g., equity DD, high win streak).
    """
    return
