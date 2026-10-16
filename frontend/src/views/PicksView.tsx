import { useMemo, useState } from "react";
import { useCatalog } from "../catalog";
import { getGame } from "../demo/catalog";
import { getShelf } from "../api/storage";
import type { GameSummary } from "../api/types";
import { GameDetailModal } from "../components/GameDetailModal";
import { LogPlayModal } from "../components/LogPlayModal";

interface Props {
  onTeachGame?: (name: string) => void;
}

export function PicksView({ onTeachGame }: Props) {
  const { data } = useCatalog();
  const [detailGame, setDetailGame] = useState<string | null>(null);
  const [logGame, setLogGame] = useState<GameSummary | null>(null);

  const shelf = getShelf();
  const playedNames = useMemo(() => new Set(shelf.plays.map((p) => p.name.toLowerCase())), [shelf.plays]);

  // Compute recommendations
  const recommendations = useMemo(() => {
    // Collect mechanics favored by player
    const favoredMechs = new Set<string>();
    shelf.plays.forEach((p) => {
      const rec = getGame(p.name);
      rec?.primary_mechanics.forEach((m) => favoredMechs.add(m));
    });

    // Score games not already heavily played
    return data.supported_games
      .map((g) => {
        const shared = g.primary_mechanics.filter((m) => favoredMechs.has(m));
        const sharedCount = shared.length;

        // Match score 70% to 98%
        const score = Math.min(98, 70 + sharedCount * 7 + (data.target_games.includes(g.name) ? 5 : 0));

        const reasons: string[] = [];
        if (shared.length > 0) {
          reasons.push(`Shares ${shared.slice(0, 2).map((m) => m.replace(/_/g, " ")).join(" & ")} with games on your shelf`);
        }
        if (g.complexity === "medium") {
          reasons.push("Matches your sweet-spot medium complexity");
        }
        if (data.target_games.includes(g.name)) {
          reasons.push("Fully supported by the AI Tutor with visual animations");
        }
        if (reasons.length === 0) {
          reasons.push("Highly rated by community players with similar tastes");
        }

        return {
          game: g,
          score,
          reasons,
          isPlayed: playedNames.has(g.name.toLowerCase()),
        };
      })
      .sort((a, b) => b.score - a.score);
  }, [data.supported_games, data.target_games, shelf.plays, playedNames]);

  return (
    <div className="space-y-6">
      <header className="panel p-6 sm:p-8 space-y-3 bg-surface border-2 border-ink">
        <div className="inline-flex items-center gap-2 rounded-full border-2 border-ink bg-yellow px-3 py-0.5 text-xs font-bold text-ink">
          <span>✨ Curated Picks</span>
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-ink">
          Recommended For You
        </h1>
        <p className="text-ink-soft text-sm sm:text-base max-w-2xl">
          Based on the {shelf.plays.length} games logged on your shelf. Games with shared mechanics and matching complexity are scored and ranked below.
        </p>
      </header>

      {/* Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
        {recommendations.map(({ game, score, reasons, isPlayed }) => {
          const rec = getGame(game.name);
          const bggId = game.bgg_id || rec?.bgg_id;
          const imageSrc = game.image_path || rec?.image_path || (bggId ? `/images/game_${bggId}.jpg` : undefined);
          const rating = (game.bayes_avg_rating || rec?.bayes_avg_rating || 7.5).toFixed(1);

          return (
            <div
              key={game.name}
              className="tile p-4 flex flex-col justify-between group cursor-pointer hover:-translate-y-1 transition duration-200"
              onClick={() => setDetailGame(game.name)}
            >
              <div>
                <div className="relative aspect-[4/3] rounded-lg overflow-hidden border-2 border-ink bg-sunk mb-3">
                  {imageSrc ? (
                    <img
                      src={imageSrc}
                      alt={game.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                      onError={(e) => {
                        (e.currentTarget as HTMLImageElement).style.display = "none";
                      }}
                    />
                  ) : null}

                  <div className="absolute inset-0 flex flex-col items-center justify-center p-2 text-center -z-10 bg-sunk">
                    <span className="font-display font-extrabold text-sm">{game.name}</span>
                  </div>

                  {/* Match Pill */}
                  <div className="absolute top-2 left-2 px-2.5 py-0.5 rounded-full border-2 border-ink bg-red text-white text-xs font-extrabold shadow-sm">
                    ⚡ {score}% Match
                  </div>

                  {/* Rating */}
                  <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full border-2 border-ink bg-yellow text-[11px] font-extrabold text-ink shadow-sm">
                    ★ {rating}
                  </div>

                  {/* Bottom overlay */}
                  <div className="absolute bottom-1.5 left-1.5 right-1.5 flex items-center justify-between text-[10px] font-bold bg-surface/90 border border-ink px-2 py-0.5 rounded">
                    <span>👥 {game.player_count_min}–{game.player_count_max}p</span>
                    <span>⏳ {game.mfg_playtime || 45}m</span>
                    <span>{isPlayed ? "✓ On Shelf" : "New to you"}</span>
                  </div>
                </div>

                <h3 className="font-display font-extrabold text-base text-ink group-hover:text-red transition line-clamp-1">
                  {game.name}
                </h3>

                {/* Match Reasons */}
                <div className="mt-2 space-y-1.5">
                  {reasons.slice(0, 2).map((r, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-xs text-ink-soft">
                      <span className="text-green font-bold text-xs mt-0.5">✓</span>
                      <span className="line-clamp-2">{r}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-4 pt-3 border-t-2 border-sunk flex items-center gap-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onTeachGame?.(game.name);
                  }}
                  className="flex-1 py-1 px-2.5 rounded-full border border-ink bg-red text-white hover:opacity-90 text-xs font-bold text-center"
                >
                  Teach Me
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setLogGame(game);
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
