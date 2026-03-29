import asyncio
from fastapi import APIRouter, Request, Query
from backend.services.ai_service import get_latest_signal
from backend.backtester import run_backtest

router = APIRouter()

@router.get("/latest")
async def latest_signal(request: Request, ticker: str = Query(default="TSLA")):
    ticker = ticker.upper()
    latest = getattr(request.app.state, "latest_signals", {})
    signal = latest.get(ticker)
    
    if not signal:
        # start watching this ticker in background
        from ai.pipeline import start_background_loop
        
        async def push_signal(s: dict):
            t = s.get("ticker", "UNKNOWN")
            request.app.state.latest_signals[t] = s
            request.app.state.signal_history.append(s)
        
        # only start if not already in watchlist
        watchlist = getattr(request.app.state, "watchlist", [])
        if ticker not in watchlist and len(watchlist) < 3:
            watchlist.append(ticker)
            request.app.state.watchlist = watchlist
            asyncio.create_task(start_background_loop(ticker, on_signal=push_signal))
        
        return {
            "ticker": ticker,
            "detected": False,
            "signal_type": "neutral",
            "avg_sentiment": 0,
            "item_count": 0,
            "flagged_items": [],
            "brief": {},
            "prediction": {},
            "combined_signal": {
                "verdict": "LOADING",
                "confidence": "—",
                "sentiment_aligned": False,
                "price_aligned": False,
            },
            "message": f"Starting analysis for {ticker}... refresh in 60 seconds."
        }
    
    return signal

@router.get("/history")
async def signal_history(request: Request, ticker: str = Query(default="TSLA")):
    ticker = ticker.upper()
    history = getattr(request.app.state, "signal_history", [])
    filtered = [s for s in history if s.get("ticker") == ticker]
    return {"signals": filtered, "count": len(filtered)}

@router.get("/health")
async def health():
    return {"status": "ok"}

@router.get("/backtest")
async def backtest(event: str = None, ticker: str = None):
    """Run historical backtest. ?event=adani or ?event=cybertruck or ?event=tsla_earnings"""
    return run_backtest(event_id=event, ticker=ticker)

@router.get("/backtest/summary")
async def backtest_summary():
    """Returns just the accuracy stats — fast, for dashboard display"""
    import json
    from backend.backtester import OUTPUT_DIR
    
    report_path = OUTPUT_DIR / "backtest_report.json"
    if report_path.exists():
        with open(report_path, "r") as f:
            report = json.load(f)
            return report.get("summary", {})
    return {"error": "Backtest report not found. Run python backend/backtester.py first."}

@router.get("/prediction")
async def price_prediction(ticker: str = Query(default="TSLA")):
    from ai.prediction.prophet_model import predict
    return predict(ticker.upper())

@router.get("/watchlist")
async def get_watchlist(request: Request):
    return {"watchlist": getattr(request.app.state, "watchlist", [])}

@router.post("/watchlist/add")
async def add_to_watchlist(request: Request, ticker: str = Query(...)):
    from ai.pipeline import start_background_loop
    ticker = ticker.upper()
    watchlist = getattr(request.app.state, "watchlist", [])
    if ticker in watchlist:
        return {"watchlist": watchlist, "message": f"{ticker} already in watchlist"}
    if len(watchlist) >= 3:
        return {"error": "Max 3 tickers allowed", "watchlist": watchlist}
    watchlist.append(ticker)
    request.app.state.watchlist = watchlist
    async def push_signal(signal: dict):
        t = signal.get("ticker", "UNKNOWN")
        request.app.state.latest_signals[t] = signal
        request.app.state.signal_history.append(signal)
    asyncio.create_task(start_background_loop(ticker, on_signal=push_signal))
    return {"watchlist": watchlist, "message": f"{ticker} added"}

@router.post("/watchlist/remove")
async def remove_from_watchlist(request: Request, ticker: str = Query(...)):
    ticker = ticker.upper()
    watchlist = getattr(request.app.state, "watchlist", [])
    if ticker in watchlist:
        watchlist.remove(ticker)
    request.app.state.watchlist = watchlist
    return {"watchlist": watchlist}

@router.get("/price")
async def live_price(ticker: str = Query(default="TSLA")):
    from data.fetcher import get_live_price
    return get_live_price(ticker.upper())