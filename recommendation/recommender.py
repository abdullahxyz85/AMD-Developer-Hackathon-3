"""
recommender.py — Main entry point for the Recommendation Engine.

Public API:
    get_recommendations(known_games, target_game) → RecommendationResponse

This is the function called by the FastAPI backend endpoint.
"""

from __future__ import annotations

import logging

from .game_metadata import GameCatalog, GameRecord, catalog as _default_catalog
from .schemas import MechanicComparison, RecommendationResponse
from .similarity import (
    key_differences,
    per_mechanic_best,
    rank_known_games,
    shared_mechanics,
    weighted_similarity,
)

logger = logging.getLogger(__name__)

# ── Hardcoded "why it helps" sentences for well-known game pairs ─────────
# These override the generic fallback for common combinations so the lesson
# feels more natural. Add more as you curate.
_WHY_IT_HELPS_OVERRIDES: dict[tuple[str, str, str], str] = {
    # (known_game, target_game, mechanic)
    ("Monopoly", "Catan", "resource_management"): (
        "Like Monopoly's property income, Catan settlements produce resources "
        "each turn based on dice — think of hexes as colour-coded property groups."
    ),
    ("Monopoly", "Catan", "trading"): (
        "Catan's player trading mirrors Monopoly's deal-making, but resources "
        "are commodities (wood, ore) rather than money."
    ),
    ("Monopoly", "Catan", "economic"): (
        "Both games have an economic loop where early investment (buying property / "
        "building settlements) generates passive income that funds future growth."
    ),
    ("Poker", "Catan", "probability"): (
        "Poker players already reason about dice odds; in Catan, numbers 6 and 8 "
        "roll most often — the same bell-curve thinking applies."
    ),
    ("Risk", "Catan", "territory_control"): (
        "Risk's army placement and Catan's road/settlement building both use "
        "geographic position to control resources and block opponents."
    ),
    ("Monopoly", "Ticket to Ride", "set_collection"): (
        "Collecting matching colored train cards is just like gathering a color "
        "monopoly — you hoard until you have enough to act."
    ),
    ("Poker", "Dominion", "hand_management"): (
        "Managing your Dominion hand each turn — deciding what to play and when "
        "— mirrors choosing which poker hand to reveal based on what you've drawn."
    ),
    ("Uno", "Dominion", "hand_management"): (
        "Both Uno and Dominion reward knowing your hand and playing cards in "
        "the right order to chain effects."
    ),
}


def _why_it_helps(
    known: GameRecord,
    target: GameRecord,
    mechanic: str,
    shared: list[str],
) -> str:
    """Return a pedagogical 'why this comparison helps' sentence.

    Uses a curated override if available, otherwise generates a generic one.
    """
    key = (known.name, target.name, mechanic)
    if key in _WHY_IT_HELPS_OVERRIDES:
        return _WHY_IT_HELPS_OVERRIDES[key]

    # Generic fallback
    mechanic_label = mechanic.replace("_", " ")
    shared_label = ", ".join(shared[:2]) if shared else "some mechanics"
    return (
        f"{known.name}'s experience with {mechanic_label} "
        f"provides a useful mental model for {target.name}'s version "
        f"(both share: {shared_label})."
    )


def get_recommendations(
    known_games: list[str],
    target_game: str,
    catalog: GameCatalog = _default_catalog,
) -> RecommendationResponse:
    """Generate mechanic-level recommendations for a player profile.

    Parameters
    ----------
    known_games:
        Names of games the player already knows (e.g. ["Monopoly", "Chess"]).
    target_game:
        Name of the game the player wants to learn (e.g. "Catan").
    catalog:
        GameCatalog instance (default: module-level singleton from games.json).

    Returns
    -------
    RecommendationResponse
        Ranked recommendations per mechanic plus warnings for poor coverage.

    Raises
    ------
    ValueError
        If target_game is not in the catalog.
    """
    warnings: list[str] = []

    # ── Resolve target game ────────────────────────────────────────────────
    target = catalog.get(target_game)
    if target is None:
        available = ", ".join(sorted(catalog.supported_games))
        raise ValueError(
            f"Target game '{target_game}' is not in the catalog. "
            f"Supported: {available}"
        )

    # ── Resolve known games ────────────────────────────────────────────────
    known_records, unknown_names = catalog.resolve_known_games(known_games)

    if unknown_names:
        warnings.append(
            f"These games are not in the catalog and were skipped: "
            f"{', '.join(unknown_names)}"
        )
        logger.warning("Unknown known_games skipped: %s", unknown_names)

    if not known_records:
        # No usable known games at all
        warnings.append(
            "No recognized known games were provided. "
            "Recommendations will be generic."
        )
        return RecommendationResponse(
            target_game=target.name,
            player_known_games=known_games,
            top_overall="(none)",
            top_overall_score=0.0,
            per_mechanic=[],
            warnings=warnings,
        )

    # ── Overall ranking ────────────────────────────────────────────────────
    ranked = rank_known_games(known_records, target)
    top_game, top_score = ranked[0]

    # ── Per-mechanic comparisons ───────────────────────────────────────────
    # Focus on PRIMARY mechanics of the target game (most important to explain).
    target_primary = target.primary_mechanics

    per_mechanic: list[MechanicComparison] = []
    covered_mechanics: set[str] = set()

    for mechanic in target_primary:
        best_known, score = per_mechanic_best(known_records, target, mechanic)

        if best_known is None:
            warnings.append(
                f"None of your known games cover '{catalog.mechanic_label(mechanic)}'. "
                "The tutor will explain this mechanic from scratch."
            )
            continue

        shared = shared_mechanics(best_known, target)
        diffs = key_differences(best_known, target)
        why = _why_it_helps(best_known, target, mechanic, shared)

        per_mechanic.append(
            MechanicComparison(
                mechanic=mechanic,
                mechanic_label=catalog.mechanic_label(mechanic),
                best_known_game=best_known.name,
                shared_mechanics=shared,
                key_differences=diffs,
                why_it_helps=why,
                score=round(score, 3),
            )
        )
        covered_mechanics.add(mechanic)

    # ── Warn about uncovered secondary mechanics ───────────────────────────
    for mechanic in target.secondary_mechanics:
        if mechanic not in covered_mechanics:
            _, score = per_mechanic_best(known_records, target, mechanic)
            if score == 0.0:
                label = catalog.mechanic_label(mechanic)
                warnings.append(
                    f"Your known games don't cover '{label}' "
                    f"(a secondary mechanic of {target.name})."
                )

    return RecommendationResponse(
        target_game=target.name,
        player_known_games=[r.name for r in known_records],
        top_overall=top_game.name,
        top_overall_score=round(top_score, 3),
        per_mechanic=per_mechanic,
        warnings=warnings,
    )

