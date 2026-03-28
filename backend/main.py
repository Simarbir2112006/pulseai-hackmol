import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routes.signals import router
from ai.pipeline import start_background_loop

app = FastAPI(title="PulseAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/signals")

@app.on_event("startup")
async def startup():
    asyncio.create_task(start_background_loop(on_signal=push_signal))

async def push_signal(signal: dict):
    # stores latest signal in memory so /latest can serve it
    app.state.latest_signal = signal
    app.state.signal_history.append(signal)

@app.on_event("startup")
async def init_state():
    app.state.latest_signal = {}
    app.state.signal_history = []