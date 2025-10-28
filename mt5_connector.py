# === mt5_connector.py (attach-first; attach-only if FORCE_ATTACH=True) ===
from __future__ import annotations

import os
import time
import glob
from typing import Iterable, Optional, Dict, Any

import MetaTrader5 as mt5
import pandas as pd

from log import log
from config import MT5_CREDENTIALS, BOT_SETTINGS, USE_ENV_CREDS, FORCE_ATTACH


# -------------------------------
# Credential handling
# -------------------------------
def _get_login_creds() -> Dict[str, Any]:
    if USE_ENV_CREDS:
        env_login = os.getenv("MT5_LOGIN")
        env_pass  = os.getenv("MT5_PASSWORD")
        env_serv  = os.getenv("MT5_SERVER")
        if env_login and env_pass and env_serv:
            try:
                login = int(env_login)
            except Exception:
                login = 0
            return {"login": login, "password": env_pass, "server": env_serv}
    # default to config.py values
    return {
        "login": int(MT5_CREDENTIALS.get("login", 0) or 0),
        "password": MT5_CREDENTIALS.get("password", "") or "",
        "server": MT5_CREDENTIALS.get("server", "") or "",
    }


# -------------------------------
# Path discovery (used only if not FORCE_ATTACH)
# -------------------------------
def _normalize_terminal_path(p: str) -> str:
    if not p:
        return ""
    p = p.strip().strip('"')
    if os.path.isdir(p):
        p = os.path.join(p, "terminal64.exe")
    return p

def _candidate_terminal_paths() -> list[str]:
    candidates: list[str] = []
    env_path = _normalize_terminal_path(os.getenv("MT5_TERMINAL_PATH") or "")
    if env_path and os.path.isfile(env_path):
        candidates.append(env_path)
    guesses = [
        r"C:\Program Files\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\MetaQuotes\MetaTrader 5\terminal64.exe",
        r"C:\Program Files\Exness\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\MetaQuotes\MetaTrader 5\terminal64.exe",
        r"C:\Program Files (x86)\Exness\MetaTrader 5\terminal64.exe",
    ]
    for g in guesses:
        if os.path.isfile(g):
            candidates.append(g)
    roaming = os.path.expanduser(r"~\AppData\Roaming\MetaQuotes\Terminal")
    if os.path.isdir(roaming):
        for exe in glob.glob(os.path.join(roaming, "*", "terminal64.exe")):
            candidates.append(exe)
    for exe in glob.glob(r"C:\Program Files\**\terminal64.exe", recursive=True)[:10]:
        candidates.append(exe)
    # dedupe
    seen = set(); ordered = []
    for p in candidates:
        if p not in seen:
            ordered.append(p); seen.add(p)
    return ordered


# -------------------------------
# Connection management
# -------------------------------
def _attach_only(retries: int = 6, sleep_sec: float = 2.0) -> bool:
    """Attach to an already-open terminal; do NOT try launching a new one."""
    # close any previous session
    try:
        mt5.shutdown()
    except Exception:
        pass

    for attempt in range(1, retries + 1):
        log(f"[MT5] Trying ATTACH (attempt {attempt}/{retries})…")
        ok = mt5.initialize()
        if ok:
            ai = mt5.account_info(); ti = mt5.terminal_info()
            if ai and ti and getattr(ti, "connected", False):
                log(f"[MT5] ✅ Attached | Login={ai.login} | Balance={ai.balance:.2f}")
                try:
                    subscribe_symbols(BOT_SETTINGS.get("symbols", []) or [])
                except Exception as e:
                    log(f"[MT5] ⚠️ subscribe_symbols failed (non-fatal): {e}")
                return True
            else:
                log("[MT5] ⚠️ Attached but not connected; retrying…")
        else:
            log(f"[MT5] ❌ attach init failed: {mt5.last_error()}")
        # gentle backoff
        time.sleep(sleep_sec)
        try:
            mt5.shutdown()
        except Exception:
            pass
    return False


def connect(retries: int = 6, sleep_sec: float = 3.0) -> bool:
    """
    If FORCE_ATTACH=True: only try attaching to an already-open terminal.
    Otherwise: attach first; then try portable and normal across candidate paths.
    """
    if FORCE_ATTACH:
        log("[MT5] FORCE_ATTACH=True → will only attach to an already-open terminal.")
        ok = _attach_only(retries=retries, sleep_sec=sleep_sec)
        if not ok:
            log("[MT5] ❌ Attach mode failed. Open your MT5 desktop, log in (green icon), then run the bot again.")
        return ok

    # Otherwise: try attach, then launches (portable → normal)
    if _attach_only(retries=2, sleep_sec=1.5):
        return True

    creds = _get_login_creds()
    paths = _candidate_terminal_paths()
    if not paths:
        log("[MT5] ❌ No terminal64.exe candidates found. Set MT5_TERMINAL_PATH.")
        return False

    log(f"[MT5] 🔎 Candidate terminal paths to try ({len(paths)}):")
    for p in paths[:5]:
        log(f"       • {p}")
    if len(paths) > 5:
        log("       • … (more candidates truncated)")

    # 1) portable
    for path in paths:
        for attempt in range(1, retries + 1):
            try: mt5.shutdown()
            except Exception: pass
            log(f"[MT5] Initializing portable path='{path}' (attempt {attempt}/{retries})…")
            ok = mt5.initialize(path=path, portable=True,
                                login=creds["login"], password=creds["password"], server=creds["server"])
            if ok:
                ai = mt5.account_info(); ti = mt5.terminal_info()
                if ai and ti and getattr(ti, "connected", False):
                    log(f"[MT5] ✅ Connected (portable) | Login={ai.login} | Balance={ai.balance:.2f}")
                    try: subscribe_symbols(BOT_SETTINGS.get("symbols", []) or [])
                    except Exception as e: log(f"[MT5] ⚠️ subscribe_symbols failed (non-fatal): {e}")
                    return True
                log("[MT5] ⚠️ portable=True initialized but not connected; retrying…")
            else:
                log(f"[MT5] ❌ portable init failed: {mt5.last_error()}")
            time.sleep(sleep_sec)
        log("[MT5] ⏭️ Giving up on this path (portable); will try normal…")

    # 2) normal
    for path in paths:
        for attempt in range(1, retries + 1):
            try: mt5.shutdown()
            except Exception: pass
            log(f"[MT5] Initializing path='{path}' (attempt {attempt}/{retries})…")
            ok = mt5.initialize(path=path,
                                login=creds["login"], password=creds["password"], server=creds["server"])
            if ok:
                ai = mt5.account_info(); ti = mt5.terminal_info()
                if ai and ti and getattr(ti, "connected", False):
                    log(f"[MT5] ✅ Connected | Login={ai.login} | Balance={ai.balance:.2f}")
                    try: subscribe_symbols(BOT_SETTINGS.get("symbols", []) or [])
                    except Exception as e: log(f"[MT5] ⚠️ subscribe_symbols failed (non-fatal): {e}")
                    return True
                log("[MT5] ⚠️ init=True but not connected; retrying…")
            else:
                log(f"[MT5] ❌ init failed: {mt5.last_error()}")
            time.sleep(sleep_sec)

    log("[MT5] ❌ All connection strategies exhausted.")
    return False


# -------------------------------
# Shutdown & health
# -------------------------------
def shutdown() -> None:
    try:
        mt5.shutdown()
        log("[MT5] Shutdown complete.")
    except Exception:
        pass

def is_connected() -> bool:
    ti = mt5.terminal_info()
    ai = mt5.account_info()
    return bool(ti and ai and getattr(ti, "connected", False))


# -------------------------------
# Symbols
# -------------------------------
def _ensure_symbol_visible(symbol: str) -> bool:
    info = mt5.symbol_info(symbol)
    if info and info.visible:
        return True
    ok = mt5.symbol_select(symbol, True)
    if not ok:
        log(f"[MT5] ❌ Could not select symbol {symbol}")
    return bool(ok)

def subscribe_symbols(symbols: Iterable[str]) -> None:
    for s in symbols:
        ok = _ensure_symbol_visible(s)
        log(f"[MT5] {'✅' if ok else '❌'} Subscribed to {s}")


# -------------------------------
# Timeframe & data
# -------------------------------
_TF_MAP = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4, "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1,
}
def to_mt5_timeframe(tf_str: str):
    return _TF_MAP.get(str(tf_str).upper(), mt5.TIMEFRAME_M5)

def get_rates(symbol: str, timeframe_str: str = "M5", lookback: int = 300) -> Optional[pd.DataFrame]:
    tf = to_mt5_timeframe(timeframe_str)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, int(lookback))
    if rates is None or len(rates) == 0:
        log(f"[MT5] ❌ No data for {symbol} ({timeframe_str})")
        return None
    df = pd.DataFrame(rates)
    if "time" in df.columns:
        df["time"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_convert(None)
    for c in ("open", "high", "low", "close"):
        if c in df.columns:
            df[c] = df[c].astype(float)
    return df

def get_tick(symbol: str):
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        log(f"[MT5] ❌ No tick for {symbol}")
        return None
    return tick

def get_symbol_info(symbol: str):
    info = mt5.symbol_info(symbol)
    if info is None:
        log(f"[MT5] ❌ No symbol info for {symbol}")
        return None
    return info


# -------------------------------
# Self-heal
# -------------------------------
def reconnect_if_needed(retries: int = 3, sleep_sec: float = 2.0) -> bool:
    if is_connected():
        return True
    log("[MT5] 🔁 Attempting reconnection…")
    return connect(retries=retries, sleep_sec=sleep_sec)
