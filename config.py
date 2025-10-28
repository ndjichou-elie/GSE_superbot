# === config.py ===
# Keep your credentials here. Do NOT redefine MT5_CREDENTIALS later in this file.
MT5_CREDENTIALS = {
    "login": 222908638,            # <-- your login
    "password": "24680@Ee",        # <-- your password
    "server": "Exness-MT5Real30",  # <-- exact server name
}

# If later you want to force using env variables instead, set this True
USE_ENV_CREDS = False

# --- Bot / risk / exec settings ---
BOT_SETTINGS = {
    "default_risk_percent": 1.0,
    "max_risk_percent": 1.0,
    "max_daily_drawdown": 20.0,
    "max_daily_loss_trades": 3,

    "session_hours_utc": [0, 24],
    "crypto_always_on": True,
    "cooldown_minutes_after_dd": 30,

    "max_trades_per_session": 15,
    "min_minutes_between_trades": 5,
    "symbol_cooldown_minutes": 10,

    "min_lot": 0.01,          # safer for BTC tests
    "max_lot": 5.0,

    "max_spread_pct_of_atr": 0.60,

    "symbols": ["BTCUSDm"],   # use your broker’s exact name
    "timeframe": "M5",
}
# Force the connector to ATTACH to an already-open terminal (recommended for your setup)
FORCE_ATTACH = True

STRATEGY_PARAMS = {
    "ema_fast": 20,
    "ema_slow": 50,
    "rsi_period": 14,
    "adx_period": 14,
    "atr_period": 14,
    "tp_atr_mult": 2.0,
    "sl_atr_mult": 1.2,
    "risk_per_trade": BOT_SETTINGS["default_risk_percent"],
    "htf_timeframe": "H1",
}
