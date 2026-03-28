import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://router.huggingface.co/hf-inference/models/ProsusAI/finbert"
HEADERS = {"Authorization": f"Bearer {os.getenv('HF_TOKEN', '')}"}


def score_text(text: str) -> float:
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
        return round(scores.get("positive", 0.0) - scores.get("negative", 0.0), 4)
    except Exception as e:
        print(f"[FinBERT] Error: {e}")
        return 0.0


def score_batch(texts: list[str]) -> list[dict]:
    return [{"text": t, "score": score_text(t)} for t in texts]