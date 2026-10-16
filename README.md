# Personalized AI Board-Game Tutor

An AI tutor that learns which board games you already know, then teaches a new
game by connecting its mechanics to games you're familiar with — with
rule-grounded citations, personalized comparisons, a short quiz, and a Manim
animation that visually demonstrates the mechanic.

This repository integrates five team workstreams into **one system booted with
one command**:

```
                         ┌──────────────────────────────┐
                         │  Frontend (React + Vite)     │  http://localhost:5173
                         └──────┬───────────────────────┘
                                │
                 ┌──────────────▼───────────────┐
                 │  Tutor backend  (server/)    │  http://127.0.0.1:8002
                 │  /lesson /ask /visual        │
                 └──┬──────────┬──────────┬─────┘
                    │          │          │
        ┌───────────▼──┐  ┌────▼─────────▼───┐
        │ Recommendation│  │  AMD Token Factory│   LLM inference
        │ :8001         │  │  (RADEON_API_KEY) │
        └───────┬───────┘  └────────▲──────────┘
                │                   │
        ┌───────▼───────┐   evidence│
        │ RAG service   │───────────┘
        │ :8100         │
        └───────┬───────┘
                │
     recommendation/data/games.json  (shared game knowledge:
      mechanics metadata + rule fact cards + curated rules)
```

## What each service does

| Service | Port | Source | Role |
|---|---|---|---|
| **Frontend** | 5173 | `frontend/` | React dashboard: pick known games + a target game, view the lesson, step-through animation / Manim video, quiz, follow-up questions, system health page. Falls back to demo data if a service is down. |
| **Tutor backend** | 8002 | `server/` (new) | Orchestrates everything: calls recommendation + RAG, builds the grounded prompt (from `tutor/prompts.py`), calls the LLM on AMD, validates the lesson schema, generates the animation plan, renders Manim videos. |
| **Recommendation** | 8001 | `recommendation/` | Ranks the player's known games per target-game mechanic (explainable similarity scores). |
| **RAG** | 8100 | `RAG/` | Hybrid retrieval (ChromaDB + BM25 + RRF) over rule fact cards and curated rules, with citations and an `insufficient_evidence` flag. |

Shared data: `recommendation/data/games.json` (10 curated games) is the single
source of game knowledge — used by recommendation, RAG, and the tutor backend.

## Setup (once)

Requirements: **Linux**, **any Python 3.13 environment**, **Node 20+**, **ffmpeg**, git.

```bash
# 1. Create a Python 3.13 environment with the dependencies
#    (any 3.13 venv/conda env works — this is just the simplest way)
python3.13 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
#    If manim's build fails: sudo apt install libcairo2-dev libpango1.0-dev pkg-config ffmpeg

# 2. Put your AMD API key in .env (never commit it)
cp .env.example .env
nano .env                     # set RADEON_API_KEY=...  (required!)

# 3. Frontend dependencies (or just let main.py do it)
cd frontend && npm install && cd ..
```

That's it. `main.py` installs Python deps, builds the RAG index on first run,
and boots everything.

## Run

With a Python 3.13 environment active (or repo-local `.venv` present):

```bash
python main.py
# explicit interpreter also works: PYTHON_BIN=/path/to/python3.13 python main.py
```

`main.py` picks the interpreter in this order: `$PYTHON_BIN` → repo-local
`.venv/bin/python` → legacy pyenv env `AMD-Hackathon-ACT-III` → the interpreter
running the launcher (must be 3.13).

You'll see:

```
  Frontend (UI)        →  http://localhost:5173
  Tutor backend        →  http://127.0.0.1:8002  (docs at /docs)
  Recommendation       →  http://127.0.0.1:8001  (docs at /docs)
  RAG                  →  http://127.0.0.1:8100  (docs at /docs)
  Logs                 →  logs/*.log      Press Ctrl+C to stop.
```

Open **http://localhost:5173**, pick the games you know (e.g. Monopoly, Chess),
pick a target game (e.g. Catan), and learn.

Useful flags:

```bash
python main.py --skip-deps       # don't run pip install
python main.py --rebuild-index   # force-rebuild the RAG index (after editing games.json / curated rules)
python main.py --no-frontend     # services only
python main.py --check           # boot + run one end-to-end lesson as a smoke test
```

## Configuration (`.env`)

| Variable | Default | Meaning |
|---|---|---|
| `RADEON_API_KEY` | *(required)* | AMD Token Factory key. The system **refuses to run without it** — no silent fallbacks. |
| `AMD_BASE_URL` | `https://developer.amd.com.cn/radeon/api/v1` | AMD OpenAI-compatible endpoint. |
| `AMD_MODEL` | `Gemma-4-31B-IT` | Exact model ID. List live IDs: `python -m tutor.run --list-models`. |
| `RECOMMEND_URL` / `RAG_URL` | `http://127.0.0.1:8001` / `.../8100` | Upstream service URLs used by the tutor backend. |

Frontend knobs live in `frontend/.env.example` (`VITE_API_URL`,
`VITE_RECOMMEND_URL`, `VITE_RAG_URL`, `VITE_DEMO_FALLBACK`, `VITE_TIMEOUT_MS`);
`main.py` injects the right defaults when it starts the dev server.

## How a lesson is produced

1. **Frontend** sends `{known_games, target_game, user_level, learning_goal}` to `POST /lesson`.
2. **Tutor backend** asks **recommendation** for per-mechanic rankings of the
   player's known games, then asks **RAG** for rule evidence for the target
   game (focused on those mechanics) *and* for the best known games.
3. The context (recommendations + cited evidence) is assembled with
   `tutor/prompts.py` and sent to the **LLM on AMD Token Factory**.
4. The response is **schema-validated** (`tutor.prompts.validate_lesson`) —
   citations, targets, comparisons and quiz answers are checked against the
   evidence; invalid output is never served.
5. If retrieval says `insufficient_evidence`, the tutor says so instead of
   inventing rules (no LLM call is made).
6. A second LLM call authors the **animation plan** — structured JSON only,
   strictly whitelisted (scene type + step captions + allowed highlight ids),
   never executable code. It is personalized: steps may reference games you
   know ("Just like in Monopoly, ...").
7. `POST /visual` renders the plan through **fixed Manim templates**
   (`server/scenes.py`) to an MP4; the frontend polls `GET /visual/{id}` and
   offers a **Manim video** tab next to its built-in SVG step-through. If
   rendering fails, the step-through remains (graceful fallback).
8. **Follow-up questions** (`POST /ask`) go through the same grounded pipeline
   in question mode.

## API summary (tutor backend, port 8002)

| Endpoint | Body | Returns |
|---|---|---|
| `POST /lesson` | `{known_games, target_game, user_level, learning_goal}` | lesson title, summary, sections (+source ids), comparisons, sources, quiz, animation plan, warnings |
| `POST /ask` | `{known_games, target_game, question}` | `{answer, sources, insufficient_evidence}` |
| `POST /visual` | animation plan JSON | `{id, status}` |
| `GET /visual/{id}` | — | `{id, status: queued\|rendering\|done\|failed, video_url?, error?}` |
| `GET /health` | — | `{status, model, service}` |
| `/media/*.mp4` | — | rendered Manim videos |

Interactive docs: `http://127.0.0.1:8002/docs` (same for the other services).

## Adding a game

1. Add it to `recommendation/data/games.json` (mechanics, `bgg_id`/`bgg_url`,
   `key_mechanics_explained`).
2. Optionally add a curated rule file in `RAG/knowledge/curated_rules/`.
3. `python main.py --rebuild-index`.
4. Optionally add a Manim scene template in `server/scenes.py` + register the
   scene type and highlight ids in `server/animation.py` (the frontend SVG
   step-through can be extended in `frontend/src` the same way).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `RADEON_API_KEY is not set` | Put the key in `.env` at the repo root and re-run. |
| `No Python 3.13 interpreter found` | `python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt`, or set `PYTHON_BIN`. |
| `pip install failed` (manim) | `sudo apt install libcairo2-dev libpango1.0-dev pkg-config ffmpeg` |
| Lesson returns HTTP 502 | Check `logs/tutor-backend.log`; usually the AMD endpoint (rate limit → wait for `Retry-After`, wrong `AMD_MODEL`). |
| Lesson returns HTTP 503 | API key missing — see above. |
| RAG unhealthy | First boot downloads the MiniLM embedding model (needs internet). Check `logs/rag.log`. |
| Video render `failed` | The UI still shows the SVG step-through. Check `logs/tutor-backend.log` for the Manim error. |
| Port already in use | `pkill -f uvicorn` then re-run. |

## Repo layout

```
├── main.py                  ← ONE-COMMAND LAUNCHER (finds any Python 3.13 env)
├── requirements.txt         ← shared Python deps (one venv)
├── .env.example             ← copy to .env, add RADEON_API_KEY
├── server/                  ← tutor backend (NEW: orchestrator + Manim renderer)
│   ├── main.py              FastAPI: /lesson /ask /visual /health
│   ├── lesson.py            recommend → RAG → prompt → LLM → validate → frontend contract
│   ├── animation.py         LLM-authored animation plans (validated, whitelisted)
│   ├── scenes.py            fixed Manim templates (4 scene types)
│   ├── renderer.py / jobs.py  MP4 rendering + job queue
│   └── llm.py / config.py   AMD Token Factory client / .env config
├── recommendation/          ← Role 3: similarity + metadata (FastAPI :8001)
├── RAG/                     ← Role 2: hybrid retrieval with citations (FastAPI :8100)
├── tutor/                   ← Role 4: prompts, grounding contract, lesson validation (library)
├── frontend/                ← Role 6: React dashboard (:5173)
├── aatam/                   ← historical (its Manim ideas live on in server/scenes.py)
└── llm/                     ← historical scratch, unused
```

Integration notes and task status: see `progress.md`.
