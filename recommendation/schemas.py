"""
schemas.py — Pydantic models for the Recommendation Engine.

These are the shared data contracts between:
  - recommender.py  (produces RecommendationResponse)
  - backend / FastAPI (passes it to the prompt builder)
  - prompt engineer (consumes RecommendationResponse to personalize lessons)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MechanicComparison(BaseModel):
    """How one mechanic of the target game relates to the player's known games."""

    mechanic: str = Field(..., description="Mechanic tag, e.g. 'resource_management'")
    mechanic_label: str = Field(..., description="Human-readable label, e.g. 'Resource Management'")
    best_known_game: str = Field(..., description="The player's known game most useful for this mechanic")
    shared_mechanics: list[str] = Field(
        default_factory=list,
        description="Mechanic tags shared between best_known_game and the target game",
    )
    key_differences: list[str] = Field(
        default_factory=list,
        description="Important ways the target game's mechanic differs from the known game",
    )
    why_it_helps: str = Field(
        ...,
        description="One sentence explaining why this comparison is pedagogically useful",
    )
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score 0–1")


class RecommendationResponse(BaseModel):
    """Full recommendation output for a player profile and a target game."""

    target_game: str
    player_known_games: list[str]
    top_overall: str = Field(
        ...,
        description="The single known game most useful overall for teaching the target game",
    )
    top_overall_score: float = Field(..., ge=0.0, le=1.0)
    per_mechanic: list[MechanicComparison] = Field(
        default_factory=list,
        description="Per-mechanic recommendations, ordered by mechanic importance",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Flags like 'No known game covers deck_building'",
    )


class RecommendationRequest(BaseModel):
    """Input to the recommendation endpoint."""

    known_games: list[str] = Field(..., min_length=1, description="Games the player already knows")
    target_game: str = Field(..., description="Game the player wants to learn")

