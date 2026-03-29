import os
import ssl
import asyncio
import requests
import feedparser
import yfinance as yf
import urllib3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from newsapi import NewsApiClient
from datetime import datetime, timezone, timedelta

load_dotenv()

# ── SSL Fix (corporate/college network with self-signed proxy cert) ─────────
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Patch all requests sessions to skip SSL verification
_original_request = requests.Session.request
def _no_ssl_request(self, *args, **kwargs):
    kwargs.setdefault("verify", False)
    return _original_request(self, *args, **kwargs)
requests.Session.request = _no_ssl_request

# Fix yfinance SSL (it uses curl under the hood on some systems)
os.environ["CURL_CA_BUNDLE"] = ""
os.environ["REQUESTS_CA_BUNDLE"] = ""

# Fix feedparser SSL
ssl._create_default_https_context = ssl._create_unverified_context
# ───────────────────────────────────────────────────────────────────────────

# ── API Keys ────────────────────────────────────────────────────────────────
NEWSAPI_KEY  = os.getenv("NEWS_API_KEY", "")
FINNHUB_KEY  = os.getenv("FINNHUB_KEY", "")   # free at finnhub.io
# StockTwits, Yahoo RSS, SEC EDGAR — no key needed


# ════════════════════════════════════════════════════════════════════════════
# SOURCE 1 — NewsAPI headlines
# ════════════════════════════════════════════════════════════════════════════
def fetch_news(ticker: str) -> list[dict]:
    try:
        newsapi = NewsApiClient(api_key=NEWSAPI_KEY)
        response = newsapi.get_everything(
            q=ticker,
            language="en",
            sort_by="publishedAt",
            page_size=15,
        )
        results = []
        for a in response.get("articles", []):
            if not a.get("title"):
                continue
            results.append({
                "source": "newsapi",
                "text": a["title"],
                "timestamp": a["publishedAt"],
                "url": a.get("url", ""),
                "weight": 1.0,
            })
        print(f"[Fetcher] NewsAPI: {len(results)} items")
        return results
    except Exception as e:
        print(f"[Fetcher] NewsAPI error: {e}")
        return []


# ════════════════════════════════════════════════════════════════════════════
# SOURCE 2 — Yahoo Finance RSS (real-time, no key)
# ════════════════════════════════════════════════════════════════════════════
def fetch_yahoo_rss(ticker: str) -> list[dict]:
    try:
        url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        feed = feedparser.parse(url)
        results = []
        for entry in feed.entries[:15]:
            results.append({
                "source": "yahoo_rss",
                "text": entry.title,
                "timestamp": entry.get("published", datetime.utcnow().isoformat()),
                "url": entry.get("link", ""),
                "weight": 1.0,
            })
        print(f"[Fetcher] Yahoo RSS: {len(results)} items")
        return results
    except Exception as e:
        print(f"[Fetcher] Yahoo RSS error: {e}")
        return []


# ════════════════════════════════════════════════════════════════════════════
# SOURCE 4 — yfinance extras (analyst recs + recent news)
# ════════════════════════════════════════════════════════════════════════════
def fetch_yfinance_extras(ticker: str) -> list[dict]:
    results = []
    try:
        stock = yf.Ticker(ticker)

        for article in (stock.news or [])[:10]:
            content = article.get("content", {})
            title = (
                content.get("title")
                or article.get("title", "")
            ).strip()

            pub_time = (
                content.get("pubDate")
                or article.get("providerPublishTime")
            )

            if isinstance(pub_time, (int, float)):
                timestamp = datetime.utcfromtimestamp(pub_time).isoformat()
            else:
                timestamp = str(pub_time) if pub_time else datetime.utcnow().isoformat()

            if title:
                results.append({
                    "source": "yf_news",
                    "text": title,
                    "timestamp": timestamp,
                    "url": content.get("canonicalUrl", {}).get("url", "") or article.get("link", ""),
                    "weight": 1.0,
                })

        recs = stock.recommendations
        if recs is not None and not recs.empty:
            latest = recs.iloc[-1]
            total_buy  = int(latest["strongBuy"] if "strongBuy" in latest.index else 0) + int(latest["buy"] if "buy" in latest.index else 0)
            total_sell = int(latest["strongSell"] if "strongSell" in latest.index else 0) + int(latest["sell"] if "sell" in latest.index else 0)
            total_hold = int(latest["hold"] if "hold" in latest.index else 0)

            if total_buy > total_sell and total_buy > total_hold:
                rec_text = f"{ticker} analyst consensus: majority BUY rating ({total_buy} buys vs {total_sell} sells)"
            elif total_sell > total_buy:
                rec_text = f"{ticker} analyst consensus: majority SELL rating ({total_sell} sells vs {total_buy} buys)"
            else:
                rec_text = f"{ticker} analyst consensus: HOLD — {total_hold} hold ratings"

            results.append({
                "source": "yf_analyst",
                "text": rec_text,
                "timestamp": datetime.utcnow().isoformat(),
                "weight": 1.5,
            })

        hist = stock.history(period="5d")
        if not hist.empty:
            open_price  = hist["Close"].iloc[0]
            close_price = hist["Close"].iloc[-1]
            change_pct  = ((close_price - open_price) / open_price) * 100
            direction   = "up" if change_pct > 0 else "down"
            momentum_text = (
                f"{ticker} price moved {direction} {abs(change_pct):.1f}% "
                f"over the last 5 days (from {open_price:.2f} to {close_price:.2f})"
            )
            results.append({
                "source": "yf_price",
                "text": momentum_text,
                "timestamp": datetime.utcnow().isoformat(),
                "price_change_pct": round(change_pct, 2),
                "weight": 1.2,
            })

        print(f"[Fetcher] yfinance extras: {len(results)} items")
        return results

    except Exception as e:
        print(f"[Fetcher] yfinance extras error: {e}")
        return []


# ════════════════════════════════════════════════════════════════════════════
# SOURCE 5 — Google Trends via pytrends
# ════════════════════════════════════════════════════════════════════════════
def fetch_trend_score(ticker: str) -> float:
    TERM_MAP = {
        "TSLA": "Tesla stock",
        "AAPL": "Apple stock",
        "NVDA": "Nvidia stock",
        "AMZN": "Amazon stock",
        "MSFT": "Microsoft stock",
    }
    term = TERM_MAP.get(ticker, f"{ticker} stock")

    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="en-US", tz=360, timeout=(10, 25))
        pytrends.build_payload([term], timeframe="now 1-d", geo="US")
        data = pytrends.interest_over_time()

        if data.empty or term not in data.columns:
            print("[Fetcher] pytrends: no data, using neutral weight 1.0")
            return 1.0

        latest_score = int(data[term].iloc[-1])
        multiplier = round(0.5 + (latest_score / 100), 3)
        print(f"[Fetcher] pytrends: '{term}' interest={latest_score}/100 → weight={multiplier}x")
        return multiplier

    except ImportError:
        print("[Fetcher] pytrends not installed — run: pip install pytrends")
        return 1.0
    except Exception as e:
        print(f"[Fetcher] pytrends error: {e}")
        return 1.0


# ════════════════════════════════════════════════════════════════════════════
# SOURCE 6 — SEC EDGAR insider trades (Form 4 filings)
# ════════════════════════════════════════════════════════════════════════════
def fetch_insider_trades(ticker: str) -> list[dict]:
    try:
        today = datetime.utcnow()
        start = (today - timedelta(days=30)).strftime("%Y-%m-%d")
        end   = today.strftime("%Y-%m-%d")

        url = (
            f"https://efts.sec.gov/LATEST/search-index?q=%22{ticker}%22"
            f"&dateRange=custom&startdt={start}&enddt={end}&forms=4&hits.hits._source=display_names,file_date"
        )
        headers = {"User-Agent": "PulseAI sanveer@pulseai.com"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        hits = resp.json().get("hits", {}).get("hits", [])
        results = []

        for hit in hits[:8]:
            src = hit.get("_source", {})
            display_names = src.get("display_names", ["Unknown insider"])
            name = display_names[0] if display_names else "Unknown insider"
            filed_at = src.get("file_date", today.strftime("%Y-%m-%d"))

            trade_text = (
                f"{ticker} insider {name} filed a Form 4 transaction report "
                f"on {filed_at} — insider activity detected"
            )
            results.append({
                "source": "sec_edgar",
                "text": trade_text,
                "timestamp": filed_at,
                "weight": 1.8,
            })

        print(f"[Fetcher] SEC EDGAR: {len(results)} insider filings")
        return results

    except Exception as e:
        print(f"[Fetcher] SEC EDGAR error: {e}")
        return []


# ════════════════════════════════════════════════════════════════════════════
# SOURCE 7 — Finnhub (analyst ratings + earnings surprises)
# ════════════════════════════════════════════════════════════════════════════
def fetch_finnhub(ticker: str) -> list[dict]:
    if not FINNHUB_KEY:
        print("[Fetcher] Finnhub: no key set — skipping (set FINNHUB_KEY in .env)")
        return []

    results = []
    base = "https://finnhub.io/api/v1"
    headers = {"X-Finnhub-Token": FINNHUB_KEY}

    try:
        resp = requests.get(f"{base}/stock/recommendation", params={"symbol": ticker}, headers=headers, timeout=8)
        resp.raise_for_status()
        recs = resp.json()
        if recs:
            latest = recs[0]
            buy_count  = latest.get("buy", 0) + latest.get("strongBuy", 0)
            sell_count = latest.get("sell", 0) + latest.get("strongSell", 0)
            hold_count = latest.get("hold", 0)
            rec_text = (
                f"{ticker} Finnhub analyst summary for {latest.get('period', 'recent')}: "
                f"{buy_count} buys, {hold_count} holds, {sell_count} sells"
            )
            results.append({
                "source": "finnhub_analyst",
                "text": rec_text,
                "timestamp": datetime.utcnow().isoformat(),
                "weight": 1.5,
            })
    except Exception as e:
        print(f"[Fetcher] Finnhub analyst error: {e}")

    try:
        resp = requests.get(f"{base}/stock/earnings", params={"symbol": ticker, "limit": 4}, headers=headers, timeout=8)
        resp.raise_for_status()
        earnings = resp.json()
        for e in (earnings or [])[:2]:
            actual   = e.get("actual")
            estimate = e.get("estimate")
            period   = e.get("period", "recent quarter")
            if actual is not None and estimate is not None:
                diff = actual - estimate
                beat_miss = "beat" if diff >= 0 else "missed"
                surprise_text = (
                    f"{ticker} earnings {beat_miss} estimates for {period}: "
                    f"actual EPS {actual:.2f} vs estimate {estimate:.2f} "
                    f"({'+'if diff>=0 else ''}{diff:.2f} surprise)"
                )
                results.append({
                    "source": "finnhub_earnings",
                    "text": surprise_text,
                    "timestamp": datetime.utcnow().isoformat(),
                    "weight": 2.0,
                    "eps_surprise": round(diff, 4),
                })
    except Exception as e:
        print(f"[Fetcher] Finnhub earnings error: {e}")

    print(f"[Fetcher] Finnhub: {len(results)} items")
    return results


def get_live_price(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        return {
            "ticker": ticker,
            "price": round(float(info.last_price), 2),
            "change": round(float(info.last_price - info.previous_close), 2),
            "change_pct": round(
                ((info.last_price - info.previous_close) / info.previous_close) * 100, 2
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        print(f"[Fetcher] Live price error: {e}")
        return {"ticker": ticker, "price": None, "change": None, "change_pct": None}


# ════════════════════════════════════════════════════════════════════════════
# MASTER FETCHER — fetch_all()
# ════════════════════════════════════════════════════════════════════════════
async def fetch_all(ticker: str) -> list[dict]:
    print(f"\n[Fetcher] Starting full fetch for {ticker}...")

    loop = asyncio.get_running_loop()

    news_task        = loop.run_in_executor(None, fetch_news,            ticker)
    yahoo_task       = loop.run_in_executor(None, fetch_yahoo_rss,       ticker)
    yf_task          = loop.run_in_executor(None, fetch_yfinance_extras,  ticker)
    sec_task         = loop.run_in_executor(None, fetch_insider_trades,   ticker)
    finnhub_task     = loop.run_in_executor(None, fetch_finnhub,          ticker)
    trend_task       = loop.run_in_executor(None, fetch_trend_score,      ticker)

    (
        news, yahoo, yf_extras,
        sec, finnhub, trend_multiplier
    ) = await asyncio.gather(
        news_task, yahoo_task, yf_task,
        sec_task, finnhub_task, trend_task
    )

    all_data = []
    all_data.extend(news)
    all_data.extend(yahoo)
    all_data.extend(yf_extras)
    all_data.extend(sec)
    all_data.extend(finnhub)

    if trend_multiplier != 1.0:
        print(f"[Fetcher] Applying trend multiplier {trend_multiplier}x to {len(all_data)} items")
        for item in all_data:
            item["weight"] = round(item.get("weight", 1.0) * trend_multiplier, 3)

    for item in all_data:
        item["trend_multiplier"] = trend_multiplier

    def _ts(item):
        ts = item.get("timestamp", "")
        try:
            return ts if isinstance(ts, str) else str(ts)
        except Exception:
            return ""

    all_data.sort(key=_ts, reverse=True)

    sources = {}
    for item in all_data:
        s = item.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1

    print(f"[Fetcher] Total: {len(all_data)} items from {len(sources)} sources")
    for src, count in sources.items():
        print(f"          {src}: {count}")
    print(f"          trend_multiplier: {trend_multiplier}x\n")

    return all_data


# ════════════════════════════════════════════════════════════════════════════
# Quick test — run directly: python data/fetcher.py
# ════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import json

    ticker = "TSLA"
    print(f"Running standalone test for {ticker}...\n")

    results = asyncio.run(fetch_all(ticker))

    print("\n--- TOP 5 ITEMS ---")
    print(json.dumps(results[:5], indent=2, default=str))
    print(f"\nTotal: {len(results)} items")

    out = os.path.join(os.path.dirname(__file__), f"{ticker}_pipeline_output.json")
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[SAVED] {out}")