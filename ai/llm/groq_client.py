import os
import requests
from ai.anomaly.detector import AnomalyResult

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama3-8b-8192"

SYSTEM_PROMPT = """You are a financial assistant helping everyday users understand market news.
Your goal is to explain what's happening and gently guide the user on what it could mean for them — without giving direct financial advice.

Rules:
* Use very simple, clear language.
* Do NOT give direct instructions like "buy now" or "sell immediately".
* Instead, suggest what a careful user might consider doing.
* Base everything ONLY on the headline and signal.
* Do NOT add outside information or guess missing details.
* If unclear, say: "The exact reason is not fully clear from the headline."
* Keep it short and easy to read (max ~120 words).

Guidelines:
* Explain what happened in plain English.
* Explain why it matters.
* Link it to the signal (BUY = positive momentum, SELL = negative pressure).
* Gently suggest a possible mindset (e.g., "may be worth watching", "could be a cautious moment").

Output format:
Summary: (1–2 simple sentences)
Why it matters: (simple explanation)
What this could mean for you: (gentle, indirect guidance — no commands)"""


USER_PROMPT_TEMPLATE = """Explain this news in simple terms and what it could mean for a regular user:
Headline: "{headline}"
Signal: {signal}"""


def _get_top_headline(result: AnomalyResult) -> str:
    """Pick the most extreme flagged item to use as the main headline."""
    if not result.flagged_items:
        return ""
    return min(result.flagged_items, key=lambda x: x.get("score", 0))["text"] \
        if result.signal_type == "negative_spike" \
        else max(result.flagged_items, key=lambda x: x.get("score", 0))["text"]


def _parse_response(content: str) -> dict:
    """Parse the plain-text structured response into a dict."""
    result = {"summary": "", "why_it_matters": "", "what_this_means": ""}
    
    lines = content.strip().splitlines()
    current_key = None
    buffer = []

    for line in lines:
        line = line.strip()
        if line.lower().startswith("summary:"):
            current_key = "summary"
            buffer = [line.split(":", 1)[-1].strip()]
        elif line.lower().startswith("why it matters:"):
            if current_key:
                result[current_key] = " ".join(buffer).strip()
            current_key = "why_it_matters"
            buffer = [line.split(":", 1)[-1].strip()]
        elif line.lower().startswith("what this could mean"):
            if current_key:
                result[current_key] = " ".join(buffer).strip()
            current_key = "what_this_means"
            buffer = [line.split(":", 1)[-1].strip()]
        elif line and current_key:
            buffer.append(line)

    if current_key and buffer:
        result[current_key] = " ".join(buffer).strip()

    return result


def generate_brief(ticker: str, result: AnomalyResult) -> dict:
    """
    Takes a ticker and AnomalyResult, returns a parsed brief dict.
    Only call this when result.detected is True.
    """
    if not result.detected:
        return {}

    headline = _get_top_headline(result)
    signal = "BUY" if result.signal_type == "positive_spike" else "SELL"
    user_prompt = USER_PROMPT_TEMPLATE.format(headline=headline, signal=signal)

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
                "temperature": 0.4,
                "max_tokens": 300,
            },
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        parsed = _parse_response(content)

        # attach metadata
        parsed["ticker"] = ticker
        parsed["signal"] = signal
        parsed["headline"] = headline
        parsed["avg_sentiment"] = result.avg_sentiment

        return parsed

    except Exception as e:
        print(f"[Groq] Error: {e}")
        return {
            "ticker": ticker,
            "signal": signal,
            "headline": headline,
            "summary": "Brief generation failed. Please review the flagged headlines manually.",
            "why_it_matters": "The exact reason is not fully clear from the headline.",
            "what_this_means": "This could be a cautious moment to keep an eye on this stock.",
            "avg_sentiment": result.avg_sentiment,
        }