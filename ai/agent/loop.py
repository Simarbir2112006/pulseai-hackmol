import asyncio
import os
from datetime import datetime
from anomaly.detector import detect, AnomalyResult
from sentiment.finbert import score_batch
from llm.groq_client import generate_brief

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 60))  # seconds


async def _fetch_data(ticker: str) -> list[str]:
    """
    Placeholder — Jaspreet's pipeline feeds this.
    Returns a list of raw text strings (headlines + reddit posts).
    Replace this with the actual import once data/ branch is merged.
    """
    # from data.fetcher import fetch_all
    # return await fetch_all(ticker)
    return []


def _run_analysis(ticker: str, texts: list[str]) -> tuple[AnomalyResult, dict]:
    """Score → detect → brief. Returns (AnomalyResult, brief dict)."""
    scored = score_batch(texts)
    result = detect(scored)
    brief = generate_brief(ticker, result) if result.detected else {}
    return result, brief


def _make_signal(ticker: str, result: AnomalyResult, brief: dict) -> dict:
    """Build the signal payload the backend stores and serves."""
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