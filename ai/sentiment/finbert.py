import os
import requests

HF_TOKEN = os.getenv("HF_TOKEN", "")
API_URL = "https://api-inference.huggingface.co/models/ProsusAI/finbert"
HEADERS = {"Authorization": f"Bearer {HF_TOKEN}"}


def score_text(text: str) -> float:
    """Single headline → float (-1 to +1). Positive minus negative prob."""
    try:
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json={"inputs": text},
            timeout=10,
        )
        response.raise_for_status()
        result = response.json()[0]
        scores = {item["label"]: item["score"] for item in result}
        return round(scores["positive"] - scores["negative"], 4)
    except Exception as e:
        print(f"[FinBERT] Error: {e}")
        return 0.0  # neutral fallback


def score_batch(texts: list[str]) -> list[dict]:
    """List of texts → list of {text, score} dicts."""
    return [{"text": t, "score": score_text(t)} for t in texts]