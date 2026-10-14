"""
retrieval.py — Hybrid retrieval engine (Work Plan tasks 2.2 + 2.3).

Pipeline for every request:
  1. resolve_game()          exact -> case-insensitive -> normalized -> difflib
  2. dense search            Chroma cosine, metadata-filtered to the resolved game
  3. keyword search          BM25Okapi over the same game's chunks
  4. RRF fusion              Reciprocal Rank Fusion (k=60), mechanic boost
  5. evidence check          insufficient_evidence flag for the "tutor doesn't know" path

Everything is loaded once at startup (see RetrievalEngine) — queries are then
pure CPU lookups plus one embed call.
"""

from __future__ import annotations

import difflib
import json
import pickle
import re
import sys
from collections import defaultdict
from pathlib import Path

RAG_DIR = Path(__file__).resolve().parents[1]

# ingest.py lives in scripts/ — make the import work regardless of how the
# server is launched (uvicorn, gunicorn, tests)
SCRIPTS_DIR = RAG_DIR / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
from ingest import COLLECTION_NAME, tokenize  # reuse identical tokenization

CHROMA_DIR = RAG_DIR / "knowledge" / "index" / "chroma"
BM25_PATH = RAG_DIR / "knowledge" / "index" / "bm25.pkl"
CHUNKS_PATH = RAG_DIR / "knowledge" / "index" / "chunks.json"

DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RRF_K = 60
# dense cosine distance above this on the top hit = weak evidence.
# Tuned empirically: relevant rule questions measure 0.33–0.66, clearly
# off-topic questions 0.65–1.05. Phase 3 eval will re-tune.
MAX_TOP_DISTANCE = 0.75
MECHANIC_BOOST = 1.3  # multiplier for chunks matching focus_mechanics


class GameNotResolved(Exception):
    """Raised internally when the requested game is unknown to the KB."""


class RetrievalEngine:
    def __init__(self, embed_model_name: str = DEFAULT_EMBED_MODEL):
        import chromadb
        from rank_bm25 import BM25Okapi  # noqa: F401  (unpickled from bm25.pkl)
        from sentence_transformers import SentenceTransformer

        data = json.load(open(CHUNKS_PATH, encoding="utf-8"))
        self.chunks: dict[str, dict] = {c["id"]: c for c in data["chunks"]}
        self.embed_model_name = data.get("embed_model", embed_model_name)

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.collection = client.get_collection(COLLECTION_NAME)

        payload = pickle.load(open(BM25_PATH, "rb"))
        self.bm25_ids: list[str] = payload["ids"]
        self.bm25 = payload["bm25"]

        # per-game chunk pools + supported game list
        self.ids_by_game: dict[str, list[int]] = defaultdict(list)
        for i, cid in enumerate(self.bm25_ids):
            self.ids_by_game[self.chunks[cid]["game"]].append(i)
        self.games: dict[str, dict] = {}
        for cid, c in self.chunks.items():
            g = self.games.setdefault(c["game"], {
                "name": c["game"], "bgg_id": c.get("bgg_id"),
                "bgg_url": c["source"]["url"], "has_curated_rules": False,
            })
            if c["layer"] == "curated_rules":
                g["has_curated_rules"] = True
                if c["source"]["url"]:
                    g["bgg_url"] = c["source"]["url"]

        print(f"[retrieval] loading embed model: {self.embed_model_name}")
        self.model = SentenceTransformer(self.embed_model_name)
        print(f"[retrieval] ready: {len(self.chunks)} chunks, "
              f"{len(self.games)} games, chroma={self.collection.count()} vectors")

    # ---------- game resolution (2.2) ----------

    @staticmethod
    def _normalize(name: str) -> str:
        return re.sub(r"[^a-z0-9]", "", name.lower())

    def resolve_game(self, name: str) -> str | None:
        """exact -> case-insensitive -> normalized -> substring -> fuzzy."""
        if name in self.games:
            return name
        lowered = {g.lower(): g for g in self.games}
        if name.lower() in lowered:
            return lowered[name.lower()]
        norm = self._normalize(name)
        norm_map = {self._normalize(g): g for g in self.games}
        if norm in norm_map:
            return norm_map[norm]
        # substring: 'the settlers of catan' contains 'catan'; longest name wins
        contained = [g for n, g in norm_map.items() if n and n in norm]
        if contained:
            return max(contained, key=lambda g: len(self._normalize(g)))
        matches = difflib.get_close_matches(norm, list(norm_map), n=1, cutoff=0.8)
        return norm_map[matches[0]] if matches else None

    # ---------- search arms ----------

    def _dense(self, query: str, game: str, n: int) -> list[tuple[str, float]]:
        """Chroma cosine search filtered to one game; [(id, distance), ...]."""
        emb = self.model.encode([query], normalize_embeddings=True)[0].tolist()
        res = self.collection.query(
            query_embeddings=[emb], n_results=n, where={"game": game},
        )
        return list(zip(res["ids"][0], res["distances"][0]))

    def _keyword(self, query: str, game: str, n: int) -> list[tuple[str, float]]:
        """BM25 restricted to the game's chunk pool; [(id, score), ...]."""
        pool = set(self.ids_by_game[game])
        scores = self.bm25.get_scores(tokenize(query))
        ranked = sorted(pool, key=lambda i: -scores[i])[:n]
        return [(self.bm25_ids[i], scores[i]) for i in ranked if scores[i] > 0]

    # ---------- fused retrieval (2.2) ----------

    def retrieve(self, game: str, query: str,
                 focus_mechanics: list[str] | None = None, k: int = 6,
                 mode: str = "hybrid") -> dict:
        """mode: 'keyword' | 'vector' | 'hybrid' (BM25+dense fused via RRF)."""
        assert mode in ("keyword", "vector", "hybrid")
        focus = set(focus_mechanics or [])
        resolved = self.resolve_game(game)
        if resolved is None:
            return {"passages": [], "game_resolved": None,
                    "insufficient_evidence": True, "retrieval_mode": mode}

        pool_size = len(self.ids_by_game[resolved])
        n = min(max(k * 2, 8), pool_size)  # fetch extra for fusion headroom
        dense_hits = self._dense(query, resolved, n) if mode in ("vector", "hybrid") else []
        kw_hits = self._keyword(query, resolved, n) if mode in ("keyword", "hybrid") else []
        rankings = [r for r in (dense_hits, kw_hits) if r]

        # RRF fusion
        fused: dict[str, float] = defaultdict(float)
        for ranking in rankings:
            for rank, (cid, _) in enumerate(ranking):
                fused[cid] += 1.0 / (RRF_K + rank + 1)
        if not fused:
            return {"passages": [], "game_resolved": resolved,
                    "insufficient_evidence": True, "retrieval_mode": mode}

        # recommender hand-off: focus_mechanics must GUARANTEE the matching
        # mechanic cards are in the candidate pool, even if neither retriever
        # ranked them — inject them at the current best fused score.
        if focus:
            top_fused = max(fused.values(), default=0.0)
            for cid, chunk in self.chunks.items():
                if chunk["game"] == resolved and chunk.get("mechanic") in focus:
                    fused[cid] = max(fused[cid], top_fused)

        max_rrf = len(rankings) / (RRF_K + 1)  # best possible: rank 1 in all lists

        # mechanic boost on top of the injected/organic score; focus chunks
        # also sort strictly above non-focus chunks on score ties
        focus_ids = {cid for cid, c in self.chunks.items()
                     if c["game"] == resolved and c.get("mechanic") in focus}
        scored = []
        for cid, s in fused.items():
            chunk = self.chunks[cid]
            score = min(1.0, (s / max_rrf) * (MECHANIC_BOOST if chunk.get("mechanic") in focus else 1.0))
            scored.append((cid, round(score, 4)))
        scored.sort(key=lambda t: (t[0] not in focus_ids, -t[1]))
        scored = scored[:k]

        # ---------- evidence check (2.3) ----------
        top_distance = dense_hits[0][1] if dense_hits else 1.0
        insufficient = top_distance > MAX_TOP_DISTANCE

        passages = [self._to_passage(cid, score) for cid, score in scored]
        return {"passages": passages, "game_resolved": resolved,
                "insufficient_evidence": insufficient, "retrieval_mode": mode}

    def _to_passage(self, cid: str, score: float) -> dict:
        c = self.chunks[cid]
        return {
            "game": c["game"], "section": c["section"], "layer": c["layer"],
            "mechanic": c.get("mechanic"), "text": c["text"], "score": score,
            "source": {"title": c["source"]["title"], "url": c["source"]["url"]},
        }
