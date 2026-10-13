"""
api.py — FastAPI routes for the Recommendation Engine.

Endpoints:
    POST /recommend   → get personalized game recommendations
    GET  /games       → list all supported games + their mechanic metadata

Run standalone (for development/testing):
    uvicorn recommendation.api:app --reload --port 8001

Or mount into the main backend app:
    from recommendation.api import router
    app.include_router(router, prefix="/api")
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .game_metadata import catalog
from .recommender import get_recommendations
from .schemas import RecommendationRequest, RecommendationResponse

logger = logging.getLogger(__name__)

# ── Router (import this into the main backend app) ────────────────────────────
router = APIRouter(tags=["recommendation"])


# ── Schemas for /games response ───────────────────────────────────────────────

from pydantic import BaseModel


class GameSummary(BaseModel):
    name: str
    description: str
    game_type: str
    complexity: str
    player_count_min: int
    player_count_max: int
    primary_mechanics: list[str]
    primary_mechanic_labels: list[str]
    tags: list[str]


class GamesResponse(BaseModel):
    supported_games: list[GameSummary]
    mechanic_vocabulary: dict[str, str]   # tag → human label
    target_games: list[str]               # games the tutor can teach
    known_games: list[str]                # games usable as "known" by player


# Curated lists — update these as you add more games to games.json
_TARGET_GAMES = ["Catan", "Ticket to Ride", "Dominion"]
_KNOWN_GAMES  = ["Chess", "Monopoly", "Uno", "Poker", "Checkers", "Risk", "Scrabble"]


# ── POST /recommend ───────────────────────────────────────────────────────────

@router.post(
    "/recommend",
    response_model=RecommendationResponse,
    summary="Get personalized game recommendations",
    description=(
        "Given a player's known games and a target game they want to learn, "
        "returns ranked familiar-game comparisons per mechanic with explanations "
        "and key differences."
    ),
)
def recommend(req: RecommendationRequest) -> RecommendationResponse:
    """Generate mechanic-level recommendations for a player profile."""
    try:
        return get_recommendations(
            known_games=req.known_games,
            target_game=req.target_game,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected error in /recommend")
        raise HTTPException(status_code=500, detail="Internal recommendation error") from exc


# ── GET /games ────────────────────────────────────────────────────────────────

@router.get(
    "/games",
    response_model=GamesResponse,
    summary="List all supported games",
    description=(
        "Returns all games in the catalog with their mechanics and metadata. "
        "Use this to populate the game-selection UI."
    ),
)
def list_games() -> GamesResponse:
    """Return the full supported game list + mechanic vocabulary."""
    summaries: list[GameSummary] = []

    for name in catalog.supported_games:
        rec = catalog.get(name)
        if rec is None:
            continue
        summaries.append(
            GameSummary(
                name=rec.name,
                description=rec.description,
                game_type=rec.game_type,
                complexity=rec.complexity,
                player_count_min=rec.player_count[0],
                player_count_max=rec.player_count[1],
                primary_mechanics=rec.primary_mechanics,
                primary_mechanic_labels=[
                    catalog.mechanic_label(m) for m in rec.primary_mechanics
                ],
                tags=rec.tags,
            )
        )

    # Build mechanic vocabulary from catalog
    mechanic_vocab: dict[str, str] = {}
    for name in catalog.supported_games:
        rec = catalog.get(name)
        if rec is None:
            continue
        for m in rec.all_mechanics:
            mechanic_vocab[m] = catalog.mechanic_label(m)

    return GamesResponse(
        supported_games=summaries,
        mechanic_vocabulary=dict(sorted(mechanic_vocab.items())),
        target_games=_TARGET_GAMES,
        known_games=_KNOWN_GAMES,
    )


# ── Standalone FastAPI app (for dev / testing this module in isolation) ───────

app = FastAPI(
    title="Board Game Recommendation Engine",
    description="Personalized game mechanic comparison API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

