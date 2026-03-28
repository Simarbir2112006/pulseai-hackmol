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
        combined   = raw.get("combined_signal", {})
        brief      = raw.get("brief", {})

        return {
            "ticker":                 raw.get("ticker", ticker),
            "timestamp":              raw.get("timestamp", ""),
            "sentiment":              round(float(raw.get("avg_sentiment", 0)) * 100, 2),
            "time_series":            time_series,
            "anomaly":                bool(raw.get("detected", False)),
            "signal_type":            raw.get("signal_type", "neutral"),
            "news":                   news,
            "item_count":             raw.get("item_count", 0),
            "current_price":          prediction.get("current_price", "?"),
            "predicted_tomorrow":     prediction.get("predicted_tomorrow", "?"),
            "predicted_tomorrow_date":prediction.get("predicted_tomorrow_date", ""),
            "pct_change_tomorrow":    prediction.get("pct_change_tomorrow", 0),
            "price_direction":        prediction.get("direction", "unknown"),
            "price_lower":            prediction.get("confidence_interval_tomorrow", {}).get("lower", "?"),
            "price_upper":            prediction.get("confidence_interval_tomorrow", {}).get("upper", "?"),
            "verdict":                combined.get("verdict", "HOLD"),
            "confidence":             combined.get("confidence", "low"),
            "sentiment_aligned":      combined.get("sentiment_aligned", False),
            "price_aligned":          combined.get("price_aligned", False),
            "llm_brief":              brief.get("summary", "No summary available"),
            "why_it_matters":         brief.get("why_it_matters", ""),
            "what_this_means":        brief.get("what_this_means", ""),
            "brief_confidence":       brief.get("confidence", ""),
            "sources_used":           brief.get("sources_used", []),
            "signal":                 combined.get("verdict", "HOLD"),
        }

    except Exception as e:
        print(f"[Loader] Error: {e}")
        return _mock(ticker)


def load_candle_data(ticker: str, period: str = "1mo", interval: str = "1d") -> dict:
    """
    Fetch OHLCV candle data directly from yfinance.
    period options : 1d, 5d, 1mo, 3mo, 6mo, 1y
    interval options: 1m, 5m, 15m, 30m, 1h, 1d
    Returns dict with lists: dates, opens, highs, lows, closes, volumes.
    """
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
