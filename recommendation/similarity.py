"""
similarity.py — Core scoring logic for the recommendation engine.

Two scoring strategies:
  1. weighted_similarity(known, target)  →  float 0–1
     Overall similarity between two games, weighted by mechanic importance.

  2. per_mechanic_best(known_games, target, mechanic)  →  (GameRecord, float)
     For a single mechanic of the target game, find the best known-game match.
"""

from __future__ import annotations

from .game_metadata import GameRecord


def jaccard_similarity(set_a: set[str], set_b: set[str]) -> float:
    """Unweighted Jaccard similarity between two mechanic sets."""
    if not set_a and not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def weighted_similarity(known: GameRecord, target: GameRecord) -> float:
    """Compute weighted similarity of a known game vs. a target game.

    Weights each mechanic by its importance in the TARGET game:
      - primary in target  → weight 1.5
      - secondary in target → weight 1.0

    A mechanic contributes to the score only if it also appears in the
    known game (primary or secondary).

    Formula:
        score = Σ weight(m, target) * has(m, known)
                ─────────────────────────────────────
                Σ weight(m, target)   [over all target mechanics]

    Returns a float in [0, 1].
    """
    target_mechanics = target.all_mechanics
    if not target_mechanics:
        return 0.0

    total_weight = sum(target.mechanic_weight(m) for m in target_mechanics)
    if total_weight == 0:
        return 0.0

    matched_weight = sum(
        target.mechanic_weight(m)
        for m in target_mechanics
        if m in known.all_mechanics
    )

    return matched_weight / total_weight


def rank_known_games(
    known_games: list[GameRecord],
    target: GameRecord,
) -> list[tuple[GameRecord, float]]:
    """Rank known games by weighted similarity to the target game.

    Returns list of (GameRecord, score) sorted descending by score.
    """
    scored = [(g, weighted_similarity(g, target)) for g in known_games]
    return sorted(scored, key=lambda x: x[1], reverse=True)


def per_mechanic_best(
    known_games: list[GameRecord],
    target: GameRecord,
    mechanic: str,
) -> tuple[GameRecord | None, float]:
    """For a specific target-game mechanic, find the best known-game match.

    A known game "covers" the mechanic if it has it (primary or secondary).
    Among covering games, rank by overall weighted_similarity to break ties.

    Returns (best_game_or_None, score).
    """
    candidates = [g for g in known_games if mechanic in g.all_mechanics]
    if not candidates:
        return None, 0.0

    # Rank by overall similarity (higher = better general analogy)
    ranked = rank_known_games(candidates, target)
    best_game, best_score = ranked[0]
    return best_game, best_score


def shared_mechanics(known: GameRecord, target: GameRecord) -> list[str]:
    """Return sorted list of mechanics shared between two games."""
    return sorted(known.all_mechanics & target.all_mechanics)


def key_differences(known: GameRecord, target: GameRecord) -> list[str]:
    """Generate human-readable difference strings between two games.

    Returns a list of short factual statements about what differs.
    These are rule-level structural differences, not opinions.
    """
    diffs: list[str] = []

    # --- Mechanics present in target but not known ---
    target_only = target.all_mechanics - known.all_mechanics
    for m in sorted(target_only):
        label = m.replace("_", " ")
        diffs.append(f"{target.name} uses {label}, which {known.name} does not have")

    # --- Mechanics present in known but not target ---
    known_only = known.all_mechanics - target.all_mechanics
    for m in sorted(known_only):
        label = m.replace("_", " ")
        diffs.append(f"{known.name} uses {label}, which {target.name} does not have")

    # --- Structural differences ---
    if known.complexity != target.complexity:
        diffs.append(
            f"{target.name} is {target.complexity} complexity "
            f"(vs {known.name}'s {known.complexity})"
        )

    if known.player_count != target.player_count:
        k_min, k_max = known.player_count
        t_min, t_max = target.player_count
        diffs.append(
            f"{target.name} supports {t_min}–{t_max} players "
            f"(vs {known.name}'s {k_min}–{k_max})"
        )

    return diffs

