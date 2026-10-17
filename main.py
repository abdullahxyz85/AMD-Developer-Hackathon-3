#!/usr/bin/env python3
"""One-command launcher for the Personalized AI Board-Game Tutor.

Boots, in order:
  1. a Python 3.13 environment with the deps installed (see venv_python())
  2. the RAG knowledge index      (only if not built yet, or --rebuild-index)
  3. recommendation service       http://127.0.0.1:8001
  4. RAG service                  http://127.0.0.1:8100
  5. tutor backend (this repo's server/)  http://127.0.0.1:8002
  6. frontend dev server          http://localhost:5173

Usage:
  python main.py                  # full boot
  python main.py --skip-deps      # don't run pip install
  python main.py --rebuild-index  # force RAG index rebuild
  python main.py --no-frontend    # services only
  python main.py --check          # boot, then run one end-to-end lesson
  python main.py --help

Requires: any Python 3.13 environment (auto-detected, or set PYTHON_BIN),
Node 20+, ffmpeg, and RADEON_API_KEY in .env (see .env.example).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_NAME = "AMD-Hackathon-ACT-III"  # legacy pyenv name, still supported as a fallback
SERVICES = {
    "recommendation": ("recommendation.api:app", 8001, ROOT),
    "rag": ("app.main:app", 8100, ROOT / "RAG"),
    "tutor-backend": ("server.main:app", 8002, ROOT),
}
LOG_DIR = ROOT / "logs"


def log(msg: str) -> None:
    print(f"\033[1;36m[boot]\033[0m {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"\033[1;33m[boot]\033[0m {msg}", flush=True)


def die(msg: str) -> None:
    print(f"\033[1;31m[boot] ERROR:\033[0m {msg}", flush=True)
    sys.exit(1)


def _check_version(python: Path) -> None:
    """The whole stack (manim, chromadb, sentence-transformers) targets 3.13."""
    out = subprocess.run([str(python), "-c", "import sys;print(sys.version_info[:2])"],
                         capture_output=True, text=True)
    try:
        major, minor = eval(out.stdout.strip())
    except Exception:  # noqa: BLE001
        die(f"Could not determine the Python version of {python}")
    if (major, minor) != (3, 13):
        die(f"{python} is Python {major}.{minor}; this project needs Python 3.13\n"
            f"  e.g.:  python3.13 -m venv .venv && pip install -r requirements.txt\n"
            f"  or point the launcher at your 3.13 binary:  PYTHON_BIN=/path/to/python3.13 python main.py")


def venv_python() -> Path:
    """Find a Python 3.13 interpreter for all services, in order of preference:

      1. PYTHON_BIN environment variable (explicit override)
      2. a repo-local .venv  (python3.13 -m venv .venv)
      3. the legacy pyenv virtualenv 'AMD-Hackathon-ACT-III'
      4. whatever interpreter is running this script (if it is 3.13)
    """
    candidates: list[Path] = []
    if os.environ.get("PYTHON_BIN"):
        candidates.append(Path(os.environ["PYTHON_BIN"]))
    candidates.append(ROOT / ".venv" / "bin" / "python")
    candidates.insert(1, ROOT / ".venv" / "Scripts" / "python.exe")
    pyenv_root = Path(os.environ.get("PYENV_ROOT", "~/.pyenv")).expanduser()
    candidates.append(pyenv_root / "versions" / VENV_NAME / "bin" / "python")
    candidates.append(Path(sys.executable))

    for candidate in candidates:
        if candidate.exists():
            _check_version(candidate)
            return candidate
    die("No Python 3.13 interpreter found.\n"
        "  Create one:  python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt\n"
        "  Or set PYTHON_BIN=/path/to/python3.13")


def ensure_env_file() -> None:
    env_file, example = ROOT / ".env", ROOT / ".env.example"
    if not env_file.exists():
        if example.exists():
            shutil.copy(example, env_file)
            warn("Created .env from .env.example — add your RADEON_API_KEY!")
        else:
            warn("No .env and no .env.example found.")
    key = ""
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.strip().startswith("RADEON_API_KEY="):
                key = line.split("=", 1)[1].strip()
                break
    if not key and not os.environ.get("RADEON_API_KEY"):
        die("RADEON_API_KEY is not set.\n"
            "  Put your AMD key in .env at the repository root:\n"
            "    RADEON_API_KEY=<your-key>\n"
            "  The tutor refuses to run without it (no silent fallbacks).")


def install_deps(python: Path, skip: bool) -> None:
    if skip:
        log("Skipping dependency install (--skip-deps)")
        return
    log("Installing Python dependencies (fast when already satisfied)...")
    proc = subprocess.run([str(python), "-m", "pip", "install", "-q", "-r",
                           str(ROOT / "requirements.txt")])
    if proc.returncode != 0:
        die("pip install failed. If manim's build failed, install system libs:\n"
            "  sudo apt install libcairo2-dev libpango1.0-dev pkg-config ffmpeg")


def ensure_rag_index(python: Path, rebuild: bool) -> None:
    chroma = ROOT / "RAG" / "knowledge" / "index" / "chroma"
    bm25 = ROOT / "RAG" / "knowledge" / "index" / "bm25.pkl"
    if chroma.exists() and bm25.exists() and not rebuild:
        log("RAG index found — skipping build (use --rebuild-index to rebuild)")
        return
    log("Building RAG knowledge index (games.json → fact cards → Chroma + BM25)...")
    for script in ("scripts/load_games.py", "scripts/ingest.py"):
        proc = subprocess.run([str(python), script], cwd=ROOT / "RAG")
        if proc.returncode != 0:
            die(f"RAG index build failed at {script} (see output above)")


def wait_healthy(name: str, port: int, timeout: float = 180.0) -> None:
    # recommendation has no /health; the frontend also probes it via /games
    path = "/games" if name == "recommendation" else "/health"
    url = f"http://127.0.0.1:{port}{path}"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                if resp.status == 200:
                    log(f"{name} is healthy on :{port}")
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1.0)
    die(f"{name} did not become healthy on :{port} within {timeout:.0f}s. "
        f"Check logs/{name}.log")


def start_services(python: Path) -> dict[str, subprocess.Popen]:
    LOG_DIR.mkdir(exist_ok=True)
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    procs: dict[str, subprocess.Popen] = {}
    for name, (app, port, cwd) in SERVICES.items():
        log_file = open(LOG_DIR / f"{name}.log", "w")
        log(f"Starting {name} on :{port}  (logs/{name}.log)")
        procs[name] = subprocess.Popen(
            [str(python), "-m", "uvicorn", app, "--host", "127.0.0.1", "--port", str(port)],
            cwd=cwd, env=env, stdout=log_file, stderr=subprocess.STDOUT)
    try:
        for name, (_, port, _) in SERVICES.items():
            wait_healthy(name, port)
    except SystemExit:
        stop(procs)
        raise
    return procs


def stop(procs: dict[str, subprocess.Popen]) -> None:
    for name, proc in procs.items():
        if proc.poll() is None:
            log(f"Stopping {name}...")
            proc.terminate()
    for proc in procs.values():
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def start_frontend() -> subprocess.Popen | None:
    npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
    if not shutil.which("node") or not npm:
        warn("Node/npm not found — skipping frontend. Install Node 20+ to use the UI.")
        return None
    frontend = ROOT / "frontend"
    if not (frontend / "node_modules").exists():
        log("Installing frontend dependencies (npm install)...")
        subprocess.run([npm, "install"], cwd=frontend, check=True)
    env = dict(os.environ,
               VITE_API_URL="http://localhost:8002",
               VITE_RECOMMEND_URL="http://localhost:8001",
               VITE_RAG_URL="http://localhost:8100",
               VITE_DEMO_FALLBACK="false")
    log_file = open(LOG_DIR / "frontend.log", "w")
    log("Starting frontend dev server on :5173  (logs/frontend.log)")
    return subprocess.Popen([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173", "--strictPort"], cwd=frontend, env=env,
                            stdout=log_file, stderr=subprocess.STDOUT)


def smoke_check() -> None:
    import json as _json

    payload = _json.dumps({"known_games": ["Monopoly", "Chess"], "target_game": "Catan",
                           "user_level": "beginner", "learning_goal": "understand the first turn"}
                          ).encode()
    request = urllib.request.Request("http://127.0.0.1:8002/lesson", data=payload,
                                     headers={"Content-Type": "application/json"})
    log("Smoke test: POST /lesson (Monopoly+Chess → Catan) — can take a minute...")
    with urllib.request.urlopen(request, timeout=600) as resp:
        lesson = _json.load(resp)
    print(_json.dumps({"lesson_title": lesson.get("lesson_title"),
                       "sections": len(lesson.get("sections", [])),
                       "comparisons": len(lesson.get("comparisons", [])),
                       "quiz": len(lesson.get("quiz", [])),
                       "animation_plan": (lesson.get("animation_plan") or {}).get("scene_type"),
                       "warnings": lesson.get("warnings")}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--skip-deps", action="store_true", help="skip pip install")
    parser.add_argument("--rebuild-index", action="store_true", help="force RAG index rebuild")
    parser.add_argument("--no-frontend", action="store_true", help="don't start the web UI")
    parser.add_argument("--check", action="store_true",
                        help="after boot, run one end-to-end lesson as a smoke test")
    args = parser.parse_args()

    log("Personalized AI Board-Game Tutor — booting")
    python = venv_python()
    log(f"Using Python: {python}")
    ensure_env_file()
    install_deps(python, args.skip_deps)
    ensure_rag_index(python, args.rebuild_index)

    frontend_proc = None
    procs = {}
    try:
        procs = start_services(python)
        if not args.no_frontend:
            frontend_proc = start_frontend()
            time.sleep(2)
        print()
        log("All services running:")
        print("  Frontend (UI)        →  http://localhost:5173")
        print("  Tutor backend        →  http://127.0.0.1:8002  (docs at /docs)")
        print("  Recommendation       →  http://127.0.0.1:8001  (docs at /docs)")
        print("  RAG                  →  http://127.0.0.1:8100  (docs at /docs)")
        print("  Logs                 →  logs/*.log      Press Ctrl+C to stop.")
        print()
        if args.check:
            smoke_check()
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    finally:
        if frontend_proc and frontend_proc.poll() is None:
            log("Stopping frontend...")
            frontend_proc.terminate()
        stop(procs)
        log("Bye.")


if __name__ == "__main__":
    main()
