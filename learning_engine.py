# === learning_engine.py (SQLite Adaptive Learning + Memory) ===
import sqlite3
from log import log
from config import STRATEGY_PARAMS

DB_FILE = "trade_memory.db"


# ================================
# DB Setup for strategy memory
# ================================
def _init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS strategy_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        adjustment TEXT,
        reason TEXT
    )
    """)
    conn.commit()
    conn.close()

# Ensure table exists
_init_db()


# ================================
# Fetch recent trades
# ================================
def _fetch_trades(limit=50):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT action, pnl, confidence
    FROM trades
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    trades = []
    for r in rows:
        trades.append({
            "action": r[0],
            "pnl": r[1] if r[1] is not None else 0,
            "confidence": r[2] if r[2] is not None else 0.5
        })
    return trades


# ================================
# Log an adjustment to memory
# ================================
def _log_adjustment(adjustment, reason):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO strategy_memory (timestamp, adjustment, reason)
    VALUES (datetime('now'), ?, ?)
    """, (adjustment, reason))
    conn.commit()
    conn.close()
    log(f"[LEARNING] 📝 Logged adjustment: {adjustment} → {reason}")


# ================================
# Suggest Adjustments
# ================================
def suggest_adjustments():
    trades = _fetch_trades(limit=50)
    if not trades:
        return {}

    adjustments = {}

    # --- Confidence vs. performance ---
    high_conf_losses = [t for t in trades if t["confidence"] >= 0.8 and t["pnl"] < 0]
    if len(high_conf_losses) >= 3:
        adjustments["atr_multiplier_sl"] = "tighten"
        reason = "High-confidence trades failing"
        _log_adjustment("SL tighten", reason)
        log(f"[LEARNING] ⚠️ {reason} → tightening SL")

    high_conf_wins = [t for t in trades if t["confidence"] >= 0.8 and t["pnl"] > 0]
    if len(high_conf_wins) >= 3:
        adjustments["atr_multiplier_tp"] = "extend"
        reason = "High-confidence trades succeeding"
        _log_adjustment("TP extend", reason)
        log(f"[LEARNING] ✅ {reason} → extending TP")

    # --- Directional bias detection ---
    buy_losses = [t for t in trades if t["action"] == "buy" and t["pnl"] < 0]
    sell_losses = [t for t in trades if t["action"] == "sell" and t["pnl"] < 0]

    if len(buy_losses) >= 5 and len(buy_losses) > len(sell_losses):
        adjustments["avoid_direction"] = "buy"
        reason = "Too many losing BUY trades"
        _log_adjustment("Avoid BUY", reason)
        log(f"[LEARNING] ⛔ {reason} → avoid buys temporarily")

    if len(sell_losses) >= 5 and len(sell_losses) > len(buy_losses):
        adjustments["avoid_direction"] = "sell"
        reason = "Too many losing SELL trades"
        _log_adjustment("Avoid SELL", reason)
        log(f"[LEARNING] ⛔ {reason} → avoid sells temporarily")

    # --- Risk adjustment ---
    avg_pnl = sum([t["pnl"] for t in trades]) / len(trades)
    if avg_pnl < 0:
        STRATEGY_PARAMS["risk_per_trade"] = max(0.005, STRATEGY_PARAMS["risk_per_trade"] - 0.002)
        reason = "Average PnL negative"
        _log_adjustment("Reduce risk", reason)
        log(f"[LEARNING] 📉 {reason} → risk {STRATEGY_PARAMS['risk_per_trade']*100:.2f}%")
    else:
        STRATEGY_PARAMS["risk_per_trade"] = min(0.02, STRATEGY_PARAMS["risk_per_trade"] + 0.002)
        reason = "Average PnL positive"
        _log_adjustment("Increase risk", reason)
        log(f"[LEARNING] 📈 {reason} → risk {STRATEGY_PARAMS['risk_per_trade']*100:.2f}%")

    return adjustments
