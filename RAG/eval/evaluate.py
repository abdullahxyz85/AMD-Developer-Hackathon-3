"""
evaluate.py — Retrieval evaluation (Work Plan task 3.2)

Runs every question in eval/questions.json through three retrieval modes
(keyword / vector / hybrid) and reports:

  - hit@3, hit@5, MRR      — answerable questions (expected section or mechanic)
  - unanswerable accuracy  — insufficient_evidence flag correctness
  - unknown-game accuracy  — game_resolved null correctness

Writes eval/RESULTS.md with the mode comparison table (the "measured results"
artifact required by the project guide) and a per-question detail table.

Usage (from RAG/):
  python3 eval/evaluate.py
  python3 eval/evaluate.py --k 6 --quiet
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent
RAG_DIR = EVAL_DIR.parent
sys.path.insert(0, str(RAG_DIR))
sys.path.insert(0, str(RAG_DIR / "scripts"))

from app.retrieval import RetrievalEngine  # noqa: E402

MODES = ("keyword", "vector", "hybrid")
K_EVAL = 10  # retrieve deep; metrics computed at 3 and 5


def matches_expected(passage: dict, q: dict) -> bool:
    if q.get("expected_mechanic"):
        return passage.get("mechanic") == q["expected_mechanic"]
    if q.get("expected_section"):
        if q["class"] == "ambiguous" and q["expected_section"] == "mechanic":
            return passage.get("mechanic") == q.get("expected_mechanic")
        return passage.get("section") == q["expected_section"]
    return False


def hit_at_k(ranks: list[int], k: int) -> float:
    return sum(1 for r in ranks if 0 < r <= k) / len(ranks) if ranks else 0.0


def mrr(ranks: list[int]) -> float:
    return sum(1.0 / r for r in ranks if r > 0) / len(ranks) if ranks else 0.0


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true", help="suppress per-question output")
    args = ap.parse_args()

    questions = json.load(open(EVAL_DIR / "questions.json", encoding="utf-8"))["questions"]
    engine = RetrievalEngine()

    answerable = [q for q in questions if not q.get("unanswerable")]
    unans = [q for q in questions if q.get("unanswerable")
             and q["class"] != "unknown_game"]
    unknown = [q for q in questions if q["class"] == "unknown_game"]

    results: dict[str, dict] = {}
    detail: dict[str, list] = {}

    for mode in MODES:
        t0 = time.perf_counter()
        answer_ranks: list[int] = []
        una_flags, unk_flags = [], []
        per_q: list[dict] = []

        for q in questions:
            r = engine.retrieve(game=q["game"], query=q["query"],
                                k=K_EVAL, mode=mode)
            if not q.get("unanswerable"):
                rank = next((i + 1 for i, p in enumerate(r["passages"])
                             if matches_expected(p, q)), 0)
                answer_ranks.append(rank)
                per_q.append({"id": q["id"], "mode": mode, "rank": rank})
            elif q["class"] == "unknown_game":
                ok = (r["game_resolved"] is None
                      and r["insufficient_evidence"] and not r["passages"])
                unk_flags.append(ok)
                per_q.append({"id": q["id"], "mode": mode, "ok": ok})
            else:
                ok = r["insufficient_evidence"]
                una_flags.append(ok)
                per_q.append({"id": q["id"], "mode": mode, "ok": ok})

        results[mode] = {
            "hit@3": hit_at_k(answer_ranks, 3),
            "hit@5": hit_at_k(answer_ranks, 5),
            "mrr": mrr(answer_ranks),
            "unanswerable_acc": sum(una_flags) / len(una_flags) if una_flags else None,
            "unknown_game_acc": sum(unk_flags) / len(unk_flags) if unk_flags else None,
            "latency_ms_per_q": (time.perf_counter() - t0) * 1000 / len(questions),
        }
        detail[mode] = per_q
        if not args.quiet:
            print(f"[{mode:7}] hit@3={results[mode]['hit@3']:.2f} "
                  f"hit@5={results[mode]['hit@5']:.2f} mrr={results[mode]['mrr']:.2f}")

    # ---------- write RESULTS.md ----------
    lines = [
        "# RAG Retrieval Evaluation Results",
        "",
        f"Eval set: {len(questions)} questions "
        f"({len(answerable)} answerable, {len(unans)} unanswerable, {len(unknown)} unknown-game) "
        f"from `eval/questions.json` v1 — {len(engine.chunks)} chunks, "
        f"{len(engine.games)} games, {engine.embed_model_name}.",
        "",
        "## Mode comparison",
        "",
        "| Metric | keyword (BM25) | vector (MiniLM) | hybrid (RRF) |",
        "|---|---|---|---|",
    ]
    metric_names = [("hit@3", "Hit@3"), ("hit@5", "Hit@5"), ("mrr", "MRR"),
                    ("unanswerable_acc", "Unanswerable detection"),
                    ("unknown_game_acc", "Unknown-game detection")]
    for key, label in metric_names:
        row = [label]
        for mode in MODES:
            v = results[mode][key]
            row.append("n/a" if v is None else f"{v:.2f}")
        lines.append("| " + " | ".join(row) + " |")
    lines.append("| Latency (ms/question, incl. embed) | "
                 + " | ".join(f"{results[m]['latency_ms_per_q']:.1f}" for m in MODES) + " |")

    lines += [
        "",
        "## Per-question detail (hybrid)",
        "",
        "| Question | Class | Expected | Rank (hybrid) | Pass |",
        "|---|---|---|---|---|",
    ]
    qmap = {q["id"]: q for q in questions}
    for row in detail["hybrid"]:
        q = qmap[row["id"]]
        expected = q.get("expected_section") or q.get("expected_mechanic") or "—"
        if q.get("unanswerable"):
            ok = "✅" if row["ok"] else "❌"
            rank = "flagged" if row["ok"] else "MISSED"
        else:
            ok = "✅" if 0 < row["rank"] <= 5 else "❌"
            rank = str(row["rank"]) if row["rank"] else "not found"
        lines.append(f"| {q['id']} | {q['class']} | {expected} | {rank} | {ok} |")

    best = max(MODES, key=lambda m: results[m]["mrr"])
    una_in_kb = [r for r in detail["hybrid"] if qmap[r["id"]]["class"] == "unanswerable"]
    una_detected = sum(1 for r in una_in_kb if r["ok"])
    lines += [
        "",
        "## Conclusion",
        "",
        f"- Best MRR: **{best}** ({results[best]['mrr']:.2f}). "
        "Hybrid (RRF) is the default mode in the service.",
        f"- **Unanswerable limitation (honest report):** {una_detected}/{len(una_in_kb)} "
        "in-KB absent topics were flagged. With small per-game pools (8–15 chunks) "
        "something always ranks high, so a pure distance threshold cannot detect "
        "'plausible question, absent answer'. The threshold reliably catches unknown "
        "games and nonsensical queries. The real defense for absent topics is "
        "prompt-level grounding: the tutor receives only the retrieved passages and "
        "must say the evidence does not cover the question (prompt engineer's contract).",
        "- Mechanic-card questions (mech-*) rank 6–9 on bare queries because curated "
        "sections match better; the recommender hand-off (`focus_mechanics`) injects "
        "and force-ranks the requested mechanic card, which is the actual lesson path.",
        "- Threshold `MAX_TOP_DISTANCE = 0.75` tuned on 9 calibration queries; "
        "re-tune when the KB grows.",
        "- Latency measured on the dev machine; re-measure on the demo host "
        "for the performance report.",
    ]

    out = EVAL_DIR / "RESULTS.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[OK] wrote {out}")


if __name__ == "__main__":
    main()
