import type { AIConfig, CommunitySubmission, PlayedGame, UserShelfProfile } from "./types";
import { getGame } from "../demo/catalog";

const SHELF_KEY = "bgt_user_shelf";
const SUBMISSIONS_KEY = "bgt_community_submissions";
const AI_CONFIG_KEY = "bgt_ai_config";

const DEFAULT_SHELF: UserShelfProfile = {
  username: "PlayerOne",
  display_name: "Player One",
  bio: "Tabletop strategist & engine-building enthusiast",
  plays: [
    {
      bgg_id: 13,
      name: "Catan",
      rating: 8.5,
      notes: "Won by securing high-probability ore hexes and dominating Largest Army with knights.",
      date_logged: "2026-10-12",
    },
    {
      bgg_id: 822,
      name: "Carcassonne",
      rating: 8.0,
      notes: "Great farm placement in the endgame connected 6 finished cities for the win.",
      date_logged: "2026-10-14",
    },
    {
      bgg_id: 1406,
      name: "Monopoly",
      rating: 5.5,
      notes: "Classic family game. Traded to secure orange properties and built 3 houses.",
      date_logged: "2026-09-28",
    },
    {
      bgg_id: 148228,
      name: "Splendor",
      rating: 8.5,
      notes: "Engine building felt smooth. Reserved high-tier green gem card early.",
      date_logged: "2026-10-05",
    },
  ],
};

const DEFAULT_SUBMISSIONS: CommunitySubmission[] = [
  {
    id: "sub-1",
    name: "Dune: Imperium",
    year_published: 2020,
    min_players: 1,
    max_players: 4,
    mfg_playtime: 90,
    game_weight: 3.0,
    categories: "Strategy; Sci-Fi; Political",
    mechanics: "Worker Placement; Deck Building; Hand Management",
    description: "Battle for control of Arrakis through political maneuvering, resource harvest, and military conflict.",
    how_i_won: "Rushed the High Council seat round 2 for +2 Solari per round, then pivoted to Fremen faction influence for the victory point threshold.",
    winning_tips: "Don't ignore the combat track — victory points won on conflict rounds are the fastest way to 10 points.",
    submitted_by: "PaulAtreides",
    date_added: "2026-10-15",
  },
  {
    id: "sub-2",
    name: "Ark Nova",
    year_published: 2021,
    min_players: 1,
    max_players: 4,
    mfg_playtime: 120,
    game_weight: 3.7,
    categories: "Strategy; Animals; Economic",
    mechanics: "Hand Management; Set Collection; Tile Placement",
    description: "Plan and design a modern, scientifically managed zoo with conservation projects worldwide.",
    how_i_won: "Upgraded the Association action card first to partner with universities and sponsor high-impact conservation projects early.",
    winning_tips: "Balance Appeal and Conservation points so your markers meet faster and trigger the endgame on your terms.",
    submitted_by: "EcoBuilder",
    date_added: "2026-10-14",
  },
];

const DEFAULT_AI_CONFIG: AIConfig = {
  provider: "amd",
  apiKey: "",
  serverUrl: "http://127.0.0.1:8001/v1",
  modelName: "amd/gemma-2b-it-rocm",
  temperature: 0.2,
  maxTokens: 3000,
  enabled: true,
};

const listeners = new Set<() => void>();
function notify() {
  listeners.forEach((fn) => fn());
}

export function subscribeStorage(cb: () => void) {
  listeners.add(cb);
  return () => {
    listeners.delete(cb);
  };
}

// ── Shelf Operations ────────────────────────────────────────────────────────
export function getShelf(): UserShelfProfile {
  try {
    const raw = localStorage.getItem(SHELF_KEY);
    if (!raw) {
      localStorage.setItem(SHELF_KEY, JSON.stringify(DEFAULT_SHELF));
      return DEFAULT_SHELF;
    }
    return JSON.parse(raw);
  } catch {
    return DEFAULT_SHELF;
  }
}

export function savePlay(play: Omit<PlayedGame, "date_logged"> & { date_logged?: string }) {
  const shelf = getShelf();
  const existingIdx = shelf.plays.findIndex((p) => p.name.toLowerCase() === play.name.toLowerCase());
  const entry: PlayedGame = {
    ...play,
    date_logged: play.date_logged || new Date().toISOString().split("T")[0],
  };

  if (existingIdx >= 0) {
    shelf.plays[existingIdx] = entry;
  } else {
    shelf.plays.unshift(entry);
  }

  localStorage.setItem(SHELF_KEY, JSON.stringify(shelf));
  notify();
}

export function deletePlay(gameName: string) {
  const shelf = getShelf();
  shelf.plays = shelf.plays.filter((p) => p.name.toLowerCase() !== gameName.toLowerCase());
  localStorage.setItem(SHELF_KEY, JSON.stringify(shelf));
  notify();
}

export interface ShelfAnalytics {
  totalPlayed: number;
  avgRating: number;
  avgWeight: number;
  topMechanic: string;
  mechanicAffinities: { name: string; count: number; pct: number }[];
  ratingDistribution: { rating: number; count: number }[];
}

export function getShelfAnalytics(): ShelfAnalytics {
  const shelf = getShelf();
  const total = shelf.plays.length;
  if (total === 0) {
    return {
      totalPlayed: 0,
      avgRating: 0,
      avgWeight: 0,
      topMechanic: "None",
      mechanicAffinities: [],
      ratingDistribution: Array.from({ length: 10 }, (_, i) => ({ rating: i + 1, count: 0 })),
    };
  }

  const avgRating = shelf.plays.reduce((acc, p) => acc + p.rating, 0) / total;

  // Compute weight and mechanics from catalog
  let totalWeight = 0;
  let weightCount = 0;
  const mechCounts = new Map<string, number>();

  shelf.plays.forEach((p) => {
    const rec = getGame(p.name);
    if (rec) {
      if (rec.game_weight) {
        totalWeight += rec.game_weight;
        weightCount++;
      } else {
        totalWeight += rec.complexity === "low" ? 1.8 : rec.complexity === "medium" ? 2.5 : 3.5;
        weightCount++;
      }
      rec.primary_mechanics.forEach((m) => {
        const label = m.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
        mechCounts.set(label, (mechCounts.get(label) || 0) + 1);
      });
    }
  });

  const avgWeight = weightCount > 0 ? totalWeight / weightCount : 2.5;

  const sortedMechs = [...mechCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([name, count]) => ({
      name,
      count,
      pct: Math.min(100, Math.round((count / total) * 100)),
    }));

  const topMechanic = sortedMechs[0]?.name || "Strategic";

  // Rating distribution 1..10
  const ratingDist = Array.from({ length: 10 }, (_, i) => {
    const star = i + 1;
    const count = shelf.plays.filter((p) => Math.round(p.rating) === star).length;
    return { rating: star, count };
  });

  return {
    totalPlayed: total,
    avgRating: Math.round(avgRating * 10) / 10,
    avgWeight: Math.round(avgWeight * 10) / 10,
    topMechanic,
    mechanicAffinities: sortedMechs.slice(0, 5),
    ratingDistribution: ratingDist,
  };
}

// ── Community Submissions ────────────────────────────────────────────────────
export function getSubmissions(): CommunitySubmission[] {
  try {
    const raw = localStorage.getItem(SUBMISSIONS_KEY);
    if (!raw) {
      localStorage.setItem(SUBMISSIONS_KEY, JSON.stringify(DEFAULT_SUBMISSIONS));
      return DEFAULT_SUBMISSIONS;
    }
    return JSON.parse(raw);
  } catch {
    return DEFAULT_SUBMISSIONS;
  }
}

export function addSubmission(sub: Omit<CommunitySubmission, "id" | "date_added">): CommunitySubmission {
  const list = getSubmissions();
  const newSub: CommunitySubmission = {
    ...sub,
    id: `sub-${Date.now()}`,
    date_added: new Date().toISOString().split("T")[0],
  };
  list.unshift(newSub);
  localStorage.setItem(SUBMISSIONS_KEY, JSON.stringify(list));
  notify();
  return newSub;
}

// ── AI Configuration ────────────────────────────────────────────────────────
export function getAIConfig(): AIConfig {
  try {
    const raw = localStorage.getItem(AI_CONFIG_KEY);
    if (!raw) {
      localStorage.setItem(AI_CONFIG_KEY, JSON.stringify(DEFAULT_AI_CONFIG));
      return DEFAULT_AI_CONFIG;
    }
    return JSON.parse(raw);
  } catch {
    return DEFAULT_AI_CONFIG;
  }
}

export function saveAIConfig(cfg: AIConfig) {
  localStorage.setItem(AI_CONFIG_KEY, JSON.stringify(cfg));
  notify();
}

