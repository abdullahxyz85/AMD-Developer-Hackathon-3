"""
load_games.py — Layer A fact-card builder (Work Plan task 1.4)

Reads the curated game catalog (recommendation/data/games.json) and converts
every game into small, self-contained "fact card" chunks suitable for
embedding + BM25 indexing (see scripts/ingest.py, task 1.6).

Each chunk is a dict:
    {
      "id":      "Catan:mechanic:trading",
      "game":    "Catan",
      "section": "mechanic",            # overview | mechanics_list | mechanic | notes
      "mechanic": "trading" | null,     # mechanic tag when section == "mechanic"
      "layer":   "fact_card",
      "text":    "self-contained text (game name included for retrieval quality)",
      "bgg_id":  13,
      "source":  {"title": "Catan — BoardGameGeek", "url": "https://..."}
    }

Chunk types per game:
  - overview        : what the game is (description + type, players, complexity, tags)
  - mechanics_list  : which mechanics the game uses (full mechanic inventory)
  - mechanic (n)    : one rule card per key_mechanics_explained entry
  - notes           : strategy/quirk notes

Usage:
    python3 scripts/load_games.py                      # default paths
    python3 scripts/load_games.py --input X --output Y # override
    python3 scripts/load_games.py --dry-run            # summary only, no file written
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# RAG/scripts/ -> RAG/ -> repo root
RAG_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = RAG_DIR.parent
DEFAULT_INPUT = REPO_ROOT / "recommendation" / "data" / "games.json"
DEFAULT_OUTPUT = RAG_DIR / "knowledge" / "fact_cards" / "fact_cards.json"

SECTION_OVERVIEW = "overview"
SECTION_MECHANICS_LIST = "mechanics_list"
SECTION_MECHANIC = "mechanic"
SECTION_NOTES = "notes"


def _players_text(player_count: list) -> str:
    if not player_count or len(player_count) != 2:
        return "unknown player count"
    lo, hi = player_count
    return f"{lo} player" if lo == hi else f"{lo}–{hi} players"


def _source(game_name: str, game: dict) -> dict:
    """Citation metadata; falls back gracefully if bgg_url is missing."""
    url = game.get("bgg_url")
    if url:
        return {"title": f"{game_name} — BoardGameGeek", "url": url}
    return {"title": f"{game_name} — curated project data", "url": ""}


def _make_chunk(
    game_name: str, section: str, text: str, source: dict, bgg_id: int | None,
    mechanic: str | None = None,
) -> dict:
    chunk_id = f"{game_name}:{section}" + (f":{mechanic}" if mechanic else "")
    return {
        "id": chunk_id,
        "game": game_name,
        "section": section,
        "mechanic": mechanic,
        "layer": "fact_card",
        "text": text,
        "bgg_id": bgg_id,
        "source": source,
    }


def game_to_chunks(game_name: str, game: dict, mechanic_labels: dict) -> list[dict]:
    """Convert one game record into fact-card chunks."""
    source = _source(game_name, game)
    bgg_id = game.get("bgg_id")
    chunks: list[dict] = []

    # 1. Overview card — answers "what is this game?"
    desc = (game.get("description") or "").strip()
    parts = [f"{game_name} is {game.get('type', 'a')} game.", desc]
    if game.get("player_count"):
        parts.append(f"It plays with {_players_text(game['player_count'])}.")
    if game.get("complexity"):
        parts.append(f"Complexity: {game['complexity']}.")
    if game.get("tags"):
        parts.append(f"Tags: {', '.join(game['tags'])}.")
    chunks.append(_make_chunk(
        game_name, SECTION_OVERVIEW, " ".join(p for p in parts if p), source, bgg_id
    ))

    # 2. Mechanics inventory card — answers "what mechanics does X use?"
    all_mechanics = list(game.get("primary_mechanics", [])) + list(game.get("secondary_mechanics", []))
    if all_mechanics:
        labeled = [
            mechanic_labels.get(m, m.replace("_", " ")) for m in dict.fromkeys(all_mechanics)
        ]
        chunks.append(_make_chunk(
            game_name, SECTION_MECHANICS_LIST,
            f"{game_name} uses the following mechanics: {'; '.join(labeled)}.",
            source, bgg_id,
        ))

    # 3. Per-mechanic rule cards — the rule content for retrieval
    for tag, rule_text in (game.get("key_mechanics_explained") or {}).items():
        label = mechanic_labels.get(tag, tag.replace("_", " "))
        chunks.append(_make_chunk(
            game_name, SECTION_MECHANIC,
            f"{game_name} — {label}: {rule_text.strip()}",
            source, bgg_id, mechanic=tag,
        ))

    # 4. Notes card — strategy hints and quirks
    notes = (game.get("notes") or "").strip()
    if notes:
        chunks.append(_make_chunk(
            game_name, SECTION_NOTES, f"{game_name} notes: {notes}", source, bgg_id
        ))

    return chunks


def load_catalog(path: Path) -> dict:
    """Load and minimally validate games.json."""
    if not path.exists():
        sys.exit(f"[ERROR] Catalog not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "games" not in data or not data["games"]:
        sys.exit(f"[ERROR] No games found in {path}")
    return data


def build_fact_cards(data: dict) -> list[dict]:
    """Convert the full catalog into a flat, deterministic chunk list."""
    mechanic_labels = data.get("mechanic_labels", {})
    chunks: list[dict] = []
    for game_name in sorted(data["games"]):
        chunks.extend(game_to_chunks(game_name, data["games"][game_name], mechanic_labels))
    return chunks


def main() -> None:
    ap = argparse.ArgumentParser(description="Build Layer A fact cards from games.json")
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    ap.add_argument("--dry-run", action="store_true", help="print summary, write nothing")
    args = ap.parse_args()

    data = load_catalog(args.input)
    chunks = build_fact_cards(data)

    # Summary
    by_section: dict[str, int] = {}
    for c in chunks:
        by_section[c["section"]] = by_section.get(c["section"], 0) + 1
    games_covered = len({c["game"] for c in chunks})
    no_url = sorted({c["game"] for c in chunks if not c["source"]["url"]})

    print(f"Catalog      : {args.input}")
    print(f"Games        : {games_covered}")
    print(f"Chunks       : {len(chunks)}  {by_section}")
    if no_url:
        print(f"[WARN] missing bgg_url: {', '.join(no_url)}")

    if args.dry_run:
        print("[DRY RUN] no file written")
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"generated_from": str(args.input), "chunks": chunks}, f,
                  ensure_ascii=False, indent=2)
    print(f"Written      : {args.output}")


if __name__ == "__main__":
    main()
