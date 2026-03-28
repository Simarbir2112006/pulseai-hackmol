import yfinance as yf
from newsapi import NewsApiClient
import json
from datetime import datetime

# =============================================
# API KEYS — fill these in before hackathon
# =============================================
NEWSAPI_KEY = "e9434256287646dc9586bdbb81deaf4a"

# =============================================
# FLAG: Set to True once Reddit API is approved
# =============================================
REDDIT_API_READY = False

# =============================================
# SOURCE 1 — News Headlines (NewsAPI)
# =============================================
def fetch_news(ticker):
    newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
    response = newsapi.get_everything(
        q=ticker, language="en",
        sort_by="publishedAt", page_size=10
    )
    return [
        {
            "source": "news",
            "text": a["title"],
            "timestamp": a["publishedAt"]
        }
        for a in response["articles"]
    ]

# =============================================
# SOURCE 2 — Reddit Posts
# MOCKED until API access is approved.
# Once approved:
#   1. pip install praw
#   2. Set REDDIT_API_READY = True above
#   3. Fill in REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET
# =============================================
REDDIT_CLIENT_ID = "your_client_id_here"
REDDIT_CLIENT_SECRET = "your_client_secret_here"

def fetch_reddit(ticker):
    if not REDDIT_API_READY:
        print("[INFO] Reddit API not yet approved — using mock data.")
        return [
            {"source": "reddit", "text": f"{ticker} earnings beat expectations, bulls loading up", "timestamp": "2026-03-28T09:30:00"},
            {"source": "reddit", "text": f"Is {ticker} still a buy at this price?", "timestamp": "2026-03-28T09:00:00"},
            {"source": "reddit", "text": f"{ticker} short sellers getting crushed today", "timestamp": "2026-03-28T08:30:00"},
            {"source": "reddit", "text": f"Major recall rumor circulating for {ticker} — anyone else seeing this?", "timestamp": "2026-03-28T08:00:00"},
            {"source": "reddit", "text": f"{ticker} CEO sold shares last week, should we be worried?", "timestamp": "2026-03-28T07:30:00"},
        ]

    # --- Real Reddit fetch (runs only when REDDIT_API_READY = True) ---
    import praw
    reddit = praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent="pulseai_test"
    )
    results = []
    sub = reddit.subreddit("stocks+investing+wallstreetbets")
    for post in sub.search(ticker, limit=10, sort="new"):
        results.append({
            "source": "reddit",
            "text": post.title,
            "timestamp": datetime.utcfromtimestamp(post.created_utc).isoformat()
        })
    return results

# =============================================
# SOURCE 3 — Stock Price History (yfinance)
# =============================================
def fetch_price(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="5d")
    results = []
    for timestamp, row in hist.iterrows():
        results.append({
            "source": "price",
            "text": f"{ticker} closed at {row['Close']:.2f}",
            "timestamp": str(timestamp),
            "price": round(row["Close"], 2),
            "volume": int(row["Volume"])
        })
    return results

# =============================================
# MAIN — Fetch, merge, sort, output
# =============================================
ticker = "TSLA"
print(f"Fetching data for {ticker}...\n")

all_data = []
all_data.extend(fetch_news(ticker))
all_data.extend(fetch_reddit(ticker))
all_data.extend(fetch_price(ticker))

# Sort by most recent first
all_data.sort(key=lambda x: x["timestamp"], reverse=True)

# Preview top 5 items
print("--- TOP 5 ITEMS (most recent) ---")
print(json.dumps(all_data[:5], indent=2))
print(f"\nTotal items fetched: {len(all_data)}")

# Save full output to JSON file — Simarbir can use this directly for FinBERT scoring
output_filename = f"{ticker}_pipeline_output.json"
with open(output_filename, "w") as f:
    json.dump(all_data, f, indent=2)

print(f"\n[SAVED] Full output written to: {output_filename}")
print("[NEXT] Hand this file to Simarbir for FinBERT sentiment scoring.")