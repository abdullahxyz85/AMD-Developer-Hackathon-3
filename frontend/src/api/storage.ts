import type { PlayedGame, UserShelfProfile } from "./types";
import { getGame } from "../demo/catalog";

const SHELF_KEY = "bgt_user_shelf";

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
