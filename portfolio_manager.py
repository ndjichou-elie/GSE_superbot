# === portfolio_manager.py (Phase 15: Portfolio & Multi-Symbol Intelligence) ===
import numpy as np
import sqlite3
from datetime import datetime, timedelta
from log import log
from config import STRATEGY_PARAMS

DB_FILE = "trade_memory.db"

# ================================
# Fetch recent trade history
# ================================
def _fetch_trade_history(days=30):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cutoff = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        SELECT symbol, action, pnl, timestamp
        FROM trades
        WHERE timestamp >= ?
    """, (cutoff,))
    rows = cursor.fetchall()
    conn.close()
    return rows


# ================================
# Correlation matrix
# ================================
def correlation_matrix(symbols, days=30):
    data = {s: [] for s in symbols}
    trades = _fetch_trade_history(days)

    for symbol, action, pnl, ts in trades:
        if symbol in data:
            data[symbol].append(pnl if pnl is not None else 0)

    aligned = []
    for s in symbols:
        if len(data[s]) < 2:
            data[s] = [0, 0]
        aligned.append(data[s][-50:])  # last 50 trades max

    try:
        corr = np.corrcoef(aligned)
        return corr
    except Exception as e:
        log(f"[PORTFOLIO] ⚠️ Correlation calc failed: {e}")
        return None


# ================================
# Symbol performance scoring
# ================================
def score_symbols(symbols, days=30):
    trades = _fetch_trade_history(days)
    scores = {s: 0 for s in symbols}

    for s in symbols:
        pnl = [t[2] for t in trades if t[0] == s and t[2] is not None]
        if pnl:
            mean_pnl = np.mean(pnl)
            volatility = np.std(pnl)
            scores[s] = mean_pnl - volatility  # Sharpe-like score

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    log(f"[PORTFOLIO] 📊 Symbol scores → {ranked}")
    return ranked


# ================================
# Portfolio-level diversification check
# ================================
def diversification_check(open_positions, symbols):
    corr = correlation_matrix(symbols)

    if corr is None:
        return open_positions  # fallback

    flagged = []
    for i, sym1 in enumerate(symbols):
        for j, sym2 in enumerate(symbols):
            if i < j and abs(corr[i, j]) > 0.7:
                pos1 = [p for p in open_positions if p["symbol"] == sym1]
                pos2 = [p for p in open_positions if p["symbol"] == sym2]
                if pos1 and pos2 and pos1[0]["action"] == pos2[0]["action"]:
                    flagged.append(sym2)

    safe_positions = [p for p in open_positions if p["symbol"] not in flagged]

    if flagged:
        log(f"[PORTFOLIO] ⚠️ Diversification reduced exposure → removed {flagged}")

    return safe_positions


# ================================
# Portfolio-level allocation
# ================================
def allocate_portfolio(open_positions, symbols, balance):
    """
    Dynamically allocates capital across symbols.
    """
    ranked = score_symbols(symbols)
    if not ranked:
        return open_positions

    # Total risk cap (e.g., 5% of balance)
    max_portfolio_risk = STRATEGY_PARAMS.get("max_portfolio_risk", 0.05) * balance

    # Allocate risk proportional to score
    total_score = sum([max(0.1, s[1]) for s in ranked])  # avoid division by 0
    allocated = []

    for pos in open_positions:
        score = dict(ranked).get(pos["symbol"], 0.1)
        share = max(0.1, score) / total_score
        allocated_risk = share * max_portfolio_risk

        pos["allocated_risk"] = allocated_risk
        allocated.append(pos)

        log(f"[PORTFOLIO] 💰 Allocated {allocated_risk:.2f} risk to {pos['symbol']} (score={score:.2f})")

    return allocated
