import numpy as np
import MetaTrader5 as mt5
from log import log

# ================================
# Monte Carlo VaR & CVaR
# ================================
def _simulate_returns(symbol, n=1000, horizon=60):
    """
    Simulates price returns using normal distribution.
    - horizon: minutes ahead
    - n: number of Monte Carlo paths
    """
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 500)
    if rates is None or len(rates) < 50:
        log(f"[RISK] ❌ Not enough data to simulate {symbol}")
        return None

    closes = np.array([r['close'] for r in rates])
    returns = np.diff(np.log(closes))

    mu, sigma = np.mean(returns), np.std(returns)

    # Simulate future returns
    sims = np.random.normal(mu, sigma, (n, horizon))
    simulated_paths = sims.cumsum(axis=1)

    # Final simulated returns
    final_returns = simulated_paths[:, -1]
    return final_returns


def var_risk_check(symbol, max_loss=0.01, alpha=0.95):
    """
    Checks if simulated VaR & CVaR are within acceptable risk.
    - max_loss: fraction of account balance (e.g. 0.01 = 1%)
    - alpha: confidence level for VaR (default 95%)
    """
    account = mt5.account_info()
    if account is None:
        log("[RISK] ❌ Could not fetch account info")
        return False

    balance = account.balance
    final_returns = _simulate_returns(symbol)
    if final_returns is None:
        return True  # fallback → allow

    # Sort outcomes
    sorted_returns = np.sort(final_returns)

    # VaR
    var_index = int((1 - alpha) * len(sorted_returns))
    var_value = sorted_returns[var_index]

    # CVaR (expected shortfall: average of worst losses)
    cvar_value = sorted_returns[:var_index].mean()

    # Convert to monetary loss
    potential_loss_var = balance * abs(var_value)
    potential_loss_cvar = balance * abs(cvar_value)

    if potential_loss_var > balance * max_loss:
        log(f"[RISK] 🚫 {symbol} blocked by VaR → {potential_loss_var:.2f} > {max_loss*100:.1f}% balance")
        return False

    if potential_loss_cvar > balance * max_loss * 1.2:  # allow slightly higher CVaR
        log(f"[RISK] 🚫 {symbol} blocked by CVaR → {potential_loss_cvar:.2f} > {max_loss*100:.1f}% balance")
        return False

    log(f"[RISK] ✅ {symbol} risk approved (VaR={potential_loss_var:.2f}, CVaR={potential_loss_cvar:.2f})")
    return True
