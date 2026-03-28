import requests
from datetime import datetime, timedelta
import random

API_URL = "http://localhost:8000/signals/latest"


def generate_mock_data(ticker):
    now = datetime.now()

    time_series = []
    for i in range(20):
        t = (now - timedelta(seconds=i * 5)).strftime("%H:%M:%S")
        sentiment = random.uniform(40, 70)

        time_series.append({
            "time": t,
            "sentiment": sentiment
        })

    time_series.reverse()

    anomaly = random.random() > 0.8

    news = [
        {
            "title": f"{ticker} gaining momentum in market",
            "source": "MockNews",
            "time": now.strftime("%H:%M:%S")
        },
        {
            "title": f"Investors discussing {ticker} heavily",
            "source": "Social Feed",
            "time": (now - timedelta(minutes=2)).strftime("%H:%M:%S")
        }
    ]

    return {
        "ticker": ticker,
        "sentiment": time_series[-1]["sentiment"],
        "time_series": time_series,
        "anomaly": anomaly,
        "news": news,
        "llm_brief": f"Mock analysis: sentiment trending {'positive' if not anomaly else 'volatile'}",
        "signal": random.choice(["BUY", "SELL", "HOLD"])
    }


def load_data(ticker):
    # 🔥 If API not available → use mock
    if not API_URL:
        return generate_mock_data(ticker)

    try:
        response = requests.get(f"{API_URL}?ticker={ticker}", timeout=5)

        if response.status_code != 200:
            raise Exception("Bad API response")

        raw = response.json()

        time_series = []
        for item in raw.get("flagged_items", []):
            ts = item.get("timestamp", "")

            try:
                parsed_time = datetime.fromisoformat(ts.replace("Z", ""))
                time_str = parsed_time.strftime("%H:%M:%S")
            except:
                time_str = ts[-8:] if ts else ""

            time_series.append({
                "time": time_str,
                "sentiment": float(item.get("score", 0)) * 100
            })

        time_series = sorted(time_series, key=lambda x: x["time"])

        news = []
        for item in raw.get("flagged_items", []):
            news.append({
                "title": item.get("text", ""),
                "source": item.get("source", "unknown"),
                "time": item.get("timestamp", "")
            })

        return {
            "ticker": raw.get("ticker", ticker),
            "sentiment": float(raw.get("avg_sentiment", 0)) * 100,
            "time_series": time_series,
            "anomaly": bool(raw.get("detected", False)),
            "news": news,
            "llm_brief": raw.get("brief", {}).get("summary", "No summary available"),
            "signal": raw.get("brief", {}).get("signal", "HOLD")
        }

    except Exception as e:
        print("API Error:", e)
        return generate_mock_data(ticker)