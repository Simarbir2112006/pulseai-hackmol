import asyncio
from sentiment.finbert import score_batch
from anomaly.detector import detect
from llm.groq_client import generate_brief
from agent.loop import run_loop

TICKER = "TSLA"


def analyze() -> dict:
    """
    On-demand single analysis run for TSLA.
    Synchronous — FastAPI can call this directly.

    Returns:
    {
        ticker, timestamp, detected, signal_type,
        avg_sentiment, item_count, flagged_items, brief
    }
    """
    from agent.loop import run_once
    return asyncio.run(run_once(TICKER))


def run_pipeline(texts: list[str]) -> dict:
    """
    Core logic — takes raw texts, runs the full AI stack.
    Useful for testing each stage independently without the agent loop.

    Usage:
        from ai.pipeline import run_pipeline
        result = run_pipeline(["Tesla recalls 10000 cars", "Musk tweets about TSLA"])
    """
    if not texts:
        return {
            "ticker": TICKER,
            "detected": False,
            "reason": "no data provided",
            "brief": {}
        }

    # stage 1 — sentiment
    scored = score_batch(texts)
    print(f"[Pipeline] Scored {len(scored)} items")

    # stage 2 — anomaly detection
    result = detect(scored)
    print(f"[Pipeline] Anomaly detected: {result.detected} | Signal: {result.signal_type} | Avg: {result.avg_sentiment:+.3f}")

    # stage 3 — brief generation (only if anomaly fired)
    brief = {}
    if result.detected:
        print(f"[Pipeline] Generating brief for {len(result.flagged_items)} flagged items...")
        brief = generate_brief(TICKER, result)

    return {
        "ticker": TICKER,
        "detected": result.detected,
        "signal_type": result.signal_type,
        "avg_sentiment": result.avg_sentiment,
        "item_count": result.item_count,
        "flagged_items": result.flagged_items,
        "brief": brief,
    }


def start_background_loop(on_signal=None):
    """
    Starts the autonomous 24/7 agent loop for TSLA.
    Call once at FastAPI startup.

    Example in FastAPI main.py:
        @app.on_event("startup")
        async def startup():
            asyncio.create_task(start_background_loop(on_signal=push_to_frontend))
    """
    print(f"[Pipeline] Starting background loop for {TICKER}")
    return run_loop(TICKER, on_signal=on_signal)