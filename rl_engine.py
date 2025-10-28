# === rl_engine.py (Reinforcement Learning Optimizer for Strategy Params) ===
import random
from backtester import run_backtest
from log import log
from config import BOT_SETTINGS, STRATEGY_PARAMS


class RLEngine:
    def __init__(self, symbol="EURUSDm", lookback_days=30, trials=5):
        self.symbol = symbol
        self.lookback_days = lookback_days
        self.trials = trials
        self.best_params = STRATEGY_PARAMS.copy()

    def run_trials(self):
        log(f"[RL] 🧠 Running {self.trials} trials for {self.symbol} on {self.lookback_days} days")

        best_score = -9999
        best_params = None

        for t in range(self.trials):
            # Randomize some key strategy params within safe ranges
            test_params = {
                "sl_atr_mult": round(random.uniform(0.8, 2.5), 2),
                "tp_atr_mult": round(random.uniform(1.2, 3.5), 2),
                "rsi_buy_min": random.randint(45, 60),
                "rsi_sell_max": random.randint(40, 55),
                "adx_min": random.randint(15, 30),
            }

            # Temporarily override global strategy settings
            for k, v in test_params.items():
                STRATEGY_PARAMS[k] = v

            # Run backtest
            summary = run_backtest(self.symbol, self.lookback_days)
            if not summary:
                continue

            # Composite score: profit - penalty for drawdown + bonus for win rate
            score = (
                summary["total_profit"]
                - (summary["max_drawdown"] * 2)
                + (summary["win_rate"] * 5)
            )

            log(f"[RL] Trial {t+1}/{self.trials} {test_params} → "
                f"Profit={summary['total_profit']}, WinRate={summary['win_rate']}%, "
                f"DD={summary['max_drawdown']} → Score={score:.2f}")

            if score > best_score:
                best_score = score
                best_params = test_params

        if best_params:
            self.best_params = best_params
            log(f"[RL] ✅ Best params for {self.symbol}: {best_params} (Score {best_score:.2f})")
        else:
            log("[RL] ❌ No valid params found")

        return best_params

    def update_live_strategy(self):
        if not self.best_params:
            return

        for k, v in self.best_params.items():
            STRATEGY_PARAMS[k] = v
        log(f"[RL] 🔄 Live strategy updated with RL params: {self.best_params}")
