import asyncio
from ai.sentiment.finbert import score_batch
from ai.anomaly.detector import detect
from ai.llm.groq_client import generate_brief
from ai.agent.loop import run_loop, run_once

TICKER = "TSLA"


def analyze() -> dict:
    return asyncio.run(run_once(TICKER))


def run_pipeline(texts: list[str]) -> dict:
    if not texts:
        return {"ticker": TICKER, "detected": False, "reason": "no data", "brief": {}}

    scored = score_batch(texts)
    print(f"[Pipeline] Scored {len(scored)} items")

    result = detect(scored)
    print(f"[Pipeline] Detected: {result.detected} | Signal: {result.signal_type} | Avg: {result.avg_sentiment:+.3f}")

    brief = {}
    if result.detected:
        print(f"[Pipeline] Generating brief...")
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
    print(f"[Pipeline] Starting background loop for {TICKER}")
    return run_loop(TICKER, on_signal=on_signal)