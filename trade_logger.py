# === trade_logger.py (SQLite + Confidence Logging) ===
import sqlite3
from datetime import datetime
from log import log

DB_FILE = "trade_memory.db"


# ================================
# DB Setup
# ================================
def _init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        symbol TEXT,
        action TEXT,
        entry_price REAL,
        sl REAL,
        tp REAL,
        exit_price REAL,
        pnl REAL,
        outcome TEXT,
        confidence REAL
    )
    """)
    conn.commit()
    conn.close()


# Ensure table exists
_init_db()


# ================================
# Save Trade (on entry)
# ================================
def log_trade(symbol, action, entry_price, sl, tp, lot=0.1, confidence=0.5):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO trades (timestamp, symbol, action, entry_price, sl, tp, exit_price, pnl, outcome, confidence)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        symbol, action, entry_price, sl, tp,
        None, None, None, confidence
    ))
    conn.commit()
    trade_id = cursor.lastrowid
    conn.close()

    log(f"[TRADE_LOG] {symbol} {action.upper()} entry={entry_price}, SL={sl}, TP={tp}, Lot={lot}, Conf={confidence}")
    return trade_id


# ================================
# Update Trade (on exit)
# ================================
def update_trade(trade_id, exit_price, pnl, outcome):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    UPDATE trades
    SET exit_price=?, pnl=?, outcome=?
    WHERE id=?
    """, (exit_price, pnl, outcome, trade_id))
    conn.commit()
    conn.close()

    log(f"[TRADE_LOG] Updated trade {trade_id} → exit={exit_price}, PnL={pnl}, outcome={outcome}")


# ================================
# Fetch Recent Trades
# ================================
def get_recent_trades(limit=5):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, symbol, action, entry_price, exit_price, pnl, outcome, confidence, timestamp
    FROM trades
    ORDER BY id DESC
    LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    trades = []
    for r in rows:
        trades.append({
            "id": r[0],
            "symbol": r[1],
            "action": r[2],
            "entry_price": r[3],
            "exit_price": r[4],
            "pnl": r[5] if r[5] is not None else 0,
            "outcome": r[6],
            "confidence": r[7],
            "timestamp": r[8]
        })
    return trades


# ================================
# Get Performance Summary
# ================================
def get_performance_summary(limit=500):
    trades = get_recent_trades(limit=limit)
    if not trades:
        return {"total_trades": 0, "win_rate": 0, "avg_pnl": 0, "avg_conf": 0}

    total_trades = len(trades)
    wins = len([t for t in trades if t["pnl"] > 0])
    avg_pnl = sum([t["pnl"] for t in trades]) / total_trades
    avg_conf = sum([t["confidence"] for t in trades if t["confidence"]]) / total_trades

    return {
        "total_trades": total_trades,
        "win_rate": round(wins / total_trades * 100, 2),
        "avg_pnl": round(avg_pnl, 2),
        "avg_conf": round(avg_conf, 2),
    }
