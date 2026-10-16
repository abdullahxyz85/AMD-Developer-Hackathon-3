"""
Phase 2 tests: endpoint behavior + hybrid retrieval correctness.

Run (from RAG/):  pytest tests/test_api.py -v
The model + index load once per session (~5-10s).
"""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    """TestClient with lifespan (loads the RetrievalEngine once)."""
    with TestClient(app) as c:
        yield c


# ---------- /health and /rag/games ----------

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["games"] == 10
    assert body["chunks"] == 144


def test_root_lists_endpoints(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "/rag/retrieve" in r.json()["endpoints"]


def test_list_games(client):
    r = client.get("/rag/games")
    assert r.status_code == 200
    games = {g["name"]: g for g in r.json()}
    assert set(games) == {"Catan", "Monopoly", "Chess", "Ticket to Ride",
                          "Dominion", "Uno", "Poker", "Risk", "Scrabble", "Checkers"}
    # all ten games have curated rules, with BGG citations
    assert games["Catan"]["has_curated_rules"] is True
    assert games["Catan"]["bgg_id"] == 13
    assert games["Catan"]["bgg_url"] == "https://boardgamegeek.com/boardgame/13/catan"
    assert games["Uno"]["has_curated_rules"] is True
    assert games["Uno"]["bgg_id"] == 2223


# ---------- /rag/retrieve: happy paths ----------

def test_retrieve_curated_game(client):
    r = client.post("/rag/retrieve", json={
        "game": "Catan", "query": "how does trading with the bank work", "k": 5,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["game_resolved"] == "Catan"
    assert body["insufficient_evidence"] is False
    assert 1 <= len(body["passages"]) <= 5
    top = body["passages"][0]
    assert top["game"] == "Catan"
    assert 0.0 <= top["score"] <= 1.0
    # every passage carries a citation
    for p in body["passages"]:
        assert p["source"]["url"].startswith("https://")
        assert p["text"].strip()
    # the trading mechanic card should surface prominently
    texts = " ".join(p["text"] for p in body["passages"]).lower()
    assert "trade" in texts


def test_retrieve_scores_sorted_desc(client):
    r = client.post("/rag/retrieve", json={
        "game": "Chess", "query": "when can I castle", "k": 6,
    })
    scores = [p["score"] for p in r.json()["passages"]]
    assert scores == sorted(scores, reverse=True)
    assert "castling" in " ".join(p["text"] for p in r.json()["passages"]).lower()


def test_k_is_respected(client):
    r = client.post("/rag/retrieve", json={
        "game": "Monopoly", "query": "rent and houses", "k": 2,
    })
    assert len(r.json()["passages"]) <= 2


def test_focus_mechanics_boost(client):
    """Without focus: mixed results. With focus=['trading']: the trading
    card must rank first — this is the recommender hand-off path."""
    base = client.post("/rag/retrieve", json={
        "game": "Catan", "query": "getting resources and building", "k": 6,
    }).json()
    focused = client.post("/rag/retrieve", json={
        "game": "Catan", "query": "getting resources and building",
        "focus_mechanics": ["trading"], "k": 6,
    }).json()
    assert focused["passages"][0]["mechanic"] == "trading"
    # the boost must actually change the top result vs the unfocused ranking
    assert focused["passages"][0] != base["passages"][0]
    # and scores must be higher with the boost applied
    assert focused["passages"][0]["score"] >= base["passages"][0]["score"]


# ---------- /rag/retrieve: game resolution ----------

@pytest.mark.parametrize("variant", ["catan", "CATAN", "the settlers of catan"])
def test_fuzzy_game_resolution(client, variant):
    r = client.post("/rag/retrieve", json={"game": variant, "query": "trading"})
    assert r.status_code == 200
    assert r.json()["game_resolved"] == "Catan"


def test_unknown_game_insufficient_evidence(client):
    r = client.post("/rag/retrieve", json={
        "game": "Splendor", "query": "how many starting cards",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["game_resolved"] is None
    assert body["passages"] == []
    assert body["insufficient_evidence"] is True  # tutor must say "I don't know"


def test_off_topic_query_flags_insufficient(client):
    """Known game, but question about something absent from the KB."""
    r = client.post("/rag/retrieve", json={
        "game": "Chess", "query": "quantum flux capacitor calibration settings",
    })
    assert r.status_code == 200
    assert r.json()["insufficient_evidence"] is True


# ---------- contract validation ----------

def test_request_validation_errors(client):
    assert client.post("/rag/retrieve", json={"query": "no game"}).status_code == 422
    assert client.post("/rag/retrieve", json={"game": "Catan", "query": ""}).status_code == 422
    assert client.post("/rag/retrieve", json={
        "game": "Catan", "query": "x", "k": 999  # k > 20
    }).status_code == 422


def test_response_schema_fields(client):
    r = client.post("/rag/retrieve", json={"game": "Risk", "query": "reinforcement phase"})
    p = r.json()["passages"][0]
    assert set(p) == {"game", "section", "layer", "mechanic", "text", "score", "source"}
    assert set(p["source"]) == {"title", "url"}
    assert p["layer"] in ("fact_card", "curated_rules")
