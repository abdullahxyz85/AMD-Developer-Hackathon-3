"""
Smoke tests: retrieval quality on the three demo-critical questions
(verified manually during task 1.6 — see WORKPLAN.md 1.6).

These guard against silent index regressions (bad embeds, broken BM25,
missing chunks) between now and the Phase 2 service.

Run:  pytest tests/test_smoke.py -v
"""

import pytest

from conftest import bm25_query, dense_query

# (query, expected chunk id) — both retrievers should surface these
CASES = [
    ("how do I get out of jail in Monopoly", "Monopoly:rule:exceptions"),
    ("castling the king and rook", "Chess:rule:exceptions"),
    ("trading resources with the bank in Catan", "Catan:mechanic:trading"),
]


@pytest.mark.parametrize("query,expected", CASES)
def test_dense_retrieval_top3(chroma_collection, embed_model, query, expected):
    results = dense_query(chroma_collection, embed_model, query, n=3)
    ids = [cid for cid, _ in results]
    assert expected in ids, f"dense miss: {query!r} -> {ids}"


@pytest.mark.parametrize("query,expected", CASES)
def test_bm25_retrieval_top3(bm25_index, query, expected):
    results = bm25_query(bm25_index, query, n=3)
    ids = [cid for cid, _ in results]
    assert expected in ids, f"bm25 miss: {query!r} -> {ids}"


def test_game_metadata_filter(chroma_collection, embed_model):
    """where={'game': ...} must restrict results to that game."""
    results = dense_query(chroma_collection, embed_model, "king and rook",
                          n=5, where={"game": "Chess"})
    assert results, "filter returned nothing"
    for cid, _ in results:
        assert cid.startswith("Chess:"), f"filter leak: {cid}"


def test_retrievers_return_aligned_ids(bm25_index, chunk_store):
    """BM25 index ids must resolve in the chunk store (citations need it)."""
    for cid, _ in bm25_query(bm25_index, "robber in Catan", n=5):
        assert cid in chunk_store, f"bm25 id not in chunk store: {cid}"
