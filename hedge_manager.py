import time
from datetime import datetime, timedelta
from log import log
from config import BOT_SETTINGS
from trade_manager import execute_trade, close_trade
from regime_engine import detect_market_regime
from signal_engine import compute_signal


# ==================================================
# Hedge Manager — Smart Institutional-Style Hedging
# ==================================================
class HedgeManager:
    def __init__(self):
        self.active_hedges = {}  # {symbol: {"lot": 0.5, "expiry": datetime, "direction": "sell"}}

    def should_hedge(self, trade, unrealized_loss, atr_value):
        """
        Decide whether a hedge should be applied.
        - trade: {"symbol": "EURUSDm", "action": "buy", "lot": 0.5, "sl": ..., "tp": ...}
        - unrealized_loss: float (current $ loss of this trade)
        - atr_value: float (ATR of symbol for scaling thresholds)
        """
        threshold = BOT_SETTINGS.get("hedge_loss_threshold_atr", 2.0) * atr_value

        if unrealized_loss < -threshold:
            # Check if hedge already exists
            if trade["symbol"] in self.active_hedges:
                return False

            # Regime check → hedge more in ranging, less in trending
            regime = detect_market_regime(trade["symbol"])
            if regime == "trending":
                log(f"[HEDGE] ❌ Skipping hedge for {trade['symbol']} (trending regime)")
                return False

            return True
        return False

    def place_hedge(self, trade):
        """
        Place a partial hedge (opposite direction).
        """
        hedge_lot = trade["lot"] * BOT_SETTINGS.get("hedge_lot_ratio", 0.5)
        opposite = "sell" if trade["action"] == "buy" else "buy"

        hedge_trade = {
            "symbol": trade["symbol"],
            "action": opposite,
            "lot": hedge_lot,
            "sl": None,
            "tp": None,
        }

        ok = execute_trade(trade["symbol"], hedge_trade)
        if ok:
            expiry_minutes = BOT_SETTINGS.get("hedge_expiry_minutes", 60)
            self.active_hedges[trade["symbol"]] = {
                "lot": hedge_lot,
                "expiry": datetime.utcnow() + timedelta(minutes=expiry_minutes),
                "direction": opposite,
            }
            log(f"[HEDGE] 🔒 Hedge opened on {trade['symbol']} → {opposite} {hedge_lot}")
        else:
            log(f"[HEDGE] ⚠️ Failed to place hedge for {trade['symbol']}")

    def monitor_hedges(self):
        """
        Periodically check active hedges.
        - Close hedge if expired.
        - Close hedge if market stabilizes.
        """
        now = datetime.utcnow()
        expired = []

        for sym, hedge in self.active_hedges.items():
            if now >= hedge["expiry"]:
                close_trade(sym, hedge["direction"], partial=False)
                expired.append(sym)
                log(f"[HEDGE] ⏳ Expired hedge closed for {sym}")
                continue

            # Check market recovery
            signal = compute_signal(sym)
            if signal["action"] != hedge["direction"]:
                # Market is going opposite to hedge → remove hedge
                close_trade(sym, hedge["direction"], partial=False)
                expired.append(sym)
                log(f"[HEDGE] 🔄 Market stabilized, hedge closed for {sym}")

        # Remove closed hedges
        for sym in expired:
            self.active_hedges.pop(sym, None)
