# === news_engine.py (Market Sentiment AI with Multi-Source) ===
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime, timedelta
from log import log

analyzer = SentimentIntensityAnalyzer()

# NewsAPI (primary source)
NEWS_API_KEY = "32c91d92205a4fd4b8e9f38944f5e784"
NEWS_URL = "https://newsapi.org/v2/everything"

CACHE = {}

def fetch_news(symbol="forex", hours=6):
    """
    Fetch latest financial news related to symbol.
    - Tries NewsAPI first
    - Falls back to Yahoo Finance RSS if NewsAPI fails
    Returns list of headlines.
    """
    global CACHE
    now = datetime.utcnow()
    if symbol in CACHE and (now - CACHE[symbol]["time"]).seconds < 300:
        return CACHE[symbol]["data"]

    headlines = []

    # --- Try NewsAPI ---
    try:
        params = {
            "q": symbol,
            "sortBy": "publishedAt",
            "from": (now - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "apiKey": NEWS_API_KEY,
            "language": "en",
        }
        r = requests.get(NEWS_URL, params=params, timeout=10)
        r.raise_for_status()

        # Force UTF-8 decode
        r.encoding = "utf-8"

        data = r.json()  # if this fails, we'll go to fallback
        if data.get("status") == "ok":
            articles = data.get("articles", [])
            headlines = [a.get("title", "") for a in articles if a.get("title")]
            log(f"[NEWS] ✅ Got {len(headlines)} headlines from NewsAPI")
    except Exception as e:
        log(f"[NEWS] ❌ NewsAPI failed: {e}")

    # --- Fallback: Yahoo Finance ---
    if not headlines:
        try:
            rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={symbol}&region=US&lang=en-US"
            r = requests.get(rss_url, timeout=10)
            r.raise_for_status()
            r.encoding = "utf-8"

            for line in r.text.splitlines():
                if "<title>" in line and "</title>" in line:
                    title = line.replace("<title>", "").replace("</title>", "").strip()
                    if title and "Yahoo" not in title:
                        headlines.append(title)
            log(f"[NEWS] ✅ Using Yahoo Finance fallback, got {len(headlines)} headlines")
        except Exception as e:
            log(f"[NEWS] ❌ Fallback failed: {e}")

    CACHE[symbol] = {"time": now, "data": headlines}
    return headlines

def sentiment_score(symbol="forex"):
    """
    Returns sentiment score ∈ [-1,1]
    -1 = very bearish, +1 = very bullish
    """
    headlines = fetch_news(symbol)
    if not headlines:
        return 0.0

    scores = []
    for h in headlines[:10]:  # top 10 headlines
        scores.append(analyzer.polarity_scores(h)["compound"])

    avg = sum(scores) / len(scores) if scores else 0.0
    log(f"[NEWS] 📰 {symbol} Sentiment={avg:.2f}")
    return avg
