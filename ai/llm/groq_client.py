import os
import requests
from dotenv import load_dotenv
from ai.anomaly.detector import AnomalyResult

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"

SYSTEM_PROMPT = """You are PulseAI, a financial intelligence assistant for everyday retail investors.
Your job is to explain what is happening in the market right now for a specific stock, based ONLY on the headlines and data provided to you.

Rules:
* Use very simple, clear language — explain like the user has no finance background.
* Do NOT give direct instructions like "buy now" or "sell immediately".
* Do NOT add any outside information, news, or context not present in the headlines given.
* If something is unclear from the headlines, say: "The exact reason is not fully clear from available data."
* Keep total response under 150 words.
* Base your confidence on how many sources agree with each other.

Output format — use EXACTLY these labels:
Summary: (1-2 sentences on what is happening right now)
Why it matters: (1-2 sentences on why this affects the stock)
What this could mean for you: (gentle suggestion, no commands)
Confidence: (High / Medium / Low — based on how many sources agree)"""


def _build_user_prompt(
    ticker: str,
    signal: str,
    flagged_items: list[dict],
    prediction: dict,
    avg_sentiment: float,
) -> str:
    # Build headlines section grouped by source
    source_groups = {}
    for item in flagged_items:
        src = item.get("source", "unknown")
        if src not in source_groups:
            source_groups[src] = []
        source_groups[src].append(
            f'  [{item.get("score", 0):+.2f}] {item.get("text", "")}'
        )

    headlines_text = ""
    for src, lines in source_groups.items():
        headlines_text += f"\n{src.upper()}:\n" + "\n".join(lines)

    # Correlation between sentiment and price
    sentiment_direction = "positive" if avg_sentiment > 0 else "negative"
    price_direction = prediction.get("direction", "unknown")
    pct = prediction.get("pct_change_tomorrow", 0)
    current = prediction.get("current_price", "?")
    predicted = prediction.get("predicted_tomorrow", "?")

    correlation = "ALIGNED" if sentiment_direction == price_direction else "CONFLICTING"

    return f"""Analyze the following market data for {ticker} and write a brief for a retail investor.

SIGNAL: {signal}
SENTIMENT: {sentiment_direction} (avg score: {avg_sentiment:+.3f})
PRICE MODEL: predicts {price_direction} movement ({pct:+.1f}% tomorrow)
CURRENT PRICE: ${current} → PREDICTED TOMORROW: ${predicted}
SIGNAL ALIGNMENT: Sentiment and price model are {correlation}

FLAGGED HEADLINES (these triggered the anomaly):
{headlines_text}

Write the brief now based ONLY on the above data."""


def _parse_response(content: str) -> dict:
    result = {
        "summary": "",
        "why_it_matters": "",
        "what_this_means": "",
        "confidence": "medium"
    }

    lines = content.strip().splitlines()
    current_key = None
    buffer = []

    KEY_MAP = {
        "summary:": "summary",
        "why it matters:": "why_it_matters",
        "what this could mean": "what_this_means",
        "confidence:": "confidence",
    }

    for line in lines:
        stripped = line.strip()
        matched = False
        for prefix, key in KEY_MAP.items():
            if stripped.lower().startswith(prefix):
                if current_key and buffer:
                    result[current_key] = " ".join(buffer).strip()
                current_key = key
                buffer = [stripped.split(":", 1)[-1].strip()]
                matched = True
                break
        if not matched and stripped and current_key:
            buffer.append(stripped)

    if current_key and buffer:
        result[current_key] = " ".join(buffer).strip()

    return result


def generate_brief(
    ticker: str,
    result: AnomalyResult,
    prediction: dict = None,
) -> dict:
    if not result.detected:
        return {}

    if prediction is None:
        prediction = {}

    signal = "BUY" if result.signal_type == "positive_spike" else "SELL"

    user_prompt = _build_user_prompt(
        ticker=ticker,
        signal=signal,
        flagged_items=result.flagged_items,
        prediction=prediction,
        avg_sentiment=result.avg_sentiment,
    )

    try:
        response = requests.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
                "max_tokens": 350,
            },
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = _parse_response(content)

        parsed["ticker"] = ticker
        parsed["signal"] = signal
        parsed["avg_sentiment"] = result.avg_sentiment
        parsed["signal_alignment"] = (
            "aligned" if (
                (result.avg_sentiment > 0 and prediction.get("direction") == "up") or
                (result.avg_sentiment < 0 and prediction.get("direction") == "down")
            ) else "conflicting"
        )
        parsed["sources_used"] = list({
            item.get("source", "unknown")
            for item in result.flagged_items
        })

        return parsed

    except Exception as e:
        print(f"[Groq] Error: {e}")
        return {
            "ticker": ticker,
            "signal": signal,
            "summary": "Brief generation failed. Review flagged headlines manually.",
            "why_it_matters": "The exact reason is not fully clear from available data.",
            "what_this_means": "This could be a cautious moment to monitor this stock closely.",
            "confidence": "low",
            "avg_sentiment": result.avg_sentiment,
            "signal_alignment": "unknown",
            "sources_used": [],
        }