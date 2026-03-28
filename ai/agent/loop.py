import asyncio
import os
import json
from datetime import datetime
from ai.anomaly.detector import detect, AnomalyResult
from ai.sentiment.finbert import score_batch
from ai.llm.groq_client import generate_brief

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 60))  # seconds


async def _fetch_data(ticker: str) -> list[str]:
    path = os.path.join(os.path.dirname(_file_), "../../data/TSLA_pipeline_output.json")
    with open(path) as f:
        items = json.load(f)
    return [item["text"] for item in items]


def _run_analysis(ticker: str, texts: list[str]) -> tuple[AnomalyResult, dict]:
    scored = score_batch(texts)
    result = detect(scored)
    brief = generate_brief(ticker, result) if result.detected else {}
    return result, brief


def _make_signal(ticker: str, result: AnomalyResult, brief: dict) -> dict:
    return {
        "ticker": ticker,
        "timestamp": datetime.utcnow().isoformat(),
        "detected": result.detected,
        "signal_type": result.signal_type,
        "avg_sentiment": result.avg_sentiment,
        "item_count": result.item_count,
        "flagged_items": result.flagged_items,
        "brief": brief,
    }


async def run_loop(ticker: str, on_signal=None):
    """
    Main agent loop. Runs forever, polling every POLL_INTERVAL seconds.

    on_signal: optional async callback — backend passes its push function here
                so signals get sent to FastAPI the moment they're detected.

    Usage:
        asyncio.run(run_loop("AAPL"))
        asyncio.run(run_loop("AAPL", on_signal=my_push_fn))
    """
    print(f"[Agent] Starting loop for {ticker} — polling every {POLL_INTERVAL}s")

    while True:
        try:
            print(f"[Agent] Fetching data for {ticker}...")
            texts = await _fetch_data(ticker)

            if not texts:
                print(f"[Agent] No data returned for {ticker}, skipping cycle.")
            else:
                result, brief = _run_analysis(ticker, texts)
                signal = _make_signal(ticker, result, brief)

                if result.detected:
                    print(f"[Agent] ⚡ Signal detected — {result.signal_type} for {ticker}")
                    if on_signal:
                        await on_signal(signal)
                else:
                    print(f"[Agent] No anomaly for {ticker} (avg sentiment: {result.avg_sentiment:+.3f})")

        except Exception as e:
            print(f"[Agent] Error in loop cycle: {e}")
            # don't crash the loop — log and continue

        await asyncio.sleep(POLL_INTERVAL)


async def run_once(ticker: str) -> dict:
    """
    Single run — no loop. Useful for on-demand API calls from FastAPI.
    Returns the signal dict directly.
    """
    texts = await _fetch_data(ticker)
    if not texts:
        return {"ticker": ticker, "detected": False, "reason": "no data"}
    result, brief = _run_analysis(ticker, texts)
    return _make_signal(ticker, result, brief)