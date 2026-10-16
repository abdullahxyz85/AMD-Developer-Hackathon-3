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
  image_path?: string;
  bayes_avg_rating?: number;
  num_ratings?: number;
  year_published?: number;
  mfg_playtime?: number;
  game_weight?: number;
  has_video?: boolean;
  video_url?: string;
  components?: string;
  how_to_play?: string;
  winning_strategies?: string;
  how_i_won?: string;
  winning_tips?: string;
  designers?: string;
  publishers?: string;
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
  image_path: g.image_path ?? (g.bgg_id ? `/images/game_${g.bgg_id}.jpg` : undefined),
}));

export const MECHANIC_LABELS: Record<string, string> = data.mechanic_labels;

// Curated split
// Any game can be selected as "known" or as the target to learn
// (the UI greys out targets the player already knows).
export const TARGET_GAMES = GAMES.map((g) => g.name);
export const KNOWN_GAMES = GAMES.map((g) => g.name);

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
    bgg_id: g.bgg_id,
    bgg_url: g.bgg_url,
    image_path: g.image_path,
    bayes_avg_rating: g.bayes_avg_rating,
    num_ratings: g.num_ratings,
    year_published: g.year_published,
    mfg_playtime: g.mfg_playtime,
    game_weight: g.game_weight,
    has_video: g.has_video,
    video_url: g.video_url,
    components: g.components,
    how_to_play: g.how_to_play,
    winning_strategies: g.winning_strategies,
    how_i_won: g.how_i_won,
    winning_tips: g.winning_tips,
    designers: g.designers,
    publishers: g.publishers,
  }));
  return {
    supported_games: supported,
    mechanic_vocabulary: MECHANIC_LABELS,
    target_games: TARGET_GAMES,
    known_games: KNOWN_GAMES,
  };
}
