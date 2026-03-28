from ai.agent.loop import run_loop, run_once


def start_background_loop(ticker: str, on_signal=None):
    print(f"[Pipeline] Starting background loop for {ticker}")
    return run_loop(ticker, on_signal=on_signal)