"""
game_metadata.py — Load and access curated game data.

Loads from data/games.json. The JSON is the single source of truth for
game mechanics and metadata; this module wraps it with typed helpers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

_DATA_FILE = Path(__file__).parent / "data" / "games.json"


@dataclass
class GameRecord:
    name: str
    description: str
    game_type: str
    player_count: tuple[int, int]
    complexity: str
    primary_mechanics: list[str]
    secondary_mechanics: list[str]
    tags: list[str]
    notes: str
    key_mechanics_explained: dict[str, str] = field(default_factory=dict)

    @property
    def all_mechanics(self) -> set[str]:
        """All mechanics (primary + secondary) as a set."""
        return set(self.primary_mechanics) | set(self.secondary_mechanics)

    def mechanic_weight(self, mechanic: str) -> float:
        """Return importance weight for a mechanic in this game.

        Primary mechanics are more central and scored higher.
        """
        if mechanic in self.primary_mechanics:
            return 1.5
        if mechanic in self.secondary_mechanics:
            return 1.0
        return 0.0


class GameCatalog:
    """Registry of all supported games loaded from games.json."""

    def __init__(self, data_file: Path = _DATA_FILE) -> None:
        with data_file.open(encoding="utf-8") as f:
            raw = json.load(f)

        self._mechanic_labels: dict[str, str] = raw.get("mechanic_labels", {})
        self._games: dict[str, GameRecord] = {}

        for name, data in raw.get("games", {}).items():
            pc = data.get("player_count", [2, 4])
            self._games[name] = GameRecord(
                name=name,
                description=data.get("description", ""),
                game_type=data.get("type", "unknown"),
                player_count=(pc[0], pc[1]),
                complexity=data.get("complexity", "medium"),
                primary_mechanics=data.get("primary_mechanics", []),
                secondary_mechanics=data.get("secondary_mechanics", []),
                tags=data.get("tags", []),
                notes=data.get("notes", ""),
                key_mechanics_explained=data.get("key_mechanics_explained", {}),
            )

    # ------------------------------------------------------------------ #
    # Public helpers                                                       #
    # ------------------------------------------------------------------ #

    @property
    def supported_games(self) -> list[str]:
        """Alphabetical list of all games in the catalog."""
        return sorted(self._games.keys())

    def get(self, game_name: str) -> GameRecord | None:
        """Case-insensitive lookup. Returns None if game not found."""
        # Try exact match first
        if game_name in self._games:
            return self._games[game_name]
        # Try case-insensitive
        lower = game_name.lower()
        for key, record in self._games.items():
            if key.lower() == lower:
                return record
        return None

    def mechanic_label(self, mechanic: str) -> str:
        """Return the human-readable label for a mechanic tag."""
        return self._mechanic_labels.get(mechanic, mechanic.replace("_", " ").title())

    def resolve_known_games(
        self, known_games: list[str]
    ) -> tuple[list[GameRecord], list[str]]:
        """Resolve a list of game name strings to GameRecord objects.

        Returns (found_records, unknown_names).
        """
        found: list[GameRecord] = []
        unknown: list[str] = []
        for name in known_games:
            record = self.get(name)
            if record is not None:
                found.append(record)
            else:
                unknown.append(name)
        return found, unknown


# Module-level singleton — import and use directly
catalog = GameCatalog()

