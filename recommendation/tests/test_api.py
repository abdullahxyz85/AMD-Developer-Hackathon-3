"""
tests/test_api.py — Tests for the FastAPI endpoints.
Uses TestClient (no real server needed).
Run with: pytest recommendation/tests/
"""

import pytest
from fastapi.testclient import TestClient

from recommendation.api import app

client = TestClient(app)


# ── POST /recommend ───────────────────────────────────────────────────────────

def test_recommend_valid_request():
    resp = client.post("/recommend", json={
        "known_games": ["Monopoly", "Chess"],
        "target_game": "Catan"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_game"] == "Catan"
    assert data["top_overall"] == "Monopoly"
    assert data["top_overall_score"] > 0
    assert isinstance(data["per_mechanic"], list)
    assert len(data["per_mechanic"]) > 0


def test_recommend_personalization_different_profiles():
    """Core requirement: two different profiles get different recommendations."""
    resp_a = client.post("/recommend", json={
        "known_games": ["Monopoly", "Chess"],
        "target_game": "Catan"
    })
    resp_b = client.post("/recommend", json={
        "known_games": ["Poker", "Checkers"],
        "target_game": "Catan"
    })
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    top_a = resp_a.json()["top_overall"]
    top_b = resp_b.json()["top_overall"]
    assert top_a != top_b


def test_recommend_unknown_target_returns_422():
    resp = client.post("/recommend", json={
        "known_games": ["Monopoly"],
        "target_game": "NonExistentGame9999"
    })
    assert resp.status_code == 422
    assert "not in the catalog" in resp.json()["detail"]


def test_recommend_unknown_known_game_returns_warning():
    resp = client.post("/recommend", json={
        "known_games": ["Monopoly", "FakeGame"],
        "target_game": "Catan"
    })
    assert resp.status_code == 200
    warnings = resp.json()["warnings"]
    assert any("FakeGame" in w for w in warnings)


def test_recommend_empty_known_games_rejected():
    """Empty known_games list should fail Pydantic validation."""
    resp = client.post("/recommend", json={
        "known_games": [],
        "target_game": "Catan"
    })
    assert resp.status_code == 422   # Pydantic min_length=1


def test_recommend_response_schema():
    """Validate every field in the response schema is present and typed correctly."""
    resp = client.post("/recommend", json={
        "known_games": ["Monopoly"],
        "target_game": "Catan"
    })
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data["target_game"], str)
    assert isinstance(data["player_known_games"], list)
    assert isinstance(data["top_overall"], str)
    assert isinstance(data["top_overall_score"], float)
    assert isinstance(data["per_mechanic"], list)
    assert isinstance(data["warnings"], list)

    for m in data["per_mechanic"]:
        assert "mechanic" in m
        assert "mechanic_label" in m
        assert "best_known_game" in m
        assert "shared_mechanics" in m
        assert "key_differences" in m
        assert "why_it_helps" in m
        assert "score" in m
        assert 0.0 <= m["score"] <= 1.0


def test_recommend_ticket_to_ride():
    resp = client.post("/recommend", json={
        "known_games": ["Scrabble", "Uno"],
        "target_game": "Ticket to Ride"
    })
    assert resp.status_code == 200
    assert resp.json()["target_game"] == "Ticket to Ride"


def test_recommend_dominion():
    resp = client.post("/recommend", json={
        "known_games": ["Poker", "Chess"],
        "target_game": "Dominion"
    })
    assert resp.status_code == 200
    assert resp.json()["target_game"] == "Dominion"


# ── GET /games ────────────────────────────────────────────────────────────────

def test_games_endpoint_returns_200():
    resp = client.get("/games")
    assert resp.status_code == 200


def test_games_endpoint_schema():
    resp = client.get("/games")
    data = resp.json()

    assert "supported_games" in data
    assert "mechanic_vocabulary" in data
    assert "target_games" in data
    assert "known_games" in data

    assert isinstance(data["supported_games"], list)
    assert isinstance(data["mechanic_vocabulary"], dict)
    assert isinstance(data["target_games"], list)
    assert isinstance(data["known_games"], list)


def test_games_endpoint_contains_mvp_games():
    resp = client.get("/games")
    names = [g["name"] for g in resp.json()["supported_games"]]

    for expected in ["Catan", "Monopoly", "Chess", "Ticket to Ride", "Dominion"]:
        assert expected in names, f"Expected '{expected}' in /games response"


def test_games_endpoint_target_games_list():
    resp = client.get("/games")
    targets = resp.json()["target_games"]
    assert "Catan" in targets
    assert "Ticket to Ride" in targets
    assert "Dominion" in targets


def test_games_endpoint_mechanic_vocabulary_not_empty():
    resp = client.get("/games")
    vocab = resp.json()["mechanic_vocabulary"]
    assert len(vocab) > 0
    # Check a few known tags
    assert "resource_management" in vocab
    assert "trading" in vocab


def test_games_endpoint_game_summary_fields():
    resp = client.get("/games")
    for game in resp.json()["supported_games"]:
        assert "name" in game
        assert "description" in game
        assert "game_type" in game
        assert "complexity" in game
        assert "player_count_min" in game
        assert "player_count_max" in game
        assert "primary_mechanics" in game
        assert "primary_mechanic_labels" in game
        assert "tags" in game

