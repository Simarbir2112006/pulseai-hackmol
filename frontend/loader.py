import requests
from datetime import datetime

API_URL = "http://localhost:8000"


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

        # -----------------------------
        # Time series (for sentiment graph)
        # -----------------------------
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

        # -----------------------------
        # News mapping
        # -----------------------------
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

        # -----------------------------
        # FIXED: Prediction mapping
        # -----------------------------
        prediction = {
            "current_price": raw.get("current_price", "?"),
            "predicted_tomorrow": raw.get("predicted_tomorrow", "?"),
            "predicted_tomorrow_date": raw.get("predicted_tomorrow_date", ""),
            "pct_change_tomorrow": raw.get("pct_change_tomorrow", 0),
            "direction": "unknown",
            "confidence_interval_tomorrow": {
                "lower": raw.get("price_lower", "?"),
                "upper": raw.get("price_upper", "?")
            }
        }

        # -----------------------------
        # FIXED: Combined signal mapping
        # -----------------------------
        combined = {
            "verdict": raw.get("brief", {}).get("signal", "HOLD"),
            "confidence": "low",
            "sentiment_aligned": False,
            "price_aligned": False
        }

        brief = raw.get("brief", {})

        # -----------------------------
        # FINAL STRUCTURE (FRONTEND READY)
        # -----------------------------
        return {
            "ticker": raw.get("ticker", ticker),
            "timestamp": raw.get("timestamp", ""),

            # sentiment
            "sentiment": round(float(raw.get("avg_sentiment", 0)) * 100, 2),
            "time_series": time_series,

            # anomaly
            "anomaly": bool(raw.get("detected", False)),
            "signal_type": raw.get("signal_type", "neutral"),

            # news
            "news": news,
            "item_count": raw.get("item_count", 0),

            # FIXED: Price fields (no more $?)
            "current_price": prediction.get("current_price") or raw.get("current_price", "?"),
            "predicted_tomorrow": prediction.get("predicted_tomorrow"),
            "predicted_tomorrow_date": prediction.get("predicted_tomorrow_date"),
            "pct_change_tomorrow": prediction.get("pct_change_tomorrow"),
            "price_direction": prediction.get("direction"),
            "price_lower": prediction["confidence_interval_tomorrow"]["lower"],
            "price_upper": prediction["confidence_interval_tomorrow"]["upper"],

            # signal
            "verdict": combined.get("verdict"),
            "confidence": combined.get("confidence"),
            "sentiment_aligned": combined.get("sentiment_aligned"),
            "price_aligned": combined.get("price_aligned"),

            # LLM
            "llm_brief": brief.get("summary", "No summary available"),
            "why_it_matters": brief.get("why_it_matters", ""),
            "what_this_means": brief.get("what_this_means", ""),
            "brief_confidence": brief.get("confidence", ""),
            "sources_used": brief.get("sources_used", []),

            "signal": combined.get("verdict"),
        }

    except Exception as e:
        print(f"[Loader] Error: {e}")
        return _mock(ticker)


# -----------------------------
# Candlestick (no change needed)
# -----------------------------
def load_candle_data(ticker: str, period: str = "1mo", interval: str = "1d") -> dict:
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=period, interval=interval)
        if hist.empty:
            return {}

        return {
            "dates":   hist.index.strftime("%Y-%m-%d %H:%M").tolist(),
            "opens":   [round(float(v), 2) for v in hist["Open"]],
            "highs":   [round(float(v), 2) for v in hist["High"]],
            "lows":    [round(float(v), 2) for v in hist["Low"]],
            "closes":  [round(float(v), 2) for v in hist["Close"]],
            "volumes": [int(v) for v in hist["Volume"]],
        }

    except Exception as e:
        print(f"[Loader] Candle data error: {e}")
        return {}


# -----------------------------
# Fallback mock
# -----------------------------
def _mock(ticker: str) -> dict:
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