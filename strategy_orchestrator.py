# === strategy_orchestrator.py ===
import time
from log import log
from config import BOT_SETTINGS
from mt5_connector import get_rates, is_connected
from position_sizer import compute_lot
from signal_engine import generate_signal
from exit_engine import check_exit
from trade_manager import execute_order, get_open_positions
from regime_engine import detect_regime, adjust_sl_tp
from volatility_engine import spread_ok
from intelligence_engine import check_economic_events  # macro events gate
from session_limiter import can_trade, register_trade

SYMBOLS = BOT_SETTINGS["symbols"]
SLEEP_SECS = 60

def _is_crypto_symbol(symbol: str) -> bool:
    s = symbol.upper()
    return any(x in s for x in ("BTC", "ETH", "XAUUSDCRYPTO?"))  # keep simple

def _should_check_macro(symbols) -> bool:
    """Only run the macro-events gate if there are non-crypto symbols."""
    return not all(_is_crypto_symbol(s) for s in symbols)

def run_strategy(symbols=None, interval=SLEEP_SECS):
    symbols = symbols or SYMBOLS
    log("[ORCHESTRATOR] 🚀 Starting strategy (LIVE MODE)")
    log(f"[ORCHESTRATOR] Universe: {symbols} | TF: {BOT_SETTINGS['timeframe']}")

    while True:
        try:
            # Connectivity guard
            if not is_connected():
                log("[ORCHESTRATOR] ❌ MT5 not connected. Retrying in 5s...")
                time.sleep(5)
                continue

            # Macro events gate (skip for all-crypto universes like BTC-only)
            if _should_check_macro(symbols):
                if not check_economic_events():
                    time.sleep(interval)
                    continue

            # Process each symbol (single symbol = BTC)
            for symbol in symbols:
                # Session / throttles
                if not can_trade(symbol):
                    continue

                # Fetch fresh market data
                df = get_rates(symbol, BOT_SETTINGS["timeframe"], lookback=300)
                if df is None or len(df) < 100:
                    log(f"[ORCHESTRATOR] ⏭️ Skipping {symbol} (no/short data)")
                    continue

                # Optional exit checks for open positions
                open_positions = get_open_positions(symbol)
                if open_positions:
                    try:
                        check_exit(symbol, df, open_positions)
                    except Exception as e:
                        log(f"[EXIT] ⚠️ error while checking exits: {e}")

                # Entry decision
                signal = generate_signal(symbol, df)
                if signal is None:
                    # log very lightly to avoid spam
                    continue

                direction = signal["direction"]  # "BUY" or "SELL"
                sl_price = signal["sl"]
                tp_price = signal["tp"]

                # Regime-aware SL/TP (single application!)
                regime = detect_regime(df)
                sl_price, tp_price = adjust_sl_tp(df, sl_price, tp_price, regime)

                # Spread sanity for crypto
                if not spread_ok(symbol, df):
                    # Avoid churning logs on tiny timeframes
                    continue

                # Position size
                lot = compute_lot(symbol, df, direction)
                if lot is None or lot <= 0:
                    continue

                # Execute
                ok, ticket = execute_order(symbol, direction, lot, sl_price, tp_price)
                if ok:
                    register_trade(symbol)
                    log(f"[ORCHESTRATOR] ✅ {direction} {symbol} lot={lot} sl={sl_price} tp={tp_price} ticket={ticket}")

            # With single-symbol BTC, skip diversification/pruning noise

            time.sleep(interval)

        except KeyboardInterrupt:
            log("[ORCHESTRATOR] 🛑 Stopped by user.")
            break
        except Exception as e:
            log(f"[ORCHESTRATOR] ❗ Unexpected error: {e}")
            time.sleep(3)
