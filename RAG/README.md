# RAG / Game Knowledge Engine

Retrieval service for the Personalized AI Board-Game Tutor. Retrieves rule-grounded
evidence passages **with citations** for a target game + question, so the tutor LLM
never has to invent rules. Part of Role 2 (RAG / Game Knowledge Engineer) — see
`WORKPLAN.md` for the full plan and decision log.

## Quick start

```bash
# 1. Environment (pyenv: AMD-Hackathon-ACT-III, Python 3.13)
# Create your virtual environment
pip install -r requirements.txt

# 2. Build the knowledge index (only needed once, or after editing knowledge/)
python3 scripts/load_games.py     # games.json -> fact cards (Layer A)
python3 scripts/ingest.py         # fact cards + curated rules -> Chroma + BM25

# 3. Run the service (standalone, port 8100)
uvicorn app.main:app --host 0.0.0.0 --port 8100

# 4. Run tests (29 tests, ~10s)
pytest tests/ -q

# 5. Re-run the retrieval evaluation
python3 eval/evaluate.py          # writes eval/RESULTS.md
```

## Query interface (for the prompt engineer / backend)

### `POST /rag/retrieve`

```json
{
  "game": "Catan",                        // fuzzy-matched: "catan", "settlers of catan" both work
  "query": "what happens when I roll a 7",
  "focus_mechanics": ["trading"],         // optional: mechanic tags from RecommendationResponse.per_mechanic
  "k": 6                                  // max passages (1-20, default 6)
}
```

Response:

```json
{
  "passages": [{
      "game": "Catan",
      "section": "mechanic",              // objective|setup|turn_structure|core_mechanics|exceptions|mechanic|overview|notes...
      "layer": "fact_card",               // "curated_rules" = hand-curated rule section, "fact_card" = from games.json
      "mechanic": "dice_rolling",         // mechanic tag, or null
      "text": "Catan — Dice Rolling: ...",
      "score": 0.99,                      // normalized fused relevance
      "source": {"title": "Catan — BoardGameGeek", "url": "https://..."}
  }],
  "game_resolved": "Catan",               // null if the game is unknown to the KB
  "insufficient_evidence": false,          // true => tutor should say "I don't know"
  "retrieval_mode": "hybrid"
}
```

**Grounding contract for lesson generation:**
1. Every claim in the lesson must trace to a passage in `passages`; cite via `source` + `section`.
2. If `insufficient_evidence == true`, the tutor must decline gracefully ("I don't have reliable rules for that").
   Note the flag reliably catches unknown games and nonsensical queries; for plausible-but-absent
   topics the tutor itself must check the passages before answering (see `eval/RESULTS.md` conclusion).
3. `focus_mechanics` (from the recommender) guarantees the requested mechanic's rule card is
   returned and ranked first — always pass it when personalizing lessons.

### Other endpoints
- `GET /rag/games` — supported games with `bgg_id`/`bgg_url` and `has_curated_rules` flag
- `GET /health` — liveness + index stats
- Interactive docs: `http://localhost:8100/docs`

## Knowledge base

Two layers (see WORKPLAN.md §1):

| Layer | Source | Content |
|---|---|---|
| A — fact cards (74 chunks) | `recommendation/data/games.json` | per-game overview, mechanics inventory, per-mechanic rule cards, notes |
| B — curated rules (70 chunks) | `knowledge/curated_rules/*.json` | objective, components, setup, turn_structure, core_mechanics, exceptions, examples for **all 10 games**: Catan, Monopoly, Chess, Ticket to Ride, Dominion, Uno, Poker, Risk, Scrabble, Checkers |

All chunks carry `bgg_url` citations. Rule text is original summary — we link to sources,
we do not republish rulebooks.

**To add a game:** add it to `recommendation/data/games.json` (with `bgg_id`/`bgg_url` and
`key_mechanics_explained`), optionally add a curated file in `knowledge/curated_rules/`,
then re-run `scripts/ingest.py`. Tests in `tests/test_ingest.py` enforce primary-mechanic
coverage automatically.

## Stack

Python 3.13 · FastAPI · ChromaDB (cosine, metadata-filtered) ·
sentence-transformers `all-MiniLM-L6-v2` (384-dim, CPU) · rank-bm25 · Reciprocal Rank Fusion.
Embeddings run on CPU by design for demo reliability (decision D5: ROCm/ONNX variant is a stretch).

## Evaluation snapshot

See `eval/RESULTS.md` (33 questions). Hybrid RRF beats keyword-only and vector-only:
**hit@3 0.84, MRR 0.63** vs 0.72/0.56 (keyword) and 0.68/0.53 (vector), with perfect
unknown-game detection; curated rules cover all 10 games (70 chunks).
Known limitations are documented there honestly — most importantly, absent-topic detection
in-KB is delegated to prompt-level grounding.
