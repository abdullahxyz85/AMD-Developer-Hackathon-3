"""
main.py — RAG standalone service (Work Plan tasks 2.4 + 2.5).

Endpoints:
  POST /rag/retrieve   evidence passages + citations for one game + question
  GET  /rag/games      supported games + mechanic/rule coverage
  GET  /health         liveness + index stats
  GET  /               service info

Run (from RAG/):
  uvicorn app.main:app --host 0.0.0.0 --port 8100
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.retrieval import RetrievalEngine
from app.schemas import (GameInfo, RetrievalRequest, RetrievalResponse)

engine: RetrievalEngine | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = RetrievalEngine()
    yield
    engine = None


app = FastAPI(
    title="Board-Game Tutor — RAG Service",
    description="Retrieves rule-grounded evidence passages with citations "
                "for the personalized board-game tutor.",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo: frontend origin set at deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "rag",
        "version": app.version,
        "endpoints": ["/rag/retrieve", "/rag/games", "/health"],
    }


@app.get("/health")
def health():
    return {
        "status": "ok" if engine else "starting",
        "chunks": len(engine.chunks) if engine else 0,
        "games": len(engine.games) if engine else 0,
        "embed_model": engine.embed_model_name if engine else None,
    }


@app.get("/rag/games")
def list_games() -> list[GameInfo]:
    return [GameInfo(**g) for g in sorted(engine.games.values(), key=lambda g: g["name"])]


@app.post("/rag/retrieve", response_model=RetrievalResponse)
def retrieve(req: RetrievalRequest) -> RetrievalResponse:
    result = engine.retrieve(
        game=req.game, query=req.query,
        focus_mechanics=req.focus_mechanics, k=req.k,
    )
    return RetrievalResponse(**result)
