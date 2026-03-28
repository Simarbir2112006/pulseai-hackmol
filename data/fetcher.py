import yfinance as yf
from newsapi import NewsApiClient
from datetime import datetime
import os

NEWSAPI_KEY = os.getenv("NEWS_API_KEY", "")

def fetch_news(ticker: str) -> list[dict]:
    try:
        newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
        response = newsapi.get_everything(
            q=ticker,
            language="en",
            sort_by="publishedAt",
            page_size=10
        )
        return [
            {
                "source": "news",
                "text": a["title"],
                "timestamp": a["publishedAt"]
            }
            for a in response["articles"]
        ]
    except Exception as e:
        print(f"[Fetcher] NewsAPI error: {e}")
        return []

import feedparser

def fetch_yahoo_rss(ticker: str) -> list[dict]:
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        feed = feedparser.parse(url)
        return [
            {
                "source": "yahoo",
                "text": entry.title,
                "timestamp": entry.published
            }
            for entry in feed.entries[:10]
        ]
    except Exception as e:
        print(f"[Fetcher] Yahoo RSS error: {e}")
        return []

def fetch_reddit_mock(ticker: str) -> list[dict]:
    """Mock reddit data until API is approved."""
    return [
        {"source": "reddit", "text": f"{ticker} earnings beat expectations, bulls loading up", "timestamp": datetime.utcnow().isoformat()},
        {"source": "reddit", "text": f"Is {ticker} still a buy at this price?", "timestamp": datetime.utcnow().isoformat()},
        {"source": "reddit", "text": f"{ticker} short sellers getting crushed today", "timestamp": datetime.utcnow().isoformat()},
        {"source": "reddit", "text": f"Major recall rumor circulating for {ticker}", "timestamp": datetime.utcnow().isoformat()},
        {"source": "reddit", "text": f"{ticker} CEO sold shares last week, should we be worried?", "timestamp": datetime.utcnow().isoformat()},
    ]


def fetch_price(ticker: str) -> list[dict]:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        return [
            {
                "source": "price",
                "text": f"{ticker} closed at {row['Close']:.2f}",
                "timestamp": str(timestamp),
                "price": round(row["Close"], 2),
                "volume": int(row["Volume"])
            }
            for timestamp, row in hist.iterrows()
        ]
    except Exception as e:
        print(f"[Fetcher] yfinance error: {e}")
        return []


async def fetch_all(ticker: str) -> list[dict]:
    all_data = []
    all_data.extend(fetch_news(ticker))
    # all_data.extend(fetch_reddit_mock(ticker))
    # all_data.extend(fetch_price(ticker))
    all_data.extend(fetch_yahoo_rss(ticker))
    all_data.sort(key=lambda x: x["timestamp"], reverse=True)
    return all_data