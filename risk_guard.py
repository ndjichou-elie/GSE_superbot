# === risk_guard.py ===
"""
Risk Guard Module
-----------------
Handles equity protection and risk checks before allowing new trades.
"""

import MetaTrader5 as mt5
from config import BOT_SETTINGS
from log import log

# Internal state
_protection_active = False
_equity_peak = None


def check_equity_protection():
    """
    Checks equity drawdown and activates protection mode if needed.
    Returns False if no new trades should be allowed, True otherwise.
    """
    global _protection_active, _equity_peak

    account = mt5.account_info()
    if account is None:
        log("[RISK_GUARD] ❌ Could not fetch account info")
        return False

    equity = account.equity

    # Track peak equity
    if _equity_peak is None or equity > _equity_peak:
        _equity_peak = equity

    # Compute drawdown from peak
    dd_pct = 100 * (_equity_peak - equity) / _equity_peak if _equity_peak else 0

    # Absolute daily drawdown block
    if dd_pct >= BOT_SETTINGS.get("max_daily_drawdown", 20.0):
        log(f"[RISK_GUARD] ❌ Max daily drawdown {dd_pct:.1f}% hit → block all new trades")
        return False

    # Capital protection threshold
    if dd_pct >= BOT_SETTINGS.get("capital_protection_dd", 10.0):
        if not _protection_active:
            _protection_active = True
            log(f"[RISK_GUARD] ⚠️ Capital protection mode activated "
                f"(drawdown {dd_pct:.1f}%) → risk reduced")
    else:
        # Deactivate protection if equity recovers
        if _protection_active and equity > _equity_peak * (1 - BOT_SETTINGS.get("capital_protection_dd", 10.0) / 100):
            _protection_active = False
            log("[RISK_GUARD] ✅ Equity recovered → protection mode off")

    return True


def is_protection_active():
    """
    Returns True if protection mode is active, otherwise False.
    """
    return _protection_active


def check_risk(symbol: str) -> bool:
    """
    Main risk check wrapper.
    Ensures equity protection and per-symbol checks before trade.
    """
    if not check_equity_protection():
        return False

    # (Optional) Here you could add per-symbol risk checks
    log(f"[RISK_GUARD] ✅ Risk check passed for {symbol}")
    return True
