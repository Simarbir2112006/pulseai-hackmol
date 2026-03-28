import asyncio
import os
from datetime import datetime
from ai.anomaly.detector import detect, AnomalyResult
from ai.sentiment.finbert import score_batch
from ai.llm.groq_client import generate_brief
from data.fetcher_simar import fetch_all

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", 60))
BATCH_SIZE = 8


async def _fetch_data(ticker: str) -> list[dict]:
    return await fetch_all(ticker)


def _run_analysis(ticker: str, items: list[dict]) -> tuple[AnomalyResult, dict]:
    all_scored = []
    texts = [item["text"] for item in items]
    batches = [texts[i:i + BATCH_SIZE] for i in range(0, len(texts), BATCH_SIZE)]
    item_batches = [items[i:i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
    
    print(f"[Agent] {len(texts)} texts → {len(batches)} batches")
    for i, (batch, item_batch) in enumerate(zip(batches, item_batches)):
        print(f"[Agent] Scoring batch {i+1}/{len(batches)}...")
        scored = score_batch(batch)
        # merge source back in
        for s, original in zip(scored, item_batch):
            s["source"] = original.get("source", "unknown")
            s["timestamp"] = original.get("timestamp", "")
        all_scored.extend(scored)

    result = detect(all_scored)
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
    print(f"[Agent] Starting loop for {ticker} — polling every {POLL_INTERVAL}s")

    while True:
        try:
            print(f"[Agent] Fetching data for {ticker}...")
            texts = await _fetch_data(ticker)

            if not texts:
                print(f"[Agent] No data returned for {ticker}, skipping.")
            else:
                result, brief = _run_analysis(ticker, texts)
                signal = _make_signal(ticker, result, brief)

                if result.detected:
                    print(f"[Agent] ⚡ {result.signal_type} detected for {ticker}")
                    if on_signal:
                        await on_signal(signal)
                else:
                    print(f"[Agent] No anomaly (avg: {result.avg_sentiment:+.3f})")

        except Exception as e:
            print(f"[Agent] Error: {e}")

        await asyncio.sleep(POLL_INTERVAL)


async def run_once(ticker: str) -> dict:
    texts = await _fetch_data(ticker)
    if not texts:
        return {"ticker": ticker, "detected": False, "reason": "no data"}
    result, brief = _run_analysis(ticker, texts)
    return _make_signal(ticker, result, brief)