# GSE_superbot
**Autonomous Crypto Trading & Risk Management Assistant for MetaTrader 5**
> GSE_superbot is an advanced, modular trading engine designed to analyze the crypto
market (with a primary focus on BTCUSD), generate trading signals, manage open positions,
and protect capital ? automatically, 24/7.
? **Important:**
This project is for research and educational purposes. It does **not** guarantee profit,
and it comes with real financial risk. You are fully responsible for how you run it.
---
## ? Table of Contents
1. [What is GSE_superbot?](#-what-is-gse_superbot)
2. [Key Features](#-key-features)
3. [High-Level Architecture](#-high-level-architecture)
4. [Project Structure](#-project-structure)
5. [How the Trading Loop Works](#-how-the-trading-loop-works)
6. [Installation & Setup](#-installation--setup)
7. [Configuration](#-configuration)
8. [Safety & Risk Management](#-safety--risk-management)
9. [Roadmap / Next Steps](#-roadmap--next-steps)
10. [License](#-license)
11. [Author](#-author)
---
## ? What is GSE_superbot?
GSE_superbot is an AI-assisted trading system built to behave like a disciplined
professional trader:
- It watches the market (price action, volatility, trend strength, volume, sentiment).
- It decides if a setup is high quality.
- It sizes the position based on risk.
- It opens and manages the trade in MetaTrader 5.
- It protects the account using global risk rules.
The bot is built to run with **very small accounts** as well as to scale.
Main target pair for now: **BTCUSD** (crypto CFD / synthetic BTC pair in MT5).
---
## ? Key Features
### 1. Multi-layer Signal Engine
- EMA structure / trend direction (fast vs slow EMA cross, multi-timeframe).
- RSI for momentum exhaustion / overbought-oversold confirmation.
- ADX to check trend strength (filter out weak chop).
- ATR to measure volatility and set dynamic stops.
- Volume breakout filter to avoid fake/no-liquidity signals.
- Optional news/sentiment filter to block trading during high-risk sentiment events.
> Goal: Only take trades when *trend + momentum + volatility + volume* all agree.
---
### 2. Risk Guard (Capital Protection)
- Max % risk per trade (position size automatically calculated).
- Dynamic stop loss based on ATR and structure.
- Daily max loss limit ? shuts down trading after too much drawdown in one day.
- Daily profit lock ? if you hit target profit for the day, bot can stop trading and
?protect the win.?
- Max concurrent open trades.
- Emergency kill switch on abnormal volatility.
> Goal: Survive first. Profit second.
---
### 3. Trade Manager
- Opens trades via MT5.
- Places stop loss (SL) and take profit (TP) automatically.
- Moves SL to break-even after price moves in your favor.
- Partial take-profit logic (e.g. close 50% at TP1, let the rest trail).
- Trailing stop based on ATR.
- Closes trades if the setup becomes invalid.
> Goal: Trade like a disciplined human, with zero emotions.
---
### 4. Advisor Engine (Market Intelligence Layer)
- Pulls market context (trend bias, volatility regime, sentiment).
- Can integrate financial news headlines + sentiment model (FinBERT-style sentiment
scoring of BTC-related headlines).
- Produces a short ?human-readable? summary like:
 - ?Market is bullish but overheated. Avoid new longs until pullback near 15m 50EMA.?
> Goal: Understand *why* you’re in a trade, not just enter blindly.
---
### 5. Modular + Extensible
- Each core responsibility lives in its own Python module.
- Easy to replace a strategy, model, or broker without rewriting the whole bot.
- Can run in **live mode** (real account) or **paper/backtest mode** (no live orders).
---
## ? High-Level Architecture
**Core modules (planned / implemented):**
| File / Module | Responsibility |
|---------------------------|----------------|
| ‘signal_engine.py‘ | Scans market data, builds long/short/no-trade signal using
indicators and sentiment filters. |
| ‘position_sizer.py‘ | Calculates lot size based on account balance, % risk, and
ATR distance to stop. |
| ‘trade_manager.py‘ | Sends orders to MT5, updates SL/TP, applies partial take
profits, trailing stops. |
| ‘risk_guard.py‘ | Enforces global safety rules (max daily loss, max open
trades, etc.) and can shut the bot down. |
| ‘advisor_engine.py‘ | Generates human-style market commentary and bias for
dashboard / logs. |
| ‘config.py‘ / ‘settings.yaml‘ | Central configuration (risk %, symbols, broker login,
feature toggles). |
| ‘main.py‘ | Orchestrates the loop: fetch data ? generate signal ? pass
risk checks ? execute / manage trades. |
| ‘utils/‘ | Helpers like logging, MT5 connection wrappers, time utils,
math helpers, etc. |
---
## ? Project Structure
This is the expected layout of the repository:
‘‘‘text
GSE_superbot/
?
?? main.py
?? config.py # or /config/settings.yaml
?? requirements.txt
?
?? signal_engine.py
?? risk_guard.py
?? advisor_engine.py
?? trade_manager.py
?? position_sizer.py
?
?? utils/
? ?? mt5_client.py # connect to MetaTrader5 terminal, get candles, send orders
? ?? indicators.py # EMA, RSI, ATR, ADX, volume analysis
? ?? sentiment.py # optional sentiment scoring / news filter
? ?? logger.py # structured logging, PnL tracking
? ?? time_utils.py
?
?? backtests/
? ?? backtest_runner.py # run historical simulations
? ?? sample_results.md
?
?? logs/
 ?? trades.log
 ?? daily_risk.log
‘‘‘
If your actual folder names differ, update the tree above so the README matches the repo.
---
## ? How the Trading Loop Works
**Step 1. Get fresh market data**
- Pulls recent candles (ex: M5, M15, H1) for ‘BTCUSD‘ from MetaTrader 5.
- Computes indicators (EMA, RSI, ADX, ATR, volume).
**Step 2. Build a trade idea**
- ‘signal_engine‘ decides:
 - ‘LONG‘, ‘SHORT‘, or ‘FLAT‘ (no trade).
 - Suggested stop loss level (based on ATR + structure).
 - Suggested first take profit and optional second take profit.
**Step 3. Check global safety**
- ‘risk_guard‘ validates:
 - Have we already hit max daily drawdown?
 - Are we already in too many trades?
 - Is volatility insanely high (potential news spike)?
 - Has daily profit target been reached (lock in the win)?
If anything fails ? the bot skips this trade.
**Step 4. Size the trade**
- ‘position_sizer‘ calculates lot size so that:
 - If SL is hit, the loss is e.g. 1% (configurable) of account balance.
**Step 5. Execute and manage**
- ‘trade_manager‘ opens the order in MT5 with SL & TP.
- Monitors open position:
 - Moves SL to break-even after TP1.
 - Starts trailing if trade keeps running.
 - Force-closes if signal flips the other way or risk_guard says ?exit now.?
**Step 6. Log everything**
- Every decision is logged so you can audit later:
 - Why we entered.
 - Where the stop was.
 - How much we risked.
 - PnL impact.
---
## ? Installation & Setup
### 1. Requirements
- **Python 3.10+**
- **MetaTrader 5** installed on the same machine and logged in to your broker (for
example, an account that supports BTCUSD).
- A Windows environment is usually easiest because MT5 is native on Windows.
- Basic Python environment (virtualenv or venv).
### 2. Clone the repo
‘‘‘bash
git clone https://github.com/ndjichou-elie/GSE_superbot.git
cd GSE_superbot
‘‘‘
### 3. Create & activate a virtual environment
**Windows (PowerShell):**
‘‘‘bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
‘‘‘
**Linux / WSL:**
‘‘‘bash
python3 -m venv .venv
source .venv/bin/activate
‘‘‘
### 4. Install dependencies
‘‘‘bash
pip install -r requirements.txt
‘‘‘
Typical libraries include:
- ‘MetaTrader5‘ (Python MT5 bridge)
- ‘pandas‘, ‘numpy‘
- ‘scikit-learn‘
- ‘torch‘, ‘transformers‘ (for sentiment model if enabled)
- ‘requests‘, ‘pytz‘, etc.
(If some of these aren?t in your ‘requirements.txt‘ yet, add them.)
### 5. Configure the bot
Update either ‘config.py‘ or ‘config/settings.yaml‘ with:
- Your trading symbol (e.g. ‘"BTCUSD"‘).
- Risk per trade (ex: ‘RISK_PERCENT = 1.0‘).
- Daily max loss.
- Daily profit lock.
- Whether sentiment/news filter is active or not.
- Path / login info for MT5 if needed.
Example (YAML style):
‘‘‘yaml
symbol: "BTCUSD"
risk:
 max_risk_percent_per_trade: 1.0
 max_daily_loss_percent: 5.0
 lock_trading_after_profit_percent: 3.0
trade_management:
 tp1_rr: 1.5 # take partial profit at 1.5R
 tp2_trailing: true # trail the rest with ATR
sentiment_filter:
 enabled: true
 min_score: 0.2 # block longs if sentiment is too negative
‘‘‘
### 6. Run
‘‘‘bash
python main.py --mode live
‘‘‘
or for safe testing / paper mode:
‘‘‘bash
python main.py --mode backtest --from 2025-01-01 --to 2025-02-01
‘‘‘
(Adjust the date range to whatever your backtest runner supports.)
---
## ? Safety & Risk Management
This bot tries to behave like a disciplined trader, but nothing is 100% safe:
- **Leverage kills accounts fast.** Small accounts are at even higher risk.
- Crypto trades 24/7. Gaps and violent spikes can skip your stop.
- News events can invalidate any technical setup in seconds.
- Past performance in backtests does not guarantee future performance.
By using this code:
- You accept full responsibility for all financial outcomes.
- You agree that this code is provided ?as is,? without any warranty.
- You agree this is **not financial advice**. It is a technical automation project.
---
## ? Roadmap / Next Steps
Planned / in-progress improvements:
1. **Dashboard / Monitoring UI**
 - Web dashboard to see open trades, PnL, daily risk status, and advisor summary.
2. **Smarter Sentiment Layer**
 - Real-time crypto news feed scoring.
 - Block trades during panic / FUD spikes.
3. **Strategy Library**
 - Multiple signal profiles (scalping / swing / breakout).
 - Per-symbol configuration so the bot can handle multiple markets.
4. **Self-Evaluation / Learning**
 - Daily report: which trades were winners vs losers and why.
 - Auto-disable a strategy if it?s performing badly.
5. **Full Multi-Symbol Mode**
 - Trade multiple pairs at the same time with independent risk buckets.
 - Avoid correlation traps (not opening 3 trades that are basically the same bet).
---
## ? License
This project is currently unlicensed / private research code.
If you plan to open source it, you can add a standard license such as MIT, Apache-2.0, or
GPL-3.0 here.
Example MIT snippet (optional if you choose MIT later):
‘‘‘text
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions...
‘‘‘
---
## ? Author
**NDJICHOU ELIE**
- Designer of the trading logic, risk rules, and automation flow.
- Vision: a 24/7 intelligent assistant that manages the market like a disciplined,
unemotional trader.
If you use this project, credit the author. 
