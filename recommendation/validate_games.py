"""
validate_games.py — Validate games.json for typos and schema errors.

Run anytime you or a teammate edits games.json:
    python recommendation/validate_games.py

Exit code 0 = valid. Exit code 1 = errors found (blocks CI).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "games.json"

# ── The canonical mechanic vocabulary ─────────────────────────────────────────
# Any mechanic tag used in a game record MUST be in this set.
VALID_MECHANICS = {
    "resource_management",
    "trading",
    "territory_control",
    "dice_rolling",
    "turn_based",
    "negotiation",
    "set_collection",
    "movement",
    "card_drafting",
    "probability",
    "asymmetric_roles",
    "economic",
    "area_control",
    "hand_management",
    "worker_placement",
    "victory_points",
    "elimination",
    "hidden_information",
    "pattern_recognition",
    "deck_building",
}

VALID_COMPLEXITY = {"low", "medium", "high"}

REQUIRED_GAME_FIELDS = {
    "description",
    "type",
    "player_count",
    "complexity",
    "primary_mechanics",
    "secondary_mechanics",
    "tags",
}


def validate() -> list[str]:
    """Run all checks. Returns a list of error strings (empty = all good)."""
    errors: list[str] = []

    # ── Load file ──────────────────────────────────────────────────────────────
    if not DATA_FILE.exists():
        return [f"FATAL: {DATA_FILE} not found"]

    try:
        with DATA_FILE.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return [f"FATAL: JSON parse error — {exc}"]

    games: dict = data.get("games", {})
    mechanic_labels: dict = data.get("mechanic_labels", {})

    if not games:
        errors.append("No games found in games.json")
        return errors

    # ── Check mechanic_labels covers all VALID_MECHANICS ──────────────────────
    for m in VALID_MECHANICS:
        if m not in mechanic_labels:
            errors.append(f"mechanic_labels is missing label for: '{m}'")

    # ── Check each game ────────────────────────────────────────────────────────
    for game_name, game_data in games.items():

        prefix = f"[{game_name}]"

        # Required fields present
        for field in REQUIRED_GAME_FIELDS:
            if field not in game_data:
                errors.append(f"{prefix} Missing required field: '{field}'")

        # complexity valid
        complexity = game_data.get("complexity", "")
        if complexity not in VALID_COMPLEXITY:
            errors.append(
                f"{prefix} Invalid complexity '{complexity}'. "
                f"Must be one of: {sorted(VALID_COMPLEXITY)}"
            )

        # player_count is a list of 2 ints
        pc = game_data.get("player_count")
        if not (isinstance(pc, list) and len(pc) == 2 and all(isinstance(x, int) for x in pc)):
            errors.append(f"{prefix} player_count must be a list of 2 integers, got: {pc!r}")
        elif pc[0] > pc[1]:
            errors.append(f"{prefix} player_count min ({pc[0]}) > max ({pc[1]})")

        # mechanic tag validation
        for field_name in ("primary_mechanics", "secondary_mechanics"):
            mechanics = game_data.get(field_name, [])
            if not isinstance(mechanics, list):
                errors.append(f"{prefix} '{field_name}' must be a list")
                continue
            for tag in mechanics:
                if tag not in VALID_MECHANICS:
                    errors.append(
                        f"{prefix} Unknown mechanic tag '{tag}' in '{field_name}'. "
                        f"Valid tags: {sorted(VALID_MECHANICS)}"
                    )

        # No overlap between primary and secondary
        primary = set(game_data.get("primary_mechanics", []))
        secondary = set(game_data.get("secondary_mechanics", []))
        overlap = primary & secondary
        if overlap:
            errors.append(
                f"{prefix} Mechanic(s) appear in BOTH primary and secondary: {sorted(overlap)}"
            )

        # description not empty
        desc = game_data.get("description", "")
        if not desc or not desc.strip():
            errors.append(f"{prefix} 'description' is empty")

        # At least one primary mechanic
        if not primary:
            errors.append(f"{prefix} 'primary_mechanics' must not be empty")

    return errors


def main() -> None:
    print(f"Validating {DATA_FILE} ...")
    errors = validate()

    if not errors:
        games_count = len(json.loads(DATA_FILE.read_text(encoding="utf-8")).get("games", {}))
        print(f"[OK] All good! {games_count} games validated with no errors.")
        sys.exit(0)
    else:
        print(f"\n[FAIL] Found {len(errors)} error(s):\n")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
