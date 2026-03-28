import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.signals import router
from ai.pipeline import start_background_loop
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

    async def push_signal(signal: dict):
        ticker = signal.get("ticker", "UNKNOWN")
        app.state.latest_signals[ticker] = signal
        app.state.signal_history.append(signal)

    for ticker in app.state.watchlist:
        asyncio.create_task(
            start_background_loop(ticker, on_signal=push_signal)
        )