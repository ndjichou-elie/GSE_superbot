# === backtester.py (MT5 Integrated Backtester, Safe Version) ===
import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import BOT_SETTINGS, MT5_CREDENTIALS
from log import log

class Backtester:
    def __init__(self, symbol="BTCUSDm", timeframe=mt5.TIMEFRAME_M15, start_days=30):
        self.symbol = symbol
        self.timeframe = timeframe
        self.start_days = start_days
        self.results = []

    def connect(self):
        """Ensure MT5 is connected before backtest. Do not reinitialize (main bot handles init)."""
        if not mt5.initialize():
            log(f"[Backtester] ⚠️ MT5 not re-initialized (already handled in run_bot)")
        account = mt5.account_info()
        if account is None:
            raise RuntimeError("MT5 not connected. Cannot run backtest.")
        log(f"[Backtester] ✅ Connected to MT5 for {self.symbol}")

    def fetch_data(self):
        """Pull historical data from MT5 safely."""
        utc_from = datetime.utcnow() - timedelta(days=self.start_days)
        utc_to = datetime.utcnow()
        rates = mt5.copy_rates_range(self.symbol, self.timeframe, utc_from, utc_to)
        if rates is None or len(rates) == 0:
            log(f"[Backtester] ❌ No historical data for {self.symbol}")
            return None   # skip if no history
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df

    def run(self):
        """Run backtest on historical data (simplified)."""
        self.connect()
        df = self.fetch_data()
        if df is None:
            return None  # gracefully skip

        equity = 10000.0
        risk_perc = BOT_SETTINGS["default_risk_percent"] / 100.0

        for i in range(100, len(df)):  # start after enough bars
            candle = df.iloc[:i].copy()
            price = df.iloc[i]["close"]

            # Simple pseudo-signal for backtest (random example logic)
            if price > candle["close"].mean():
                sig_type = "buy"
            elif price < candle["close"].mean():
                sig_type = "sell"
            else:
                continue

            atr = candle["close"].rolling(14).std().iloc[-1]  # quick ATR proxy
            sl = price - atr * BOT_SETTINGS["sl_atr_mult"] if sig_type == "buy" else price + atr * BOT_SETTINGS["sl_atr_mult"]
            tp = price + atr * BOT_SETTINGS["tp_atr_mult"] if sig_type == "buy" else price - atr * BOT_SETTINGS["tp_atr_mult"]

            lot = (equity * risk_perc) / (atr * 10)  # simplified lot sizing

            # fake outcome: assume next X bars determine SL/TP hit
            future = df.iloc[i:i+10]
            hit_sl = any((future["low"] <= sl) if sig_type == "buy" else (future["high"] >= sl))
            hit_tp = any((future["high"] >= tp) if sig_type == "buy" else (future["low"] <= tp))

            result = 0
            if hit_tp and not hit_sl:
                result = atr * BOT_SETTINGS["tp_atr_mult"] * lot
                equity += result
            elif hit_sl and not hit_tp:
                result = -atr * BOT_SETTINGS["sl_atr_mult"] * lot
                equity += result

            self.results.append({
                "time": df.iloc[i]["time"],
                "signal": sig_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "result": result,
                "equity": equity
            })

        return pd.DataFrame(self.results)

    def summary(self):
        if not self.results:
            return {}
        df = pd.DataFrame(self.results)
        total = df["result"].sum()
        wins = (df["result"] > 0).sum()
        losses = (df["result"] < 0).sum()
        winrate = wins / max(1, (wins + losses)) * 100
        max_dd = (df["equity"].cummax() - df["equity"]).max()
        return {
            "total_profit": round(total, 2),
            "win_rate": round(winrate, 2),
            "trades": len(df),
            "max_drawdown": round(max_dd, 2),
            "final_equity": round(df["equity"].iloc[-1], 2),
        }


# === Helper function for RL/Orchestrator ===
def run_backtest(symbol, days=30):
    bt = Backtester(symbol=symbol, timeframe=mt5.TIMEFRAME_M15, start_days=days)
    results = bt.run()
    if results is None:
        return None
    return bt.summary()
