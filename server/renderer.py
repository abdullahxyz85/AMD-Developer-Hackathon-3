"""Render a validated animation plan to MP4 with Manim.

The plan is treated as untrusted data: it is validated (server.animation) and
then injected into a temporary scene file as base64-encoded JSON. No LLM text
ever becomes Python; the scene classes in server.scenes are the only code that
runs.
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import animation
from .config import RENDER_TIMEOUT_S, ROOT

SCENE_FILE_TEMPLATE = """import base64
import json
import sys

sys.path.insert(0, {root!r})

from server.scenes import AnimationPlanScene, StepCardsScene

PLAN = json.loads(base64.b64decode({plan_b64!r}).decode("utf-8"))


class PlanScene({base_class}):
    def construct(self):
        self.perform(PLAN)
"""


def render(plan: dict, out_path: Path, *, timeout: float | None = None) -> Path:
    """Render plan to out_path (MP4). Raises RuntimeError on failure."""
    plan = animation.validate_plan(plan)  # defense in depth: never render unvalidated data
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    timeout = timeout if timeout is not None else RENDER_TIMEOUT_S

    base_class = "StepCardsScene" if plan["scene_type"] == "step_cards" else "AnimationPlanScene"
    scene_code = SCENE_FILE_TEMPLATE.format(
        root=str(ROOT),
        plan_b64=base64.b64encode(json.dumps(plan).encode("utf-8")).decode("ascii"),
        base_class=base_class,
    )

    with tempfile.TemporaryDirectory(prefix="tutor-render-") as tmp:
        tmp_dir = Path(tmp)
        scene_file = tmp_dir / "render_job.py"
        media_dir = tmp_dir / "media"
        scene_file.write_text(scene_code, encoding="utf-8")

        command = [
            sys.executable, "-m", "manim", "render", "-ql",
            "--media_dir", str(media_dir),
            str(scene_file), "PlanScene", "-o", "plan",
        ]
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        try:
            proc = subprocess.run(
                command, cwd=tmp_dir, env=env, timeout=timeout,
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Manim render timed out after {timeout:.0f}s") from exc
        if proc.returncode != 0:
            tail = "\n".join((proc.stderr or proc.stdout or "").splitlines()[-15:])
            raise RuntimeError(f"Manim render failed:\n{tail}")

        produced = list(media_dir.rglob("plan.mp4"))
        if not produced:
            raise RuntimeError(f"Manim produced no video: {(proc.stderr or '')[-400:]}")
        shutil.move(str(produced[0]), out_path)
    return out_path
