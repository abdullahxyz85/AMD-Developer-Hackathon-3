"""recommendation/__init__.py — Public API for the recommendation package."""

from .recommender import get_recommendations
from .schemas import MechanicComparison, RecommendationRequest, RecommendationResponse
from .api import router, app

__all__ = [
    "get_recommendations",
    "MechanicComparison",
    "RecommendationRequest",
    "RecommendationResponse",
    "router",   # mount into the main FastAPI app
    "app",      # standalone dev server
]

