"""Animation plan generation and validation.

The LLM authors a *plan* (structured JSON), never code. Plans are validated
against a strict whitelist before they reach the Manim renderer:

  scene_type  — one of the fixed template names
  steps       — 2..8 steps, each with label / caption / duration / highlight
  highlight   — object ids that exist in the chosen template

Invalid plans fall back to a deterministic plan derived from the lesson, so
POST /visual always receives something renderable.
"""
from __future__ import annotations

import json
import re

# Highlight ids each Manim template understands (mirrors the frontend SVG
# step-through so both render paths stay consistent).
TEMPLATE_OBJECTS: dict[str, set[str]] = {
    "dice_production": {"dice", "hex-8", "hex-6", "settlements", "robber"},
    "route_claim": {"hand", "route", "trains", "score"},
    "deck_cycle": {"hand", "action", "supply", "discard", "deck"},
    "step_cards": set(),
}

MIN_STEPS, MAX_STEPS = 2, 8
MIN_DUR, MAX_DUR = 1.5, 6.0
MAX_CAPTION = 180

SYSTEM_PROMPT = """You are the animation director for a board-game tutor.
Given a validated lesson and the player's profile, design ONE short Manim
animation plan that teaches the lesson's key mechanic visually.

Return exactly one JSON object (no markdown fences) matching:
{
  "scene_type": "dice_production" | "route_claim" | "deck_cycle" | "step_cards",
  "title": "short scene title",
  "steps": [{"label": "2-4 words", "caption": "one teaching sentence",
             "duration": 3.0, "highlight": ["id", ...]}]
}

Rules:
- Pick scene_type by the mechanic taught: dice rolling / resource production
  -> dice_production; route building / network claiming -> route_claim;
  deck building / drafting / hand management -> deck_cycle; anything else
  -> step_cards.
- 3 to 6 steps that follow the game's actual turn flow as stated in the lesson.
- Never invent rules; every caption must be supported by the lesson text.
- Personalize: where it helps understanding, connect a step to a game the
  player already knows using "Just like in <game>, ...". Use ONLY games from
  player_known_games, and only for the shared idea the lesson claims.
- Adapt depth to user_level: beginner = more, smaller steps; experienced =
  fewer, denser steps.
- highlight ids MUST come from the allowed list for the chosen scene_type:
  dice_production: dice, hex-8, hex-6, settlements, robber
  route_claim: hand, route, trains, score
  deck_cycle: hand, action, supply, discard, deck
  step_cards: [] (no highlight ids)
- duration is seconds, between 1.5 and 6.0.
"""


def build_messages(lesson: dict, rec: dict, user_level: str) -> list[dict]:
    payload = {
        "target_game": lesson.get("target_game") or rec.get("target_game"),
        "player_known_games": rec.get("player_known_games", []),
        "user_level": user_level,
        "lesson_title": lesson.get("title"),
        "sections": [s.get("text", "") for s in lesson.get("sections", [])],
        "comparisons": [
            {"familiar_game": c.get("familiar_game"), "shared_idea": c.get("text"),
             "key_difference": c.get("key_difference")}
            for c in lesson.get("comparisons", [])
        ],
    }
    return [{"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}]


def _clamp_text(value, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text[:limit]


def validate_plan(raw: str | dict) -> dict:
    """Validate/clamp an LLM plan. Raises ValueError when unusable."""
    plan = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(plan, dict):
        raise ValueError("plan must be an object")
    scene_type = plan.get("scene_type")
    if scene_type not in TEMPLATE_OBJECTS:
        raise ValueError(f"unknown scene_type: {scene_type!r}")
    allowed = TEMPLATE_OBJECTS[scene_type]
    steps_in = plan.get("steps")
    if not isinstance(steps_in, list) or not (MIN_STEPS <= len(steps_in) <= MAX_STEPS):
        raise ValueError(f"steps must be a list of {MIN_STEPS}-{MAX_STEPS} items")
    steps: list[dict] = []
    for step in steps_in:
        if not isinstance(step, dict):
            raise ValueError("each step must be an object")
        label = _clamp_text(step.get("label"), 40)
        caption = _clamp_text(step.get("caption"), MAX_CAPTION)
        if not label or not caption:
            raise ValueError("each step needs a label and a caption")
        raw_highlight = step.get("highlight") or []
        if not isinstance(raw_highlight, list):
            raise ValueError("highlight must be a list")
        highlight = [h for h in (_clamp_text(h, 24) for h in raw_highlight) if h in allowed]
        try:
            duration = float(step.get("duration", 3.0))
        except (TypeError, ValueError):
            duration = 3.0
        duration = max(MIN_DUR, min(MAX_DUR, duration))
        steps.append({"label": label, "caption": caption,
                      "duration": round(duration, 2), "highlight": highlight})
    return {"scene_type": scene_type,
            "title": _clamp_text(plan.get("title"), 80) or "How it works",
            "steps": steps}


def fallback_plan(lesson: dict, rec: dict) -> dict:
    """Deterministic plan from the lesson, used when LLM generation fails."""
    target = lesson.get("target_game") or rec.get("target_game") or "the game"
    mechanics = [m.get("mechanic", "") for m in rec.get("per_mechanic", [])]
    if any(m in ("dice_rolling", "resource_production") for m in mechanics):
        scene_type, highlights = "dice_production", ["dice", "hex-8", "hex-6", "settlements"]
    elif any(m in ("route_building", "network_building") for m in mechanics):
        scene_type, highlights = "route_claim", ["hand", "route", "trains", "score"]
    elif any(m in ("deck_building", "card_drafting", "hand_management") for m in mechanics):
        scene_type, highlights = "deck_cycle", ["deck", "hand", "action", "discard"]
    else:
        scene_type, highlights = "step_cards", []
    steps: list[dict] = []
    for section in lesson.get("sections", [])[:4]:
        text = _clamp_text(section.get("text"), MAX_CAPTION)
        if text:
            steps.append({"label": _clamp_text(section.get("title") or "Step", 40),
                          "caption": text, "duration": 4.0, "highlight": highlights})
    if len(steps) < MIN_STEPS:
        steps = [{"label": "Learn", "caption": f"{target}, step by step.", "duration": 3.0,
                  "highlight": highlights},
                 {"label": "Practice", "caption": "Answer the quiz to check yourself.",
                  "duration": 3.0, "highlight": []}]
    return {"scene_type": scene_type, "title": f"{target} — how it works", "steps": steps}


def generate_plan(lesson: dict, rec: dict, user_level: str) -> tuple[dict, str]:
    """Return (plan, origin) where origin is 'llm' or 'fallback'."""
    from . import llm
    try:
        raw = llm.chat(build_messages(lesson, rec, user_level))
        return validate_plan(raw), "llm"
    except Exception:  # noqa: BLE001 — any failure falls back deterministically
        return fallback_plan(lesson, rec), "fallback"
