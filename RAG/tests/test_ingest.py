"""
Index integrity tests: validate the artifacts ingest.py produced
(chunks.json, bm25.pkl, chroma collection) without any model loading.

Run:  pytest tests/test_ingest.py -v
"""

import json
from pathlib import Path

import pytest

from conftest import BM25_PATH, CHROMA_DIR, CHUNKS_PATH

RAG_DIR = Path(__file__).resolve().parents[1]


def test_index_artifacts_exist():
    assert CHROMA_DIR.is_dir(), f"missing chroma dir: {CHROMA_DIR}"
    assert BM25_PATH.is_file(), f"missing bm25 index: {BM25_PATH}"
    assert CHUNKS_PATH.is_file(), f"missing chunk store: {CHUNKS_PATH}"


def test_chunk_store_schema(chunk_store):
    required = {"id", "game", "section", "mechanic", "layer", "text",
                "bgg_id", "source"}
    for cid, c in chunk_store.items():
        missing = required - set(c)
        assert not missing, f"{cid}: missing fields {missing}"
        assert c["text"].strip(), f"{cid}: empty text"
        assert c["layer"] in ("fact_card", "curated_rules"), f"{cid}: bad layer"
        assert c["source"].get("url", "").startswith("https://"), f"{cid}: bad url"


def test_chunk_ids_unique(chunk_store):
    data = json.load(open(CHUNKS_PATH, encoding="utf-8"))
    ids = [c["id"] for c in data["chunks"]]
    assert len(ids) == len(set(ids)), "duplicate chunk ids"


def test_expected_games_and_counts(chunk_store):
    expected_games = {"Catan", "Monopoly", "Chess", "Ticket to Ride", "Dominion",
                      "Uno", "Poker", "Risk", "Scrabble", "Checkers"}
    games = {c["game"] for c in chunk_store.values()}
    assert games == expected_games
    # Layer B curated rules: 7 sections x 10 games
    curated = [c for c in chunk_store.values() if c["layer"] == "curated_rules"]
    assert len(curated) == 7 * len(expected_games)
    curated_games = {c["game"] for c in curated}
    assert curated_games == expected_games


def test_primary_mechanic_coverage(chunk_store):
    """Every primary mechanic of every game must have a rule card (Layer A)."""
    catalog = json.load(
        open(RAG_DIR.parent / "recommendation" / "data" / "games.json",
             encoding="utf-8"))
    rule_cards = {c["game"]: set() for c in chunk_store.values()}
    for c in chunk_store.values():
        if c["section"] == "mechanic" and c["mechanic"]:
            rule_cards.setdefault(c["game"], set()).add(c["mechanic"])
    for game, gd in catalog["games"].items():
        missing = set(gd["primary_mechanics"]) - rule_cards.get(game, set())
        assert not missing, f"{game}: primary mechanics without rule cards: {missing}"


def test_chroma_count_matches_chunk_store(chroma_collection, chunk_store):
    assert chroma_collection.count() == len(chunk_store), \
        "chroma vector count != chunk store size"


def test_embed_model_recorded():
    data = json.load(open(CHUNKS_PATH, encoding="utf-8"))
    assert data["embed_model"] == "sentence-transformers/all-MiniLM-L6-v2"
