// Bundled snapshot of recommendation/data/games.json so the dashboard works
// with no backend. Refresh with:  cp ../recommendation/data/games.json src/data/
import raw from "../data/games.json";
import type { GameSummary, GamesResponse } from "../api/types";

export interface GameRecord {
  name: string;
  bgg_id?: number;
  bgg_url?: string;
  description: string;
  type: string;
  player_count: [number, number];
  complexity: string;
  primary_mechanics: string[];
  secondary_mechanics: string[];
  tags: string[];
  notes?: string;
  key_mechanics_explained?: Record<string, string>;
}

interface RawCatalog {
  games: Record<string, Omit<GameRecord, "name">>;
  mechanic_labels: Record<string, string>;
}

const data = raw as unknown as RawCatalog;

export const GAMES: GameRecord[] = Object.entries(data.games).map(([name, g]) => ({
  name,
  ...g,
  player_count: g.player_count as [number, number],
}));

export const MECHANIC_LABELS: Record<string, string> = data.mechanic_labels;

// Same curated split as recommendation/api.py
export const TARGET_GAMES = ["Catan", "Ticket to Ride", "Dominion"];
export const KNOWN_GAMES = ["Chess", "Monopoly", "Uno", "Poker", "Checkers", "Risk", "Scrabble"];

export function mechanicLabel(tag: string): string {
  return MECHANIC_LABELS[tag] ?? tag.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function getGame(name: string): GameRecord | undefined {
  const n = name.trim().toLowerCase();
  return GAMES.find((g) => g.name.toLowerCase() === n);
}

export function allMechanics(g: GameRecord): Set<string> {
  return new Set([...g.primary_mechanics, ...g.secondary_mechanics]);
}

export function demoGamesResponse(): GamesResponse {
  const supported: GameSummary[] = GAMES.map((g) => ({
    name: g.name,
    description: g.description,
    game_type: g.type,
    complexity: g.complexity,
    player_count_min: g.player_count[0],
    player_count_max: g.player_count[1],
    primary_mechanics: g.primary_mechanics,
    primary_mechanic_labels: g.primary_mechanics.map(mechanicLabel),
    tags: g.tags,
  }));
  return {
    supported_games: supported,
    mechanic_vocabulary: MECHANIC_LABELS,
    target_games: TARGET_GAMES,
    known_games: KNOWN_GAMES,
  };
}
