"""FastAPI app for the tutor backend (port 8002).

Endpoints (frontend contract — see frontend/README.md):
  POST /lesson       {known_games, target_game, user_level, learning_goal}
  POST /ask          {known_games, target_game, question}
  POST /visual       animation plan  → {id, status}
  GET  /visual/{id}  → {id, status, video_url?, error?}
  GET  /health       → {status, model, ...}
  /media/*.mp4       rendered Manim videos
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import animation, jobs, lesson as pipeline
from .config import AMD_MODEL, MEDIA_DIR, MissingAPIKeyError
from .llm import LLMError

app = FastAPI(title="Personalized AI Board-Game Tutor — backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


class LessonRequest(BaseModel):
    known_games: list[str] = Field(min_length=1)
    target_game: str
    user_level: str = "beginner"
    learning_goal: str = ""


class AskRequest(BaseModel):
    known_games: list[str] = Field(min_length=1)
    target_game: str
    question: str


class AnimationStepIn(BaseModel):
    label: str
    caption: str
    duration: float | None = None
    highlight: list[str] | None = None


class VisualRequest(BaseModel):
    scene_type: str
    title: str = "How it works"
    steps: list[AnimationStepIn]


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "model": AMD_MODEL, "service": "tutor-backend"}


@app.post("/lesson")
def post_lesson(req: LessonRequest) -> dict:
    try:
        rec, context = pipeline.gather_context(
            req.known_games, req.target_game, req.learning_goal, None, req.user_level)
        lesson = pipeline.generate_lesson(rec, context)
        return pipeline.lesson_to_response(lesson, rec, context, req.user_level)
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (pipeline.PipelineError, LLMError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:  # lesson validation failed — never serve unvalidated output
        raise HTTPException(status_code=502, detail=f"Lesson validation failed: {exc}") from exc


@app.post("/ask")
def post_ask(req: AskRequest) -> dict:
    try:
        rec, context = pipeline.gather_context(
            req.known_games, req.target_game, "", req.question, "intermediate")
        lesson = pipeline.generate_lesson(rec, context)
        return pipeline.ask_to_response(lesson, context)
    except MissingAPIKeyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (pipeline.PipelineError, LLMError) as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=f"Answer validation failed: {exc}") from exc


@app.post("/visual")
def post_visual(req: VisualRequest) -> dict:
    try:
        return jobs.create(req.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid animation plan: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — renderer failures become job failures
        raise HTTPException(status_code=500, detail=f"Could not start render: {exc}") from exc


@app.get("/visual/{job_id}")
def get_visual(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown visual id")
    return job
