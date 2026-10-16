import { useEffect, useState } from "react";
import { deletePlay, getShelf, getShelfAnalytics, subscribeStorage } from "../api/storage";
import { getGame } from "../demo/catalog";
import type { GameSummary } from "../api/types";
import { LogPlayModal } from "../components/LogPlayModal";
import { GameDetailModal } from "../components/GameDetailModal";
import { Meeple } from "../components/ui";

interface Props {
  onTeachGame?: (name: string) => void;
}

export function ShelfView({ onTeachGame }: Props) {
  const [, setVersion] = useState(0);
  const [logModalOpen, setLogModalOpen] = useState(false);
  const [selectedGameForLog, setSelectedGameForLog] = useState<GameSummary | null>(null);
  const [detailGame, setDetailGame] = useState<string | null>(null);

  useEffect(() => {
    return subscribeStorage(() => setVersion((v) => v + 1));
  }, []);

  const shelf = getShelf();
  const analytics = getShelfAnalytics();

  return (
    <div className="space-y-8">
      {/* User Profile & Metrics Header */}
      <div className="tile p-6 sm:p-8 space-y-6 bg-surface">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b-2 border-ink pb-6">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl border-2 border-ink bg-yellow flex items-center justify-center font-display font-extrabold text-2xl text-ink shadow-md">
              <Meeple color="var(--red)" size={38} />
            </div>
            <div>
              <h1 className="font-display text-3xl font-extrabold text-ink">{shelf.display_name}</h1>
              <p className="text-ink-soft text-sm">{shelf.bio}</p>
            </div>
          </div>

          <button
            onClick={() => {
              const firstGame = getGame(shelf.plays[0]?.name || "Catan");
              setSelectedGameForLog((firstGame as unknown as GameSummary) || null);
              setLogModalOpen(true);
            }}
            className="btn btn-primary"
          >
            + Log A Game Play
          </button>
        </div>

        {/* 4 Stats Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="panel p-4 bg-paper">
            <div className="text-xs font-bold text-ink-soft">Total Played</div>
            <div className="font-display text-3xl font-extrabold text-red mt-1">{analytics.totalPlayed}</div>
          </div>
          <div className="panel p-4 bg-paper">
            <div className="text-xs font-bold text-ink-soft">Average Rating</div>
            <div className="font-display text-3xl font-extrabold text-blue mt-1">{analytics.avgRating} / 10</div>
          </div>
          <div className="panel p-4 bg-paper">
            <div className="text-xs font-bold text-ink-soft">Preferred Weight</div>
            <div className="font-display text-3xl font-extrabold text-green mt-1">{analytics.avgWeight} / 5</div>
          </div>
          <div className="panel p-4 bg-paper">
            <div className="text-xs font-bold text-ink-soft">Top Mechanic</div>
            <div className="font-display text-base font-extrabold text-ink mt-2 truncate">
              {analytics.topMechanic}
            </div>
          </div>
        </div>

        {/* Analytics Rows */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
          {/* Mechanics Affinity */}
          <div className="panel p-5 bg-paper space-y-3">
            <h3 className="font-display font-bold text-sm text-ink flex items-center gap-1.5">
              <span>📊 Mechanic Affinity</span>
            </h3>
            <div className="space-y-2 text-xs">
              {analytics.mechanicAffinities.length === 0 ? (
                <p className="text-ink-soft italic">No plays recorded yet</p>
              ) : (
                analytics.mechanicAffinities.map((m) => (
                  <div key={m.name} className="space-y-1">
                    <div className="flex justify-between font-bold text-ink">
                      <span>{m.name}</span>
                      <span>{m.count} plays</span>
                    </div>
                    <div className="h-2 w-full bg-sunk rounded-full overflow-hidden border border-ink">
                      <div className="h-full bg-ink" style={{ width: `${m.pct}%` }} />
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Rating Distribution */}
          <div className="panel p-5 bg-paper space-y-3">
            <h3 className="font-display font-bold text-sm text-ink flex items-center gap-1.5">
              <span>⭐ Rating Curve (1 - 10)</span>
            </h3>
            <div className="h-28 flex items-end justify-between gap-1 pt-3">
              {analytics.ratingDistribution.map((d) => {
                const maxCount = Math.max(...analytics.ratingDistribution.map((x) => x.count), 1);
                const heightPct = Math.max(12, Math.round((d.count / maxCount) * 100));
                return (
                  <div key={d.rating} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                    <span className="text-[10px] font-bold text-ink-soft">{d.count > 0 ? d.count : ""}</span>
                    <div
                      className="w-full rounded-t border-t-2 border-x-2 border-ink transition-all"
                      style={{
                        height: `${heightPct}%`,
                        background: d.count > 0 ? "var(--red)" : "var(--sunk)",
                      }}
                      title={`${d.count} games rated ${d.rating}`}
                    />
                    <span className="text-[10px] font-bold text-ink">{d.rating}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Played Games Shelf Grid */}
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="font-display text-2xl font-extrabold text-ink">
            Logged Plays ({shelf.plays.length})
          </h2>
        </div>

        {shelf.plays.length === 0 ? (
          <div className="tile p-12 text-center text-ink-soft space-y-3">
            <p className="text-base font-bold">Your shelf is empty!</p>
            <p className="text-sm">Log the games you have played to unlock personalized stats and AI recommendations.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5">
            {shelf.plays.map((play) => {
              const rec = getGame(play.name);
              const bggId = play.bgg_id || rec?.bgg_id;
              const imageSrc = rec?.image_path || (bggId ? `/images/game_${bggId}.jpg` : undefined);

              return (
                <div
                  key={play.name}
                  className="tile p-4 flex flex-col justify-between group relative hover:-translate-y-1 transition duration-200"
                >
                  <div>
                    {/* Cover image */}
                    <div
                      className="relative aspect-[4/3] rounded-lg overflow-hidden border-2 border-ink bg-sunk mb-3 cursor-pointer"
                      onClick={() => setDetailGame(play.name)}
                    >
                      {imageSrc ? (
                        <img
                          src={imageSrc}
                          alt={play.name}
                          className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                          onError={(e) => {
                            (e.currentTarget as HTMLImageElement).style.display = "none";
                          }}
                        />
                      ) : null}
                      <div className="absolute inset-0 flex flex-col items-center justify-center p-2 text-center -z-10 bg-sunk">
                        <span className="font-display font-extrabold text-sm">{play.name}</span>
                      </div>

                      <div className="absolute top-2 left-2 px-2.5 py-0.5 rounded-full border-2 border-ink bg-yellow text-xs font-extrabold text-ink shadow-sm">
                        ★ {play.rating.toFixed(1)}
                      </div>
                      <div className="absolute bottom-1.5 right-1.5 text-[10px] font-bold bg-surface/90 border border-ink px-2 py-0.5 rounded">
                        {play.date_logged}
                      </div>
                    </div>

                    <h3
                      className="font-display font-extrabold text-base text-ink hover:text-red transition cursor-pointer"
                      onClick={() => setDetailGame(play.name)}
                    >
                      {play.name}
                    </h3>

                    {/* Notes */}
                    {play.notes && (
                      <p className="mt-2 text-xs text-ink-soft italic bg-paper p-2.5 rounded border border-ink/30 line-clamp-3">
                        "{play.notes}"
                      </p>
                    )}
                  </div>

                  {/* Footer Buttons */}
                  <div className="mt-4 pt-3 border-t-2 border-sunk flex items-center justify-between gap-2">
                    <button
                      onClick={() => setDetailGame(play.name)}
                      className="text-xs font-bold text-ink underline"
                    >
                      View Details
                    </button>
                    <button
                      onClick={() => deletePlay(play.name)}
                      className="text-xs font-bold text-red hover:underline"
                      title="Remove from shelf"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Global Modals */}
      {detailGame && (
        <GameDetailModal
          gameName={detailGame}
          onClose={() => setDetailGame(null)}
          onLogPlay={(g) => {
            setSelectedGameForLog(g);
            setLogModalOpen(true);
          }}
          onTeachMe={(target) => {
            setDetailGame(null);
            onTeachGame?.(target);
          }}
        />
      )}

      {logModalOpen && selectedGameForLog && (
        <LogPlayModal
          game={selectedGameForLog}
          onClose={() => {
            setLogModalOpen(false);
            setSelectedGameForLog(null);
          }}
        />
      )}
    </div>
  );
}

