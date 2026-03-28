from fastapi import APIRouter, Request
from backend.services.ai_service import get_latest_signal

router = APIRouter()

@router.get("/latest")
async def latest_signal(request: Request):
    """
    Returns the latest TSLA signal from the background loop.
    Falls back to on-demand analysis if loop hasn't fired yet.
    """
    signal = getattr(request.app.state, "latest_signal", {})
    if not signal:
        signal = get_latest_signal()
    return signal

@router.get("/history")
async def signal_history(request: Request):
    """Returns all signals detected since startup."""
    history = getattr(request.app.state, "signal_history", [])
    return {"signals": history, "count": len(history)}

@router.get("/health")
async def health():
    return {"status": "ok"}