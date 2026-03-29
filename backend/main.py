import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.signals import router
from ai.pipeline import start_background_loop
from ai.notifications.telegram_bot import send_telegram_alert
from dotenv import load_dotenv

load_dotenv()

DEFAULT_WATCHLIST = ["TSLA"]

app = FastAPI(
    title="PulseAI",
    description="Autonomous financial market intelligence for retail investors.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/signals")


@app.on_event("startup")
async def startup():
    app.state.signal_history = []
    app.state.latest_signals = {}
    app.state.watchlist = DEFAULT_WATCHLIST.copy()
    app.state.processing_tickers = set()

    async def push_signal(signal: dict):
        ticker = signal.get("ticker", "UNKNOWN")
        app.state.latest_signals[ticker] = signal
        app.state.signal_history.append(signal)

        # only alert on strong correlated signals
        combined = signal.get("combined_signal", {})
        verdict = combined.get("verdict", "HOLD")
        sentiment_aligned = combined.get("sentiment_aligned", False)
        price_aligned = combined.get("price_aligned", False)

        if verdict in ("STRONG BUY", "STRONG SELL") and sentiment_aligned and price_aligned:
            prediction = signal.get("prediction", {})
            brief = signal.get("brief", {})
            send_telegram_alert(
                ticker        = ticker,
                signal_type   = "positive" if verdict == "STRONG BUY" else "negative",
                score         = signal.get("avg_sentiment", 0),
                price         = prediction.get("current_price", 0),
                pct_move      = prediction.get("pct_change_tomorrow", 0),
                anomaly_count = len(signal.get("flagged_items", [])),
                headline      = brief.get("headline", "")
                                or (signal.get("flagged_items", [{}])[0].get("text", "")
                                    if signal.get("flagged_items") else ""),
            )

    for ticker in app.state.watchlist:
        asyncio.create_task(
            start_background_loop(ticker, on_signal=push_signal)
        )