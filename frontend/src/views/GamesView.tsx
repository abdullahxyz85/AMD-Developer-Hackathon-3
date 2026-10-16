import { useMemo, useState } from "react";
import { useCatalog } from "../catalog";
import { allMechanics, getGame } from "../demo/catalog";
import { OriginBadge } from "../components/ui";
import type { GameSummary } from "../api/types";
import { GameDetailModal } from "../components/GameDetailModal";
import { LogPlayModal } from "../components/LogPlayModal";

interface Props {
  onTeachGame?: (name: string) => void;
}

export function GamesView({ onTeachGame }: Props) {
  const { data, origin, label } = useCatalog();
  const [viewMode, setViewMode] = useState<"cards" | "matrix">("cards");
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [weightFilter, setWeightFilter] = useState("");
  const [sortBy, setSortBy] = useState<"rating" | "year" | "name" | "weight">("rating");

  // Modals
  const [detailGame, setDetailGame] = useState<string | null>(null);
  const [logGame, setLogGame] = useState<GameSummary | null>(null);

  // Selected game for matrix mode
  const [sel, setSel] = useState<string | null>(null);

  const games = data.supported_games;

  // Filter & Sort
  const filteredGames = useMemo(() => {
    return games
      .filter((g) => {
        const query = search.trim().toLowerCase();
        if (query) {
          const matchName = g.name.toLowerCase().includes(query);
          const matchMech = g.primary_mechanics.some((m) => m.toLowerCase().includes(query));
          const matchTag = g.tags.some((t) => t.toLowerCase().includes(query));
          if (!matchName && !matchMech && !matchTag) return false;
        }

        if (category) {
          const c = category.toLowerCase();
          const matchType = g.game_type.toLowerCase().includes(c);
          const matchTag = g.tags.some((t) => t.toLowerCase().includes(c));
          if (!matchType && !matchTag) return false;
        }

        const rec = getGame(g.name);
        const w = rec?.game_weight ?? (g.complexity === "low" ? 1.8 : g.complexity === "medium" ? 2.5 : 3.5);

        if (weightFilter === "light" && w >= 2.0) return false;
        if (weightFilter === "medium" && (w < 2.0 || w > 3.2)) return false;
        if (weightFilter === "heavy" && w <= 3.2) return false;

        return true;
      })
      .sort((a, b) => {
        const recA = getGame(a.name);
        const recB = getGame(b.name);

        if (sortBy === "rating") {
          const rA = recA?.bayes_avg_rating ?? (a.complexity === "high" ? 7.8 : 7.2);
          const rB = recB?.bayes_avg_rating ?? (b.complexity === "high" ? 7.8 : 7.2);
          return rB - rA;
        }
        if (sortBy === "year") {
          const yA = recA?.year_published ?? 2000;
          const yB = recB?.year_published ?? 2000;
          return yB - yA;
        }
        if (sortBy === "weight") {
          const wA = recA?.game_weight ?? (a.complexity === "low" ? 1.8 : a.complexity === "medium" ? 2.5 : 3.5);
          const wB = recB?.game_weight ?? (b.complexity === "low" ? 1.8 : b.complexity === "medium" ? 2.5 : 3.5);
          return wB - wA;
        }
        return a.name.localeCompare(b.name);
      });
  }, [games, search, category, weightFilter, sortBy]);

  // Matrix calculation
  const counts = new Map<string, number>();
  games.forEach((g) => {
    const rec = getGame(g.name);
    const ms = rec ? allMechanics(rec) : new Set(g.primary_mechanics);
    ms.forEach((m) => counts.set(m, (counts.get(m) ?? 0) + 1));
  });
  const cols = [...counts.entries()].sort((a, b) => b[1] - a[1]).map(([m]) => m);
  const selected = sel ? games.find((g) => g.name === sel) : null;
  const selRec = sel ? getGame(sel) : undefined;

  return (
    <div className="space-y-6">
      {/* Header */}
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-4xl font-extrabold sm:text-5xl text-ink">The game shelf</h1>
          <p className="mt-2 max-w-prose text-lg text-ink-soft">
            Explore curated board games, review their mechanics, watch visual rule videos, and read winning playbooks.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* View Mode Toggle */}
          <div className="inline-flex rounded-full border-2 border-ink bg-surface p-1">
            <button
              onClick={() => setViewMode("cards")}
              className="rounded-full px-3 py-1 text-xs font-bold transition"
              style={{
                background: viewMode === "cards" ? "var(--ink)" : "transparent",
                color: viewMode === "cards" ? "var(--paper)" : "var(--ink)",
              }}
            >
              Cards View
            </button>
            <button
              onClick={() => setViewMode("matrix")}
              className="rounded-full px-3 py-1 text-xs font-bold transition"
              style={{
                background: viewMode === "matrix" ? "var(--ink)" : "transparent",
                color: viewMode === "matrix" ? "var(--paper)" : "var(--ink)",
              }}
            >
              Mechanics Matrix
            </button>
          </div>
          <OriginBadge origin={origin} />
        </div>
      </header>

      {/* Filter and Search Controls (Cards View) */}
      {viewMode === "cards" && (
        <div className="tile p-4 space-y-3 bg-surface">
          <div className="flex flex-col sm:flex-row gap-3 items-center">
            <div className="relative flex-1 w-full">
              <input
                type="text"
                placeholder="Search games by title, tag, or mechanic..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-paper border-2 border-ink rounded-lg px-3 py-2 text-sm text-ink placeholder:text-ink-soft focus:outline-none"
              />
            </div>
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="bg-paper border-2 border-ink rounded-lg px-3 py-2 text-xs font-bold text-ink"
              >
                <option value="rating">Top Geek Rating</option>
                <option value="year">Year Published</option>
                <option value="weight">Complexity Weight</option>
                <option value="name">Name (A-Z)</option>
              </select>
              <select
                value={weightFilter}
                onChange={(e) => setWeightFilter(e.target.value)}
                className="bg-paper border-2 border-ink rounded-lg px-3 py-2 text-xs font-bold text-ink"
              >
                <option value="">All Weights</option>
                <option value="light">Light (&lt; 2.0)</option>
                <option value="medium">Medium (2.0 - 3.2)</option>
                <option value="heavy">Heavy (3.2+)</option>
              </select>
            </div>
          </div>

          {/* Quick Category Chips */}
          <div className="flex items-center gap-1.5 overflow-x-auto text-xs pt-1">
            <span className="text-ink-soft font-bold mr-1">Category:</span>
            {["", "Strategy", "Thematic", "Family", "Card", "Abstract", "Party", "War"].map((cat) => {
              const active = category === cat;
              return (
                <button
                  key={cat}
                  onClick={() => setCategory(cat)}
                  className="rounded-full px-3 py-1 font-bold border-2 border-ink transition whitespace-nowrap"
                  style={{
                    background: active ? "var(--red)" : "var(--paper)",
                    color: active ? "var(--on-accent)" : "var(--ink)",
                  }}
                >
                  {cat || "All"}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* CARDS VIEW */}
      {viewMode === "cards" && (
        <div className="space-y-4">
          <div className="flex justify-between items-center text-xs text-ink-soft">
            <span>Showing {filteredGames.length} games</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            {filteredGames.map((g) => {
              const rec = getGame(g.name);
              const bggId = g.bgg_id || rec?.bgg_id;
              const imageSrc = g.image_path || rec?.image_path || (bggId ? `/images/game_${bggId}.jpg` : undefined);
              const rating = (g.bayes_avg_rating || rec?.bayes_avg_rating || 7.2).toFixed(1);
              const weightVal = (g.game_weight || rec?.game_weight || (g.complexity === "low" ? 1.8 : g.complexity === "medium" ? 2.5 : 3.5)).toFixed(1);
              const weightPct = Math.min(100, (parseFloat(weightVal) / 5.0) * 100);
              const isTarget = data.target_games.includes(g.name);

              return (
                <div
                  key={g.name}
                  className="tile p-4 flex flex-col justify-between group cursor-pointer hover:-translate-y-1 transition duration-200"
                  onClick={() => setDetailGame(g.name)}
                >
                  <div>
                    {/* Cover Thumbnail */}
                    <div className="relative aspect-[4/3] rounded-lg overflow-hidden border-2 border-ink bg-sunk mb-3">
                      {imageSrc ? (
                        <img
                          src={imageSrc}
                          alt={g.name}
                          className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                          onError={(e) => {
                            (e.currentTarget as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : null}

                      {/* Fallback pattern */}
                      <div className="absolute inset-0 flex flex-col items-center justify-center p-2 text-center -z-10 bg-sunk">
                        <span className="font-display font-extrabold text-sm">{g.name}</span>
                      </div>

                      {/* Rating Badge */}
                      <div className="absolute top-2 left-2 px-2 py-0.5 rounded-full border-2 border-ink bg-yellow text-[11px] font-extrabold text-ink shadow-sm">
                        ★ {rating}
                      </div>

                      {/* Target Game Badge */}
                      {isTarget && (
                        <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full border-2 border-ink bg-red text-[11px] font-extrabold text-white shadow-sm">
                          Learnable
                        </div>
                      )}

                      {/* Specs Overlay */}
                      <div className="absolute bottom-1.5 left-1.5 right-1.5 flex items-center justify-between text-[10px] font-bold bg-surface/90 border border-ink px-2 py-0.5 rounded">
                        <span>👥 {g.player_count_min === g.player_count_max ? g.player_count_min : `${g.player_count_min}-${g.player_count_max}`}p</span>
                        <span>⏳ {g.mfg_playtime || rec?.mfg_playtime || 45}m</span>
                        <span>{g.year_published || rec?.year_published || 2015}</span>
                      </div>
                    </div>

                    {/* Title */}
                    <h3 className="font-display font-extrabold text-base leading-snug text-ink group-hover:text-red transition line-clamp-1">
                      {g.name}
                    </h3>

                    {/* Weight Gauge */}
                    <div className="mt-2 space-y-1">
                      <div className="flex justify-between text-[10px] text-ink-soft font-bold">
                        <span>Weight</span>
                        <span>{weightVal} / 5</span>
                      </div>
                      <div className="h-1.5 w-full bg-sunk rounded-full overflow-hidden border border-ink">
                        <div
                          className="h-full bg-ink"
                          style={{ width: `${weightPct}%` }}
                        />
                      </div>
                    </div>

                    {/* Mechanics Tags */}
                    <div className="flex flex-wrap gap-1 mt-2.5">
                      {g.primary_mechanics.slice(0, 2).map((m) => (
                        <span
                          key={m}
                          className="px-1.5 py-0.5 rounded text-[10px] font-bold border border-ink bg-paper text-ink truncate max-w-[110px]"
                        >
                          {label(m)}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="mt-3 pt-2.5 border-t-2 border-sunk flex items-center gap-1.5">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setDetailGame(g.name);
                      }}
                      className="flex-1 py-1 px-2 rounded-full border border-ink bg-paper hover:bg-sunk text-xs font-bold text-center text-ink"
                    >
                      Details & Video
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setLogGame(g);
                      }}
                      className="p-1 rounded-full border border-ink bg-surface hover:bg-sunk text-ink font-bold text-xs"
                      title="Log Play"
                    >
                      +
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* MATRIX VIEW */}
      {viewMode === "matrix" && (
        <div className="space-y-6">
          <div className="flex flex-wrap gap-4 text-sm">
            <span className="inline-flex items-center gap-2">
              <span className="h-3.5 w-3.5 rounded-full border-2 border-ink bg-ink" /> Core mechanic
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="h-3.5 w-3.5 rounded-full border-2 border-ink" /> Secondary mechanic
            </span>
            <span className="inline-flex items-center gap-2">
              <span className="h-3.5 w-3.5 rounded-sm border-2 border-ink bg-red" /> Game you can learn
            </span>
          </div>

          <div className="tile overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr>
                  <th className="sticky left-0 z-10 bg-surface p-3 text-left font-display">Game</th>
                  {cols.map((m) => (
                    <th key={m} scope="col" className="relative h-40 w-10 min-w-10 p-0">
                      <span className="absolute bottom-2 left-1/2 origin-left -rotate-55 whitespace-nowrap text-xs font-bold">
                        {label(m)}
                      </span>
                    </th>
                  ))}
                  <th aria-hidden className="w-28 min-w-28" />
                </tr>
              </thead>
              <tbody>
                {games.map((g) => {
                  const rec = getGame(g.name);
                  const isTarget = data.target_games.includes(g.name);
                  return (
                    <tr
                      key={g.name}
                      className="border-t-2 border-sunk hover:bg-sunk"
                      style={sel === g.name ? { background: "var(--sunk)" } : undefined}
                    >
                      <th className="sticky left-0 z-10 bg-surface p-0 text-left">
                        <button
                          onClick={() => setSel(sel === g.name ? null : g.name)}
                          className="flex w-full items-center gap-2 px-3 py-2 font-display font-semibold"
                          aria-expanded={sel === g.name}
                        >
                          {isTarget && (
                            <span className="h-3 w-3 rounded-sm border-2 border-ink bg-red" aria-label="learnable" />
                          )}
                          {g.name}
                        </button>
                      </th>
                      {cols.map((m) => {
                        const prim = g.primary_mechanics.includes(m);
                        const sec = !prim && !!rec?.secondary_mechanics.includes(m);
                        return (
                          <td key={m} className="p-1 text-center">
                            {(prim || sec) && (
                              <span
                                className="mx-auto block h-3.5 w-3.5 rounded-full border-2 border-ink"
                                style={{ background: prim ? "var(--ink)" : "transparent" }}
                                title={`${g.name}: ${label(m)} (${prim ? "core" : "secondary"})`}
                              />
                            )}
                          </td>
                        );
                      })}
                      <td />
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {selected && (
            <section className="panel max-w-3xl p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="font-display text-2xl font-extrabold">{selected.name}</h2>
                <span className="text-sm text-ink-soft">
                  {selected.game_type.charAt(0).toUpperCase() + selected.game_type.slice(1)} game, {selected.complexity} complexity, {selected.player_count_min}–{selected.player_count_max} players
                </span>
              </div>
              <p className="mt-2">{selected.description}</p>
              {selRec?.key_mechanics_explained && (
                <dl className="mt-4 space-y-3">
                  {Object.entries(selRec.key_mechanics_explained).map(([m, t]) => (
                    <div key={m}>
                      <dt className="font-display font-semibold">{label(m)}</dt>
                      <dd className="text-[15px] text-ink-soft">{t}</dd>
                    </div>
                  ))}
                </dl>
              )}
              <div className="mt-4 flex items-center gap-3">
                <button
                  onClick={() => setDetailGame(selected.name)}
                  className="btn btn-primary text-xs"
                >
                  Full Details & Playbook
                </button>
                {selRec?.bgg_url && (
                  <a
                    href={selRec.bgg_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-bold underline decoration-2 underline-offset-2 text-xs"
                  >
                    View on BoardGameGeek
                  </a>
                )}
              </div>
            </section>
          )}
        </div>
      )}

      {/* Global Modals */}
      {detailGame && (
        <GameDetailModal
          gameName={detailGame}
          onClose={() => setDetailGame(null)}
          onLogPlay={(g) => setLogGame(g)}
          onTeachMe={(target) => {
            setDetailGame(null);
            onTeachGame?.(target);
          }}
        />
      )}

      {logGame && (
        <LogPlayModal
          game={logGame}
          onClose={() => setLogGame(null)}
        />
      )}
    </div>
  );
}
