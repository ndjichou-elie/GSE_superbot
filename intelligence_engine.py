# === intelligence_engine.py (Economic Events Intelligence with Detailed Logging) ===
import requests
from datetime import datetime, timedelta
from log import log

# Example API: Forex Factory (JSON calendar feed)
CALENDAR_API_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

CACHE = {"events": [], "last_update": None}


def fetch_calendar():
    """
    Fetch upcoming high-impact economic events (red impact).
    Returns list of dicts with event name, time, and impact.
    """
    global CACHE
    now = datetime.utcnow()

    # Use cached events if updated within last 5 minutes
    if CACHE["last_update"] and (now - CACHE["last_update"]).seconds < 300:
        return CACHE["events"]

    try:
        r = requests.get(CALENDAR_API_URL, timeout=10)
        r.raise_for_status()
        data = r.json()

        events = []
        for e in data:
            if e.get("impact") == "High":  # Only high-impact events
                try:
                    event_time = datetime.strptime(
                        e["date"] + " " + e["time"], "%Y-%m-%d %H:%M"
                    )
                except Exception:
                    continue
                events.append(
                    {"title": e["title"], "time": event_time, "impact": e["impact"]}
                )

        CACHE["events"] = events
        CACHE["last_update"] = now
        return events

    except Exception as ex:
        log(f"[INTEL] ❌ Error fetching calendar: {ex}")
        return []


def check_economic_events(lookahead_minutes=120):
    """
    Block trades if a high-impact event is within lookahead_minutes.
    Returns True if safe, False if blocked.
    Logs the exact reason if blocked.
    """
    events = fetch_calendar()
    if not events:
        log("[INTEL] ✅ No high-impact events detected → safe to trade")
        return True

    now = datetime.utcnow()
    cutoff = now + timedelta(minutes=lookahead_minutes)

    for e in events:
        if now <= e["time"] <= cutoff:
            mins_left = int((e["time"] - now).total_seconds() / 60)
            log(f"[INTEL] 🚫 Blocked: {e['title']} in {mins_left} min (Impact={e['impact']})")
            return False

    log("[INTEL] ✅ No upcoming high-impact events → safe to trade")
    return True
