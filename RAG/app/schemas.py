"""
schemas.py — Pydantic models for the RAG service.

These are the shared data contracts between:
  - retrieval.py   (produces RetrievalResponse)
  - main.py        (FastAPI boundary, validates requests)
  - backend / prompt engineer (consume passages + citations for lesson JSON)
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SourceRef(BaseModel):
    """Citation attached to every retrieved passage."""
    title: str = Field(..., description="Human-readable source name")
    url: str = Field("", description="Link to the original source (BGG page / rulebook)")


class RetrievalRequest(BaseModel):
    """Input to POST /rag/retrieve."""
    game: str = Field(..., min_length=1, description="Target game name (fuzzy-matched)")
    query: str = Field(..., min_length=1, description="User question or lesson focus")
    focus_mechanics: list[str] = Field(
        default_factory=list,
        description="Optional mechanic tags (from RecommendationResponse.per_mechanic) to bias retrieval",
    )
    k: int = Field(6, ge=1, le=20, description="Max passages to return")


class RetrievedPassage(BaseModel):
    """One evidence chunk with full citation metadata."""
    game: str
    section: str = Field(..., description="objective | setup | turn_structure | mechanic | overview | ...")
    layer: str = Field(..., description="curated_rules | fact_card")
    mechanic: str | None = Field(None, description="Mechanic tag when section == 'mechanic'")
    text: str
    score: float = Field(..., ge=0.0, le=1.0, description="Normalized fused relevance score")
    source: SourceRef


class RetrievalResponse(BaseModel):
    """Output of POST /rag/retrieve."""
    passages: list[RetrievedPassage] = Field(default_factory=list)
    game_resolved: str | None = Field(
        None, description="Canonical game name the request resolved to; null if unknown to the KB"
    )
    insufficient_evidence: bool = Field(
        False, description="True when the tutor should say 'I don't know' instead of answering"
    )
    retrieval_mode: str = Field("hybrid", description="keyword | vector | hybrid")


class GameInfo(BaseModel):
    """Entry in GET /rag/games."""
    name: str
    bgg_id: int | None = None
    bgg_url: str = ""
    has_curated_rules: bool = Field(..., description="True if Layer B rule sections exist")
