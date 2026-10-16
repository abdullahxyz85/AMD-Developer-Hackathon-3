"""In-memory visual render job manager (POST /visual → GET /visual/{id})."""
from __future__ import annotations

import threading
import traceback
import uuid

from . import animation, renderer
from .config import MEDIA_DIR

_LOCK = threading.Lock()
_JOBS: dict[str, dict] = {}


def create(plan: dict) -> dict:
    """Validate the plan and start a background render. Returns job status."""
    validated = animation.validate_plan(plan)  # raises ValueError on bad input
    job_id = uuid.uuid4().hex[:12]
    job = {"id": job_id, "status": "queued", "video_url": None, "error": None,
           "scene_type": validated["scene_type"], "title": validated["title"]}
    with _LOCK:
        _JOBS[job_id] = job
    threading.Thread(target=_run, args=(job, validated), daemon=True).start()
    return public(job)


def get(job_id: str) -> dict | None:
    with _LOCK:
        job = _JOBS.get(job_id)
        return public(job) if job else None


def public(job: dict) -> dict:
    return {k: job[k] for k in ("id", "status", "video_url", "error")}


def _run(job: dict, plan: dict) -> None:
    job["status"] = "rendering"
    out_path = MEDIA_DIR / f"{job['id']}.mp4"
    try:
        renderer.render(plan, out_path)
        job["status"] = "done"
        job["video_url"] = f"/media/{job['id']}.mp4"
    except Exception as exc:  # noqa: BLE001 — job status must always settle
        job["status"] = "failed"
        job["error"] = f"{exc}"[:500] or traceback.format_exc()[-500:]
