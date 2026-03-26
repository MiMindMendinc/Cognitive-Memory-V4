"""FastAPI server for grok-dream-memory."""
from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Any, Optional

# ensure src is on the path when run as `python -m api.server`
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from dream_memory.config import Config, LANES
from dream_memory.memory import MemoryStore
from dream_memory.dreamer import dream_cycle

app = FastAPI(
    title="grok-dream-memory",
    description="Local AI memory with dream consolidation.",
    version="1.0.0",
)

_config = Config.from_env()
_store = MemoryStore(_config)


# ── Request / Response models ──────────────────────────────────────────────

class AddRequest(BaseModel):
    text: str
    lane: str = "episodic"
    metadata: Optional[dict[str, Any]] = None


class AddResponse(BaseModel):
    id: str
    lane: str


class RecallRequest(BaseModel):
    query: str
    lane: Optional[str] = None
    top_k: int = 5


class RecallResponse(BaseModel):
    results: list[dict[str, Any]]


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> HTMLResponse:
    html_path = Path(__file__).parent / "dashboard.html"
    return HTMLResponse(content=html_path.read_text())


@app.post("/add", response_model=AddResponse)
async def add_memory(req: AddRequest) -> AddResponse:
    if req.lane not in LANES:
        raise HTTPException(status_code=400, detail=f"Invalid lane. Choose from: {LANES}")
    mem_id = _store.store(req.text, req.lane, req.metadata)
    return AddResponse(id=mem_id, lane=req.lane)


@app.post("/recall", response_model=RecallResponse)
async def recall_memory(req: RecallRequest) -> RecallResponse:
    if req.lane and req.lane not in LANES:
        raise HTTPException(status_code=400, detail=f"Invalid lane. Choose from: {LANES}")
    results = _store.recall(req.query, lane=req.lane, top_k=req.top_k)
    return RecallResponse(results=results)


@app.post("/dream")
async def run_dream() -> dict:
    return dream_cycle(store=_store, config=_config)


@app.get("/show")
async def show_memories(lane: Optional[str] = None) -> dict:
    if lane and lane not in LANES:
        raise HTTPException(status_code=400, detail=f"Invalid lane. Choose from: {LANES}")
    memories = _store.all_memories(lane=lane)
    return {"count": len(memories), "memories": memories}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=_config.api_host, port=_config.api_port)
