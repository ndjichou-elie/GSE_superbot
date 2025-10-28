# === run_bot.py (with explicit MT5 path init) ===
import MetaTrader5 as mt5
import time
from config import MT5_CREDENTIALS, MT5_PATH, BOT_SETTINGS
from log import log
from strategy_orchestrator import run_strategy

def connect_mt5():
    """Initialize MT5 with explicit path and credentials."""
    log("[BOT] 🚀 Starting GSE_SuperBot trading loop...")

    if not mt5.initialize(
        path=MT5_PATH,
        login=MT5_CREDENTIALS["login"],
        password=MT5_CREDENTIALS["password"],
        server=MT5_CREDENTIALS["server"]
    ):
        log(f"[BOT] ❌ MT5 initialization failed: {mt5.last_error()}")
        return False

    account = mt5.account_info()
    if account is None:
        log("[BOT] ❌ Cannot fetch account info after init")
        return False

    log(f"[BOT] ✅ Connected to MT5 server {account.server} as {account.login}")
    return True


def run_bot():
    if not connect_mt5():
        log("[BOT] ❌ Cannot continue without MT5 connection")
        return

    # Subscribe to all symbols in config
    symbols = BOT_SETTINGS.get("symbols", [])
    for sym in symbols:
        if not mt5.symbol_select(sym, True):
            log(f"[BOT] ⚠️ Failed to subscribe to symbol {sym}")
        else:
            log(f"[BOT] ✅ Subscribed to {sym}")

    # Health check (ping)
    first_symbol = symbols[0] if symbols else None
    if first_symbol:
        tick = mt5.symbol_info_tick(first_symbol)
        if tick:
            log(f"[HEALTH] ✅ {first_symbol} OK: {tick.time_msc % 1000}ms")
        else:
            log(f"[HEALTH] ❌ Failed to pull test data → connection unstable")
            log("[BOT] ❌ Health check failed → pausing for 5 minutes")
            time.sleep(300)
            return

    # Start orchestrator loop
    run_strategy(symbols, interval=BOT_SETTINGS.get("loop_interval", 60))


if __name__ == "__main__":
    run_bot()
