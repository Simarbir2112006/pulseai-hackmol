import requests
from datetime import datetime
import random
import yfinance as yf

API_URL = "http://localhost:8000"

# ── Trending tickers ───────────────────────────────────────────────────────
# Fallback list if yfinance trending call fails
FALLBACK_TICKERS = [
    "TSLA", "NVDA", "AAPL", "MSFT", "AMZN",
    "META", "GOOGL", "AMD", "NFLX", "PLTR"
]
def get_trending_tickers(limit: int = 10) -> list[str]:
    """
    Fetch top trending tickers from Yahoo Finance via yfinance.
    Falls back to a curated list if the call fails.
    """
    try:
        screener = yf.screen("most_actives", size=limit)
        quotes = screener.get("quotes", [])
        tickers = [q.get("symbol", "") for q in quotes if q.get("symbol")]
        if tickers:
            return [t.upper() for t in tickers[:limit]]
    except Exception as e:
        print(f"[Trending] yfinance screen failed: {e}")

    return FALLBACK_TICKERS[:limit]

# ── Existing loader code (unchanged) ──────────────────────────────────────

def load_data(ticker: str) -> dict:
    try:
        response = requests.get(
            f"{API_URL}/signals/latest",
            params={"ticker": ticker},
            timeout=10
        )
        if response.status_code != 200:
            raise Exception(f"Bad response: {response.status_code}")

        raw = response.json()

        time_series = []
        for item in raw.get("flagged_items", []):
            ts = item.get("timestamp", "")
            try:
                parsed = datetime.fromisoformat(ts.replace("Z", ""))
                time_str = parsed.strftime("%H:%M:%S")
            except Exception:
                time_str = ts[-8:] if ts else "00:00:00"
            time_series.append({
                "time": time_str,
                "sentiment": round(float(item.get("score", 0)) * 100, 2),
                "source": item.get("source", "unknown"),
                "z_score": item.get("z_score", None),
            })

        time_series.sort(key=lambda x: x["time"])

        news = [
            {
                "title": item.get("text", ""),
                "source": item.get("source", "unknown"),
                "time": item.get("timestamp", ""),
                "score": item.get("score", 0),
                "z_score": item.get("z_score"),
            }
            for item in raw.get("flagged_items", [])
        ]

        prediction = raw.get("prediction", {})
        combined = raw.get("combined_signal", {})
        brief = raw.get("brief", {})

        return {
            "ticker": raw.get("ticker", ticker),
            "timestamp": raw.get("timestamp", ""),
            "sentiment": round(float(raw.get("avg_sentiment", 0)) * 100, 2),
            "time_series": time_series,
            "anomaly": bool(raw.get("detected", False)),
            "signal_type": raw.get("signal_type", "neutral"),
            "news": news,
            "item_count": raw.get("item_count", 0),

            "current_price": prediction.get("current_price", "?"),
            "predicted_tomorrow": prediction.get("predicted_tomorrow", "?"),
            "predicted_tomorrow_date": prediction.get("predicted_tomorrow_date", ""),
            "pct_change_tomorrow": prediction.get("pct_change_tomorrow", 0),
            "price_direction": prediction.get("direction", "unknown"),
            "price_lower": prediction.get("confidence_interval_tomorrow", {}).get("lower", "?"),
            "price_upper": prediction.get("confidence_interval_tomorrow", {}).get("upper", "?"),

            "verdict": combined.get("verdict", "HOLD"),
            "confidence": combined.get("confidence", "low"),
            "sentiment_aligned": combined.get("sentiment_aligned", False),
            "price_aligned": combined.get("price_aligned", False),

            "llm_brief": brief.get("summary", "No summary available"),
            "why_it_matters": brief.get("why_it_matters", ""),
            "what_this_means": brief.get("what_this_means", ""),
            "brief_confidence": brief.get("confidence", ""),
            "sources_used": brief.get("sources_used", []),

            "signal": combined.get("verdict", "HOLD"),
        }

    except Exception as e:
        print(f"[Loader] Error: {e}")
        return _mock(ticker)


def get_watchlist() -> list:
    try:
        r = requests.get(f"{API_URL}/signals/watchlist", timeout=5)
        return r.json().get("watchlist", ["TSLA"])
    except Exception:
        return ["TSLA"]


def add_ticker(ticker: str) -> dict:
    try:
        r = requests.post(
            f"{API_URL}/signals/watchlist/add",
            params={"ticker": ticker},
            timeout=5
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def remove_ticker(ticker: str) -> dict:
    try:
        r = requests.post(
            f"{API_URL}/signals/watchlist/remove",
            params={"ticker": ticker},
            timeout=5
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def _mock(ticker: str) -> dict:
    """Fallback mock if backend is down."""
    return {
        "ticker": ticker,
        "timestamp": "",
        "sentiment": 50.0,
        "time_series": [],
        "anomaly": False,
        "signal_type": "neutral",
        "news": [],
        "item_count": 0,
        "current_price": "?",
        "predicted_tomorrow": "?",
        "predicted_tomorrow_date": "",
        "pct_change_tomorrow": 0,
        "price_direction": "unknown",
        "price_lower": "?",
        "price_upper": "?",
        "verdict": "HOLD",
        "confidence": "low",
        "sentiment_aligned": False,
        "price_aligned": False,
        "llm_brief": "Backend unavailable.",
        "why_it_matters": "",
        "what_this_means": "",
        "brief_confidence": "",
        "sources_used": [],
        "signal": "HOLD",
    }
