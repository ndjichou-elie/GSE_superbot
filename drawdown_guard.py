# === drawdown_guard.py (Step 1 upgraded) ===
from log import log

def monitor_drawdown(initial_balance, current_balance, max_drawdown_percent=10):
    """
    Checks if drawdown exceeds allowed maximum.
    Returns True if drawdown is triggered.
    """
    if initial_balance <= 0:
        return False

    drawdown = ((initial_balance - current_balance) / initial_balance) * 100
    if drawdown >= max_drawdown_percent:
        log(f"[DRAWDOWN] 🚨 Detected: -{drawdown:.2f}% (Limit: {max_drawdown_percent}%)")
        return True
    return False
