# === advisor_engine.py (Advanced with News Calendar + Sentiment Trend) ===
from log import log
from config import BOT_SETTINGS, PORTFOLIO_SETTINGS
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
import xml.etree.ElementTree as ET, socket, datetime
from transformers import pipeline

# === Setup sentiment model (FinBERT / HuggingFace) ===
sentiment_model = pipeline("sentiment-analysis", model="ProsusAI/finbert")

# === RSS feeds ===
REUTERS_FEEDS = [
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/marketsNews",
]
BLOOMBERG_FEEDS = [
    "https://www.bloomberg.com/feeds/podcasts/etf-report.xml",
]

# === Internal cache ===
sentiment_history = []

# === News utils ===
def _fetch_url_text(url, timeout=8):
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0 GSE-SuperBot"})
        with urlopen(req, timeout=timeout) as r:
            data = r.read()
        return data.decode("utf-8", errors="replace")
    except (HTTPError, URLError, socket.timeout) as e:
        log(f"[ADVISOR][HTTP] ⚠️ {url} | {e}")
        return None
    except Exception as e:
        log(f"[ADVISOR][HTTP] ⚠️ {url} | {e}")
        return None

def _parse_rss_titles(xml_text, max_items=5):
    titles = []
    try:
        root = ET.fromstring(xml_text)
        for node in root.findall(".//channel/item/title"):
            if node.text: titles.append(node.text.strip())
        if not titles:
            for entry in root.findall(".//{*}entry/{*}title"):
                if entry.text: titles.append(entry.text.strip())
    except ET.ParseError:
        pass
    return titles[:max_items]

def _fetch_feed_headlines(feed_urls, per_feed=3, overall_cap=6):
    agg = []
    for url in feed_urls:
        xml_text = _fetch_url_text(url)
        if not xml_text: continue
        agg.extend(_parse_rss_titles(xml_text, max_items=per_feed))
        if len(agg) >= overall_cap: break
    return list(dict.fromkeys(agg))[:overall_cap]

# === IMF Fallback ===
def fetch_imf_context():
    return {
        "global_growth": "3.0%",
        "inflation": "Cooling but above target",
        "comment": "Downside risks: geopolitics, Fed policy, energy"
    }

# === Calendar filter (stub, can connect to real API) ===
def fetch_calendar_events():
    # Later: integrate TradingEconomics API / Investing.com API
    now = datetime.datetime.utcnow()
    # Example: block around US CPI release
    events = [
        {"time": now.replace(hour=12, minute=30), "impact": "high", "event": "US CPI"},
    ]
    return events

def calendar_blocks_trading():
    now = datetime.datetime.utcnow()
    before = PORTFOLIO_SETTINGS["news_block_minutes_before"]
    after = PORTFOLIO_SETTINGS["news_block_minutes_after"]

    for ev in fetch_calendar_events():
        if ev["impact"] != "high": 
            continue
        start = ev["time"] - datetime.timedelta(minutes=before)
        end = ev["time"] + datetime.timedelta(minutes=after)
        if start <= now <= end:
            log(f"[ADVISOR] ⏸ Blocked by news event: {ev['event']} ({ev['time']})")
            return True
    return False

# === Sentiment analysis ===
def score_sentiment_trend(headlines):
    global sentiment_history
    if not headlines: 
        return 0.0

    results = sentiment_model(headlines)
    score = 0
    for r in results:
        if r["label"].lower() == "positive": score += r["score"]
        elif r["label"].lower() == "negative": score -= r["score"]
    sentiment_history.append(score)
    window = PORTFOLIO_SETTINGS["sentiment_window"]
    if len(sentiment_history) > window:
        sentiment_history = sentiment_history[-window:]
    avg_score = sum(sentiment_history) / len(sentiment_history)
    return avg_score

# === Main context ===
def analyze_global_context():
    reuters = _fetch_feed_headlines(REUTERS_FEEDS)
    bloomberg = _fetch_feed_headlines(BLOOMBERG_FEEDS)
    imf = fetch_imf_context()

    if not reuters and not bloomberg:
        if BOT_SETTINGS.get("strict_fallback", False):
            log("[ADVISOR] ❌ News feeds unavailable → strict fallback active → block trades")
            return {"economy": f"IMF: Growth {imf['global_growth']}",
                    "geopolitics": "(Strict fallback: block trades)",
                    "markets": "(Strict fallback: block trades)",
                    "block": True}
        else:
            log("[ADVISOR] ⚠️ News feeds unavailable → fallback mode")
            return {"economy": f"IMF: Growth {imf['global_growth']}",
                    "geopolitics": "(Fallback risks: inflation, geopolitics)",
                    "markets": "(Fallback: tech, energy, crypto)",
                    "fallback": True}

    # Apply sentiment trend
    all_headlines = (reuters + bloomberg)[:10]
    sentiment_score = score_sentiment_trend(all_headlines)

    return {
        "economy": f"IMF: Growth {imf['global_growth']}, Inflation {imf['inflation']}",
        "geopolitics": "; ".join(reuters[:2]) if reuters else "(No Reuters headlines)",
        "markets": "; ".join(bloomberg[:2]) if bloomberg else "(No Bloomberg headlines)",
        "sentiment_score": sentiment_score,
        "fallback": False,
    }

# === Opportunity detector ===
def detect_opportunities():
    ctx = analyze_global_context()
    if ctx.get("block", False): 
        return []

    text_geo = ctx["geopolitics"].lower()
    text_mkt = ctx["markets"].lower()
    opps = []

    if ctx.get("fallback", False):
        for sym in BOT_SETTINGS["symbols"]:
            opps.append({"sector": "General", "asset": sym, "reason": "Fallback mode"})
        return opps

    if any(k in text_geo for k in ("oil", "opec", "energy", "supply", "middle east")):
        opps.append({"sector": "Energy", "asset": "USOILm", "reason": "Oil/geopolitical tension"})
    if any(k in text_geo for k in ("fed", "inflation", "rate", "tariff", "uncertainty", "risk")):
        opps.append({"sector": "Precious Metals", "asset": "XAUUSDm", "reason": "Policy/geopolitical uncertainty"})
    if any(k in text_mkt for k in ("crypto", "bitcoin", "btc", "etf", "digital")):
        opps.append({"sector": "Crypto", "asset": "BTCUSDm", "reason": "Momentum / flows"})
    if any(k in text_mkt for k in ("tech", "ai", "nasdaq", "semiconductor", "chip")):
        opps.append({"sector": "Tech", "asset": "NAS100m", "reason": "AI/Tech leadership"})
    return opps

# === Main Advisor Logic ===
def advisor_report(profile="balanced"):
    return {
        "global_context": analyze_global_context(),
        "opportunities": detect_opportunities(),
        "sources": ["Reuters RSS", "Bloomberg RSS", "IMF WEO"],
    }

def advisor_allows_trade(signal, profile="balanced"):
    rep = advisor_report(profile)

    # Hard block by calendar
    if calendar_blocks_trading():
        return False, {"reason": "calendar_block"}

    # Hard block by strict fallback
    if rep["global_context"].get("block", False):
        log("[ADVISOR] ❌ Blocked all trades (strict fallback).")
        return False, rep

    # Sentiment threshold filter
    score = rep["global_context"].get("sentiment_score", 0.0)
    if abs(score) < PORTFOLIO_SETTINGS["sentiment_threshold"]:
        log(f"[ADVISOR] ❌ Weak sentiment trend (score={score:.2f}) → block.")
        return False, {"reason": "weak_sentiment"}

    allowed_assets = [op["asset"] for op in rep["opportunities"]]
    if signal["symbol"] in allowed_assets:
        log(f"[ADVISOR] ✅ {signal['symbol']} allowed (sentiment {score:.2f}).")
        return True, rep

    log(f"[ADVISOR] ❌ {signal['symbol']} not in Advisor opportunities.")
    return False, rep
