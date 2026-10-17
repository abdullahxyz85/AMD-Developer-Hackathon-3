# Aatam — Frontend

React + TypeScript + Tailwind dashboard for Aatam, the personalized AI board-game tutor (AMD Developer Hackathon Act III).

It deploys and works with **no backend at all**: any service that isn't configured (or doesn't respond) is filled in by built-in demo data, so the hosted link never breaks during judging. Point it at the real services and every response is labelled **Live** or **Demo** in the UI.

## Pages

| Page | What it shows |
|---|---|
| **Learn a game** | Pick known games + a target game → personalized lesson with citations, step-through visual, familiar-game "bridges", sources, quiz, follow-up questions |
| **Compare players** | Player A vs Player B learning the same game, plus a "What changed" table — the personalization proof for the demo |
| **Game shelf** | Game × mechanic matrix from `games.json`; click a game for its rule cards |

## Quick start

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
npm run build        # production build in dist/
npm run preview      # serve the build on http://localhost:4173
```

Requires Node 20+.

## Connecting the services

Copy `.env.example` to `.env` and fill in whichever services are running. All are optional.

```bash
VITE_RECOMMEND_URL=http://localhost:8001   # uvicorn recommendation.api:app --port 8001   (from repo root)
VITE_RAG_URL=http://localhost:8100         # uvicorn app.main:app --port 8100            (from RAG/)
VITE_API_URL=                              # main tutor backend (LLM on AMD), when it exists
VITE_DEMO_FALLBACK=true                    # set false to surface errors instead of falling back
VITE_TIMEOUT_MS=60000
```

`VITE_*` values are baked in at build time: restart `npm run dev` (or rebuild) after changing them. When a call fails, the error names the service, path and address, e.g. `recommend /recommend (http://localhost:8001): unreachable (network or CORS)`.

Services must allow the site's origin via CORS. The RAG and recommendation services already allow all origins.

## How a lesson is produced

```
Frontend ──► Recommendation  POST /recommend         ranked familiar games per mechanic
         ├─► Tutor backend   POST /lesson            if VITE_API_URL is set (LLM writes the lesson)
         └─► RAG             POST /rag/retrieve      otherwise: fetch evidence using the recommender's
                                                     mechanics, and assemble the lesson in the browser
                                                     from retrieved passages only (nothing invented)
```

Follow-up questions use `POST /ask` if the tutor backend exists, otherwise RAG passages directly. If retrieval reports `insufficient_evidence`, the tutor says it doesn't know.

## API contract the frontend expects

All types live in `src/api/types.ts` — they mirror `recommendation/schemas.py` and `RAG/app/schemas.py`. The tutor backend should return:

```jsonc
// POST /lesson   body: { known_games, target_game, user_level, learning_goal }
{
  "lesson_title": "Catan, explained through Monopoly and Chess",
  "short_summary": "...",
  "sections":    [{ "key": "objective", "title": "...", "body": "**bold** allowed", "source_ids": [0] }],
  "comparisons": [{ "familiar_game": "Monopoly", "shared_mechanic": "Trading", "key_difference": "...", "why_it_helps": "...", "score": 0.78 }],
  "sources":     [{ "title": "Catan — BoardGameGeek", "url": "https://...", "section": "mechanic: Trading" }],
  "quiz":        [{ "question": "...", "options": ["a","b","c"], "correct_index": 1, "explanation": "..." }],
  "animation_plan": { "scene_type": "dice_production", "title": "...", "steps": [{ "label": "Roll", "caption": "...", "duration": 2.5, "highlight": ["dice"] }] },
  "warnings": []
}

// POST /ask      body: { known_games, target_game, question }
{ "answer": "...", "sources": [ ... ], "insufficient_evidence": false }

// POST /visual   body: animation_plan  →  { "id": "abc", "status": "queued" }
// GET  /visual/{id}                    →  { "id": "abc", "status": "done", "video_url": "/media/abc.mp4" }
// GET  /health                         →  { "status": "ok", "model": "..." }
```

Missing or malformed fields are defaulted, never crash the page.

## Visuals

`animation_plan` is treated as untrusted data. Only these `scene_type`s map to built-in SVG templates; anything else falls back to plain step cards:

| scene_type | Game | Highlight ids |
|---|---|---|
| `dice_production` | Catan | `dice`, `hex-8`, `hex-6`, `settlements`, `robber` |
| `route_claim` | Ticket to Ride | `hand`, `route`, `trains`, `score` |
| `deck_cycle` | Dominion | `hand`, `action`, `supply`, `discard`, `deck` |
| `step_cards` | any | — |

If `POST /visual` returns a job and it finishes with a `video_url`, the player offers a **Manim video** tab next to the step-through. If rendering fails or there's no renderer, the step-through is shown.

## Deploying

The build is a static site (`dist/`). Routing uses `#/page` hashes, so it works on any static host.

- **Vercel:** import the repo, set *Root Directory* to `frontend`. `vercel.json` handles the rest. Add `VITE_*` env vars in project settings.
- **Netlify:** set *Base directory* to `frontend`. `netlify.toml` handles the rest.
- **Docker:**
  ```bash
  docker build -t bgt-frontend --build-arg VITE_RAG_URL=https://rag.example.com .
  docker run -p 8080:80 bgt-frontend
  ```
- **Anything else:** `npm run build` and upload `dist/`.

## Project layout

```
src/
  api/        types.ts (contracts), config.ts (endpoints), client.ts (fetch + fallback + request log)
  demo/       offline versions: catalog, recommender (exact port of recommendation/), keyword RAG, lesson + quiz
  data/       games.json — snapshot of recommendation/data/games.json
  components/ Lesson, VisualPlayer, ProfilePicker, ui
  views/      LearnView, CompareView, GamesView
```

`src/data/games.json` is a copy. After editing the catalog, refresh it:

```bash
cp ../recommendation/data/games.json src/data/games.json
```

## Known limitations

- Demo-mode lessons only contain what's in `games.json`; setup rules aren't there yet, so the lesson says so and points to the rulebook.
- Quiz questions in demo mode are a fixed set per game (3 each), written from `games.json`.
