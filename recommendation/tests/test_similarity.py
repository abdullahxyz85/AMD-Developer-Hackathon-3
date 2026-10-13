"""
tests/test_similarity.py — Unit tests for the similarity scoring functions.
Run with: pytest recommendation/tests/
"""

import pytest
from recommendation.game_metadata import catalog
from recommendation.similarity import (
    jaccard_similarity,
    key_differences,
    per_mechanic_best,
    rank_known_games,
    shared_mechanics,
    weighted_similarity,
)


# ── helpers ─────────────────────────────────────────────────────────────────

def game(name: str):
    g = catalog.get(name)
    assert g is not None, f"Game '{name}' not found in catalog"
    return g


# ── jaccard_similarity ───────────────────────────────────────────────────────

def test_jaccard_identical_sets():
    assert jaccard_similarity({"a", "b"}, {"a", "b"}) == 1.0


def test_jaccard_disjoint_sets():
    assert jaccard_similarity({"a"}, {"b"}) == 0.0


def test_jaccard_partial_overlap():
    score = jaccard_similarity({"a", "b", "c"}, {"b", "c", "d"})
    # intersection = {b,c} = 2, union = {a,b,c,d} = 4  →  0.5
    assert score == pytest.approx(0.5)


def test_jaccard_empty_sets():
    assert jaccard_similarity(set(), set()) == 0.0


# ── weighted_similarity ───────────────────────────────────────────────────────

def test_monopoly_catan_scores_higher_than_chess_catan():
    """Monopoly shares more of Catan's primary mechanics than Chess does."""
    monopoly = game("Monopoly")
    chess = game("Chess")
    catan = game("Catan")
    score_monopoly = weighted_similarity(monopoly, catan)
    score_chess = weighted_similarity(chess, catan)
    assert score_monopoly > score_chess, (
        f"Expected Monopoly ({score_monopoly:.3f}) > Chess ({score_chess:.3f}) for Catan"
    )


def test_weighted_similarity_range():
    """All scores must be in [0, 1]."""
    catan = game("Catan")
    for game_name in ["Monopoly", "Chess", "Poker", "Risk", "Checkers", "Uno", "Scrabble"]:
        score = weighted_similarity(game(game_name), catan)
        assert 0.0 <= score <= 1.0, f"{game_name} score {score} out of range"


def test_game_vs_itself_scores_one():
    """A game compared to itself should score 1.0."""
    catan = game("Catan")
    assert weighted_similarity(catan, catan) == pytest.approx(1.0)


# ── rank_known_games ─────────────────────────────────────────────────────────

def test_rank_returns_all_known_games():
    catan = game("Catan")
    known = [game("Monopoly"), game("Chess"), game("Poker")]
    ranked = rank_known_games(known, catan)
    assert len(ranked) == 3


def test_rank_descending_order():
    catan = game("Catan")
    known = [game("Monopoly"), game("Chess"), game("Poker"), game("Risk")]
    ranked = rank_known_games(known, catan)
    scores = [s for _, s in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_monopoly_top_for_catan():
    """Monopoly should be the top ranked game for Catan."""
    catan = game("Catan")
    known = [game("Monopoly"), game("Chess"), game("Checkers")]
    ranked = rank_known_games(known, catan)
    assert ranked[0][0].name == "Monopoly"


# ── per_mechanic_best ─────────────────────────────────────────────────────────

def test_per_mechanic_resource_management_catan():
    """Monopoly should be the best match for resource_management in Catan."""
    catan = game("Catan")
    known = [game("Monopoly"), game("Chess")]
    best, score = per_mechanic_best(known, catan, "resource_management")
    assert best is not None
    assert best.name == "Monopoly"
    assert score > 0.0


def test_per_mechanic_no_coverage():
    """If no known game covers the mechanic, return None and 0.0."""
    catan = game("Catan")
    # Chess and Checkers don't cover resource_management
    known = [game("Chess"), game("Checkers")]
    best, score = per_mechanic_best(known, catan, "resource_management")
    assert best is None
    assert score == 0.0


def test_per_mechanic_dice_rolling_catan():
    """Risk and Monopoly both cover dice_rolling; at least one should be returned."""
    catan = game("Catan")
    known = [game("Monopoly"), game("Risk"), game("Chess")]
    best, score = per_mechanic_best(known, catan, "dice_rolling")
    assert best is not None
    assert best.name in {"Monopoly", "Risk"}


# ── shared_mechanics ─────────────────────────────────────────────────────────

def test_shared_mechanics_monopoly_catan():
    mechanics = shared_mechanics(game("Monopoly"), game("Catan"))
    assert "resource_management" in mechanics
    assert "trading" in mechanics


def test_shared_mechanics_chess_catan_limited():
    """Chess and Catan share very few mechanics."""
    mechanics = shared_mechanics(game("Chess"), game("Catan"))
    assert "turn_based" in mechanics
    # Chess does NOT share resource_management with Catan
    assert "resource_management" not in mechanics


# ── key_differences ──────────────────────────────────────────────────────────

def test_key_differences_not_empty():
    """There should always be some differences between different games."""
    diffs = key_differences(game("Chess"), game("Catan"))
    assert len(diffs) > 0


def test_key_differences_identical_game_empty():
    """A game compared to itself should have no structural differences."""
    catan = game("Catan")
    # Structural diffs (player count, complexity) are same; mechanic diffs are empty
    diffs = key_differences(catan, catan)
    assert len(diffs) == 0

