from ai.agent.loop import run_once

async def get_latest_signal(ticker: str) -> dict:
    return await run_once(ticker)