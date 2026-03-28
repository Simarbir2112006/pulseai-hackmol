import numpy as np
from dataclasses import dataclass, field
from typing import Literal

try:
    from sklearn.ensemble import IsolationForest
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[Anomaly] sklearn not found — Z-score only mode")


SignalType = Literal["positive_spike", "negative_spike", "neutral"]


@dataclass
class AnomalyResult:
    detected: bool
    signal_type: SignalType
    avg_sentiment: float
    flagged_items: list[dict] = field(default_factory=list)
    item_count: int = 0


def _zscore_detect(items: list[dict], scores: np.ndarray, threshold: float = 1.2) -> list[dict]:
    if scores.std() == 0:
        return []
    zs = (scores - scores.mean()) / scores.std()
    return [
        {**items[i], "z_score": round(float(zs[i]), 3)}
        for i in range(len(items))
        if abs(zs[i]) > threshold
    ]


def _isoforest_detect(items: list[dict], scores: np.ndarray, contamination: float = 0.2) -> list[dict]:
    if not SKLEARN_AVAILABLE or len(scores) < 5:
        return []
    preds = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=50
    ).fit_predict(scores.reshape(-1, 1))
    return [items[i] for i in range(len(items)) if preds[i] == -1]


def detect(items: list[dict], z_threshold: float = 1.2, contamination: float = 0.2) -> AnomalyResult:
    if not items:
        return AnomalyResult(detected=False, signal_type="neutral", avg_sentiment=0.0)

    scores = np.array([float(item.get("score", 0.0)) for item in items])
    avg = float(round(scores.mean(), 4))

    z_flags = _zscore_detect(items, scores, z_threshold)
    if_flags = _isoforest_detect(items, scores, contamination)

    flagged = z_flags + [f for f in if_flags if f not in z_flags]
    detected = bool(flagged)

    signal_type: SignalType = "neutral"
    if detected:
        flag_avg = np.mean([f.get("score", 0.0) for f in flagged])
        signal_type = "negative_spike" if flag_avg < 0 else "positive_spike"

    return AnomalyResult(
        detected=detected,
        signal_type=signal_type,
        avg_sentiment=avg,
        flagged_items=flagged,
        item_count=len(items),
    )