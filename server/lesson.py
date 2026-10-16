"""End-to-end lesson pipeline.

  1. recommendation service  → ranked familiar games per mechanic
  2. RAG service             → evidence for the target game (focus mechanics)
                             + evidence for the best known games
  3. tutor.prompts           → context + messages (grounding contract)
  4. AMD Token Factory       → schema-validated lesson JSON
  5. mapping                 → the frontend LessonResponse / AskResponse contract
"""
from __future__ import annotations

import re

import httpx

from tutor.prompts import (build_messages, insufficient_lesson, prepare_context,
                           validate_lesson)

from . import animation, llm
from .config import RAG_URL, RECOMMEND_URL

HTTP_TIMEOUT = httpx.Timeout(90.0, connect=10.0)

# RAG section names → frontend lesson section keys
SECTION_KEYS = {
    "objective": "objective", "setup": "setup", "turn_structure": "turn_structure",
    "core_mechanics": "core_mechanics", "mechanic": "core_mechanics",
    "exceptions": "core_mechanics", "examples": "core_mechanics",
    "overview": "core_mechanics", "notes": "core_mechanics",
}


class PipelineError(RuntimeError):
    """An upstream service failed."""


def _post(url: str, payload: dict) -> dict:
    try:
        response = httpx.post(url, json=payload, timeout=HTTP_TIMEOUT)
    except httpx.HTTPError as exc:
        raise PipelineError(f"{url} unreachable: {exc}") from exc
    if response.status_code != 200:
        raise PipelineError(f"{url} returned HTTP {response.status_code}: {response.text[:300]}")
    return response.json()


def _pretty(section: str) -> str:
    return section.replace("_", " ").title()


def gather_context(known_games: list[str], target_game: str,
                   learning_goal: str, question: str | None, user_level: str) -> tuple[dict, dict]:
    """Call recommendation + RAG, build the tutor context."""
    rec = _post(RECOMMEND_URL + "/recommend",
                {"known_games": known_games, "target_game": target_game})
    focus = list(dict.fromkeys(m["mechanic"] for m in rec.get("per_mechanic", [])))
    query = question or (learning_goal or "understand the first turn")
    rag = _post(RAG_URL + "/rag/retrieve",
                {"game": rec["target_game"], "query": query,
                 "focus_mechanics": focus, "k": 12})
    familiar_retrievals = []
    for game in dict.fromkeys(m["best_known_game"] for m in rec.get("per_mechanic", [])):
        if game not in rec["player_known_games"]:
            continue
        mechanics = [m["mechanic"] for m in rec["per_mechanic"] if m["best_known_game"] == game]
        familiar_retrievals.append(_post(RAG_URL + "/rag/retrieve", {
            "game": game,
            "query": "Explain " + ", ".join(mechanics) + ", objectives and key rules",
            "focus_mechanics": mechanics, "k": 6}))
    context = prepare_context(rec, rag, learning_goal=learning_goal or query,
                              question=question, familiar_retrievals=familiar_retrievals)
    context["user_level"] = user_level
    return rec, context


def generate_lesson(rec: dict, context: dict) -> dict:
    """LLM-generated, schema-validated lesson (tutor.Lesson shape)."""
    if context["insufficient_evidence"]:
        return insufficient_lesson(context).model_dump()
    content = llm.chat(build_messages(context), json_mode=True)
    return validate_lesson(content, context).model_dump()


def _sources(context: dict) -> list[dict]:
    sources = []
    for passage in context["evidence"].values():
        source = passage.get("source") or {}
        sources.append({"title": source.get("title", ""), "url": source.get("url", ""),
                        "section": passage.get("section", "")})
    return sources


def _short_summary(text: str, limit: int = 260) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    summary = ""
    for sentence in sentences:
        if len(summary) + len(sentence) + 1 > limit:
            break
        summary = (summary + " " + sentence).strip()
    return summary or text[:limit]


def lesson_to_response(lesson: dict, rec: dict, context: dict, user_level: str) -> dict:
    """Map tutor.Lesson → the frontend LessonResponse contract."""
    evidence = context["evidence"]
    by_mechanic = {m["best_known_game"]: m for m in rec.get("per_mechanic", [])}

    sections = []
    for index, section in enumerate(lesson.get("sections", []), 1):
        cited = [e for e in section.get("evidence_ids", []) if e in evidence]
        dom = next((evidence[e]["section"] for e in cited
                    if evidence[e]["game"].casefold() == lesson["target_game"].casefold()), "")
        if not dom and cited:
            dom = evidence[cited[0]]["section"]
        key = SECTION_KEYS.get(dom, "core_mechanics")
        sections.append({
            "key": key,
            "title": _pretty(dom) or f"Part {index}",
            "body": section.get("text", ""),
            "source_ids": [int(e[1:]) - 1 for e in cited if re.fullmatch(r"p\d+", e)],
        })

    comparisons = []
    for comparison in lesson.get("comparisons", []):
        match = by_mechanic.get(comparison.get("familiar_game"), {})
        comparisons.append({
            "familiar_game": comparison.get("familiar_game", ""),
            "shared_mechanic": match.get("mechanic_label", "Shared mechanics"),
            "key_difference": comparison.get("key_difference", ""),
            "why_it_helps": comparison.get("text", ""),
            "score": match.get("score"),
        })

    quiz = [{"question": q.get("text", ""), "options": q.get("options", []),
             "correct_index": q.get("correct_index", 0),
             "explanation": q.get("explanation", "")}
            for q in lesson.get("quiz", [])]

    warnings = list(lesson.get("warnings", []))
    animation_plan = None
    if lesson.get("status") == "ok":
        animation_plan, origin = animation.generate_plan(lesson, rec, user_level)
        if origin == "fallback":
            warnings.append("Animation plan fell back to the deterministic template.")

    first_body = sections[0]["body"] if sections else ""
    return {
        "lesson_title": lesson.get("title", ""),
        "short_summary": _short_summary(first_body),
        "sections": sections,
        "comparisons": comparisons,
        "sources": _sources(context),
        "quiz": quiz,
        "animation_plan": animation_plan,
        "warnings": warnings,
        "status": lesson.get("status", "ok"),
        "target_game": lesson.get("target_game", rec.get("target_game", "")),
    }


def ask_to_response(lesson: dict, context: dict) -> dict:
    """Map a question-mode lesson → the frontend AskResponse contract."""
    answer = "\n\n".join(s.get("text", "") for s in lesson.get("sections", [])).strip()
    if not answer:
        answer = "; ".join(lesson.get("warnings", [])) or "I could not find reliable evidence for that."
    insufficient = lesson.get("status") != "ok"
    return {"answer": answer, "sources": _sources(context),
            "insufficient_evidence": insufficient}
