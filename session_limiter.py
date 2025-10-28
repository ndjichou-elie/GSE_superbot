# === session_limiter.py (Final with crypto_always_on + full compatibility) ===
import datetime
import time
from config import BOT_SETTINGS
from log import log

_last_trade_time = {}
_session_trade_count = 0

def within_trading_hours(symbol):
    """Check if current UTC time is within session hours.
       Cryptos can bypass hours if crypto_always_on=True."""
    now = datetime.datetime.utcnow().hour

    # crypto exception
    if BOT_SETTINGS.get("crypto_always_on", False):
        if symbol.upper() in ("BTCUSD", "BTCUSDm", "ETHUSD", "ETHUSDm"):
            return True

    start, end = BOT_SETTINGS["session_hours_utc"]
    return start <= now < end

def within_session():
    """Legacy: check if ANY trading session is open (ignores symbol).
       Used by run_bot.py compatibility."""
    now = datetime.datetime.utcnow().hour
    start, end = BOT_SETTINGS["session_hours_utc"]
    return start <= now < end

def can_trade(symbol, equity=None):
    """Check all session limits and trading rules.
       Returns (ok, reason) so caller can log decisions clearly."""
    global _session_trade_count

    # --- Equity floor ---
    if equity is not None and equity < BOT_SETTINGS["equity_floor"]:
        reason = f"Equity {equity:.2f} below floor {BOT_SETTINGS['equity_floor']}"
        log(f"[SESSION] 🛑 {reason} → block trades.")
        return False, reason

    # --- Trading hours ---
    if not within_trading_hours(symbol):
        reason = "Outside trading hours"
        log(f"[SESSION] {reason}. Sleeping 10 min...")
        return False, reason

    # --- Max trades per session ---
    if _session_trade_count >= BOT_SETTINGS["max_trades_per_session"]:
        reason = "Max trades per session reached"
        log(f"[LIMITER] 🛑 {reason}.")
        return False, reason

    # --- Symbol cooldown ---
    now_t = time.time()
    last_time = _last_trade_time.get(symbol, 0)
    cooldown = BOT_SETTINGS["symbol_cooldown_minutes"] * 60
    if now_t - last_time < cooldown:
        remaining = (cooldown - (now_t - last_time)) / 60
        reason = f"{symbol} in cooldown ({remaining:.1f}m left)"
        log(f"[LIMITER] 🛑 {reason}.")
        return False, reason

    # ✅ Passed all checks
    reason = "ok"
    log(f"[LIMITER] ✅ {symbol} passed all session checks.")
    return True, reason

def register_trade(symbol):
    """Record a trade event."""
    global _session_trade_count
    _last_trade_time[symbol] = time.time()
    _session_trade_count += 1
    log(f"[LIMITER] ✅ Trade registered for {symbol}. Session trades: {_session_trade_count}")

# --- Backward compatibility for run_bot.py ---
record_trade = register_trade
