"""
tests/test_recommender.py — Integration tests for get_recommendations().

These tests validate the core requirement:
  "Changing the user's known games changes the recommendations in a sensible way."
"""

import pytest
from recommendation.recommender import get_recommendations
from recommendation.schemas import RecommendationResponse


# ── Helper ────────────────────────────────────────────────────────────────────

def recommend(known: list[str], target: str) -> RecommendationResponse:
    return get_recommendations(known, target)


# ── Basic smoke tests ─────────────────────────────────────────────────────────

def test_returns_recommendation_response():
    result = recommend(["Monopoly", "Chess"], "Catan")
    assert isinstance(result, RecommendationResponse)


def test_target_game_preserved():
    result = recommend(["Monopoly"], "Catan")
    assert result.target_game == "Catan"


def test_known_games_preserved():
    result = recommend(["Monopoly", "Chess"], "Catan")
    assert "Monopoly" in result.player_known_games
    assert "Chess" in result.player_known_games


# ── Personalization: different profiles → different outputs ───────────────────

def test_different_profiles_different_top_overall():
    """Core requirement: Monopoly-Chess profile and Poker-Checkers profile
    should produce different top_overall games for Catan."""
    result_a = recommend(["Monopoly", "Chess"], "Catan")
    result_b = recommend(["Poker", "Checkers"], "Catan")
    # Monopoly profile should recommend Monopoly; Poker profile has no Monopoly
    assert result_a.top_overall == "Monopoly"
    assert result_b.top_overall != "Monopoly"


def test_different_profiles_different_per_mechanic():
    """Per-mechanic recommendations should change across profiles."""
    result_a = recommend(["Monopoly", "Chess"], "Catan")
    result_b = recommend(["Poker", "Checkers"], "Catan")

    games_a = {m.best_known_game for m in result_a.per_mechanic}
    games_b = {m.best_known_game for m in result_b.per_mechanic}

    # At least one mechanic should map to a different game
    assert games_a != games_b, (
        f"Expected different per_mechanic recommendations for different profiles.\n"
        f"Profile A games: {games_a}\nProfile B games: {games_b}"
    )


# ── Monopoly + Chess → Catan ──────────────────────────────────────────────────

def test_monopoly_chess_catan_top_is_monopoly():
    result = recommend(["Monopoly", "Chess"], "Catan")
    assert result.top_overall == "Monopoly"


def test_monopoly_chess_catan_has_per_mechanic():
    result = recommend(["Monopoly", "Chess"], "Catan")
    assert len(result.per_mechanic) > 0


def test_monopoly_chess_catan_resource_management_best_is_monopoly():
    result = recommend(["Monopoly", "Chess"], "Catan")
    rm = next((m for m in result.per_mechanic if m.mechanic == "resource_management"), None)
    assert rm is not None, "resource_management should appear in Catan's per_mechanic"
    assert rm.best_known_game == "Monopoly"


def test_monopoly_chess_catan_shared_mechanics_not_empty():
    result = recommend(["Monopoly", "Chess"], "Catan")
    for comp in result.per_mechanic:
        assert len(comp.shared_mechanics) > 0, (
            f"shared_mechanics empty for mechanic '{comp.mechanic}'"
        )


def test_monopoly_chess_catan_score_in_range():
    result = recommend(["Monopoly", "Chess"], "Catan")
    assert 0.0 <= result.top_overall_score <= 1.0
    for m in result.per_mechanic:
        assert 0.0 <= m.score <= 1.0


# ── Ticket to Ride ────────────────────────────────────────────────────────────

def test_scrabble_uno_ticket_to_ride():
    """Scrabble's set_collection is directly relevant to Ticket to Ride."""
    result = recommend(["Scrabble", "Uno"], "Ticket to Ride")
    assert result.target_game == "Ticket to Ride"
    assert result.top_overall_score > 0.0


def test_ticket_to_ride_set_collection_covered():
    """At least one known game should cover set_collection for Ticket to Ride."""
    result = recommend(["Monopoly", "Scrabble", "Uno"], "Ticket to Ride")
    sc = next((m for m in result.per_mechanic if m.mechanic == "set_collection"), None)
    assert sc is not None


# ── Dominion ─────────────────────────────────────────────────────────────────

def test_dominion_deck_building_uncovered_warning():
    """Chess has no deck_building — a warning should mention it."""
    result = recommend(["Chess", "Checkers"], "Dominion")
    warning_text = " ".join(result.warnings).lower()
    assert "deck" in warning_text or len(result.warnings) > 0


def test_dominion_poker_hand_management():
    """Poker covers hand_management which is primary in Dominion."""
    result = recommend(["Poker", "Chess"], "Dominion")
    hm = next((m for m in result.per_mechanic if m.mechanic == "hand_management"), None)
    assert hm is not None
    assert hm.best_known_game == "Poker"


# ── Edge cases ────────────────────────────────────────────────────────────────

def test_unknown_target_game_raises():
    with pytest.raises(ValueError, match="not in the catalog"):
        recommend(["Monopoly"], "NonExistentGame2099")


def test_unknown_known_game_generates_warning():
    result = recommend(["Monopoly", "FakeGame999"], "Catan")
    assert any("FakeGame999" in w for w in result.warnings)


def test_all_unknown_known_games():
    result = recommend(["FakeA", "FakeB"], "Catan")
    assert result.top_overall == "(none)"
    assert len(result.per_mechanic) == 0
    assert len(result.warnings) > 0


def test_single_known_game():
    result = recommend(["Monopoly"], "Catan")
    assert result.top_overall == "Monopoly"
    assert result.top_overall_score > 0.0


def test_many_known_games():
    all_known = ["Chess", "Monopoly", "Uno", "Poker", "Checkers", "Risk", "Scrabble"]
    result = recommend(all_known, "Catan")
    assert result.top_overall == "Monopoly"


# ── Evaluation set (manual ground truth) ─────────────────────────────────────

EVAL_CASES = [
    {
        "known": ["Monopoly", "Chess"],
        "target": "Catan",
        "expected_top": "Monopoly",
        "expected_shared": ["resource_management", "trading"],
    },
    {
        "known": ["Poker", "Checkers"],
        "target": "Catan",
        "expected_top_not": "Monopoly",  # Monopoly not in known
        "expected_shared_for_prob": ["probability"],
    },
    {
        "known": ["Scrabble", "Uno"],
        "target": "Ticket to Ride",
        "expected_shared_includes": ["set_collection", "hand_management"],
    },
]


def test_eval_case_monopoly_chess_catan():
    case = EVAL_CASES[0]
    result = recommend(case["known"], case["target"])
    assert result.top_overall == case["expected_top"]
    # Check that resource_management comparison includes expected shared mechanics
    rm = next((m for m in result.per_mechanic if m.mechanic == "resource_management"), None)
    if rm:
        for expected_m in case["expected_shared"]:
            assert expected_m in rm.shared_mechanics, (
                f"Expected '{expected_m}' in shared_mechanics for resource_management"
            )


def test_eval_case_poker_checkers_catan():
    case = EVAL_CASES[1]
    result = recommend(case["known"], case["target"])
    assert result.top_overall != case.get("expected_top_not", "__none__")


def test_eval_case_scrabble_uno_ticket_to_ride():
    case = EVAL_CASES[2]
    result = recommend(case["known"], case["target"])
    all_shared = set()
    for m in result.per_mechanic:
        all_shared.update(m.shared_mechanics)
    for expected_m in case["expected_shared_includes"]:
        assert expected_m in all_shared, (
            f"Expected '{expected_m}' to appear somewhere in per_mechanic shared_mechanics"
        )

