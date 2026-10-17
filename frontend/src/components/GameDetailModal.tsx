import { useEffect, useState } from "react";
import { getGame } from "../demo/catalog";
import { Meeple } from "./ui";

interface Props {
  gameName: string | null;
  onClose: () => void;
  onTeachMe: (gameName: string) => void;
}

const CHAPTERS = [
  { label: "Intro", time: 0 },
  { label: "Goal", time: 15 },
  { label: "Setup", time: 35 },
  { label: "Rules", time: 75 },
  { label: "Turn", time: 115 },
  { label: "Tips", time: 165 },
  { label: "Win", time: 210 },
];

export function GameDetailModal({ gameName, onClose, onTeachMe }: Props) {
  const [activeChapter, setActiveChapter] = useState(0);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!gameName) return null;

  const rec = getGame(gameName);
  if (!rec) return null;

  const weight = (rec.game_weight || (rec.complexity === "low" ? 1.8 : rec.complexity === "medium" ? 2.5 : 3.5)).toFixed(1);
  const rating = (rec.bayes_avg_rating || 7.2).toFixed(1);
  const votes = (rec.num_ratings || 50000).toLocaleString();
  const year = rec.year_published || 2015;
  const playtime = rec.mfg_playtime || 45;
  const imageSrc = rec.image_path || (rec.bgg_id ? `/images/game_${rec.bgg_id}.jpg` : undefined);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="game-detail-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 overflow-y-auto"
      style={{ background: "rgba(0, 0, 0, 0.65)", backdropFilter: "blur(6px)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-4xl max-h-[92vh] overflow-y-auto tile p-5 sm:p-8 space-y-6 bg-surface">
        {/* Top Header Bar */}
        <div className="flex flex-wrap items-start justify-between gap-4 border-b-2 border-ink pb-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 id="game-detail-title" className="font-display text-3xl sm:text-4xl font-extrabold text-ink">
                {rec.name}
              </h2>
              <span className="text-xl font-bold text-ink-soft">({year})</span>
            </div>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1 rounded-full border-2 border-ink bg-yellow px-2.5 py-0.5 font-bold text-ink">
                ★ {rating} Geek Rating
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border-2 border-ink bg-sunk px-2.5 py-0.5 font-bold text-ink">
                {votes} Ratings
              </span>
              <span className="inline-flex items-center gap-1 rounded-full border-2 border-ink bg-paper px-2.5 py-0.5 font-bold text-ink">
                Weight: {weight} / 5 ({rec.complexity.toUpperCase()})
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                onClose();
                onTeachMe(rec.name);
              }}
              className="btn btn-primary text-xs"
            >
              🎓 Teach Me This Game
            </button>
            <button
              onClick={onClose}
              aria-label="Close modal"
              className="rounded-full border-2 border-ink p-1.5 hover:bg-sunk text-ink font-bold"
            >
              ✕
            </button>
          </div>
        </div>

        {/* 2-Column Layout */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          {/* Left Column: Cover Image & Specs */}
          <div className="md:col-span-4 space-y-4">
            <div className="aspect-[4/3] rounded-xl overflow-hidden border-2 border-ink bg-sunk flex items-center justify-center relative">
              {imageSrc ? (
                <img
                  src={imageSrc}
                  alt={rec.name}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    // Fallback to stylized box
                    (e.currentTarget as HTMLImageElement).style.display = "none";
                  }}
                />
              ) : null}
              <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center -z-10">
                <Meeple color="var(--red)" size={48} />
                <span className="mt-2 font-display text-lg font-bold">{rec.name}</span>
              </div>
            </div>

            {/* Quick Specs Panel */}
            <div className="panel p-4 space-y-2.5 text-xs">
              <div className="flex justify-between border-b border-sunk pb-1">
                <span className="text-ink-soft">Players</span>
                <span className="font-bold text-ink">
                  {rec.player_count[0]}–{rec.player_count[1]} players
                </span>
              </div>
              <div className="flex justify-between border-b border-sunk pb-1">
                <span className="text-ink-soft">Playtime</span>
                <span className="font-bold text-ink">{playtime} mins</span>
              </div>
              <div className="flex justify-between border-b border-sunk pb-1">
                <span className="text-ink-soft">Type / Genre</span>
                <span className="font-bold text-ink capitalize">{rec.type}</span>
              </div>
              <div className="flex justify-between border-b border-sunk pb-1">
                <span className="text-ink-soft">Designer(s)</span>
                <span className="font-bold text-ink">{rec.designers || "Various"}</span>
              </div>
              {rec.bgg_url && (
                <div className="pt-1">
                  <a
                    href={rec.bgg_url}
                    target="_blank"
                    rel="noreferrer"
                    className="font-bold text-red hover:underline flex items-center gap-1"
                  >
                    <span>BoardGameGeek Profile ↗</span>
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Rules, Video, and Strategies */}
          <div className="md:col-span-8 space-y-5">
            {/* How to Play Video / Animated Demo */}
            <div className="panel p-4 space-y-3 bg-sunk/40">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-red font-bold text-lg">🎬</span>
                  <div>
                    <h3 className="font-display font-bold text-sm text-ink">How to Play Demonstration</h3>
                    <p className="text-xs text-ink-soft">Interactive visual explainer & rule chapters</p>
                  </div>
                </div>
                <span className="rounded-full border border-ink bg-yellow px-2 py-0.5 text-[11px] font-bold">
                  Rule Chapters
                </span>
              </div>

              {/* Player Stage */}
              <div className="aspect-video rounded-lg border-2 border-ink bg-surface flex flex-col items-center justify-center p-6 text-center relative overflow-hidden">
                <div className="max-w-md space-y-2">
                  <div className="inline-flex items-center gap-2 rounded-full bg-paper px-3 py-1 border border-ink text-xs font-bold">
                    <span>Part {activeChapter + 1}: {CHAPTERS[activeChapter].label}</span>
                  </div>
                  <h4 className="font-display text-xl font-extrabold text-ink">{rec.name} Tutorial</h4>
                  <p className="text-xs text-ink-soft line-clamp-3">
                    {activeChapter === 0
                      ? rec.description
                      : activeChapter === 1
                      ? `Objective: First player to complete the win condition (${rec.notes || "strategic goals"}).`
                      : activeChapter === 2
                      ? `Components & Setup: ${rec.components || "Standard board setup with starter tiles and resource bank."}`
                      : activeChapter === 3
                      ? `Core Rules: ${rec.how_to_play || "Follow sequential turn order with actions per turn."}`
                      : activeChapter === 4
                      ? `Turn Sequence: Roll or draw, take primary action, trade/build, and pass to next player.`
                      : activeChapter === 5
                      ? `Strategic Advice: ${rec.winning_tips || "Develop your resource engine early."}`
                      : `Winning Playbook: ${rec.winning_strategies || "Secure core victory points."}`}
                  </p>
                </div>
              </div>

              {/* Interactive Chapter Pills */}
              <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
                <span className="text-ink-soft font-bold mr-1">Chapters:</span>
                {CHAPTERS.map((ch, idx) => (
                  <button
                    key={ch.label}
                    onClick={() => setActiveChapter(idx)}
                    className="rounded-full px-2.5 py-1 font-bold border border-ink transition whitespace-nowrap"
                    style={{
                      background: activeChapter === idx ? "var(--ink)" : "var(--surface)",
                      color: activeChapter === idx ? "var(--paper)" : "var(--ink)",
                    }}
                  >
                    {ch.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Components Section */}
            {rec.components && (
              <div>
                <h4 className="font-display font-bold text-sm text-ink mb-1.5 flex items-center gap-1.5">
                  <span>📦 Components in the Box</span>
                </h4>
                <div className="flex flex-wrap gap-1.5 text-xs">
                  {rec.components.split(";").map((c, i) => (
                    <span key={i} className="rounded-md border border-ink bg-surface px-2 py-1 text-ink-soft">
                      {c.trim()}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Description / Synopsis */}
            <div>
              <h4 className="font-display font-bold text-sm text-ink mb-1">About the Game</h4>
              <p className="text-xs text-ink leading-relaxed bg-surface p-3 rounded-lg border border-ink/40">
                {rec.description}
              </p>
            </div>

            {/* Mechanics Tags */}
            <div>
              <h4 className="font-display font-bold text-sm text-ink mb-1.5">Mechanics & Tags</h4>
              <div className="flex flex-wrap gap-1.5 text-xs">
                {rec.primary_mechanics.map((m) => (
                  <span key={m} className="rounded-full border border-ink bg-red text-white px-2.5 py-0.5 font-bold">
                    {m.replace(/_/g, " ")}
                  </span>
                ))}
                {rec.secondary_mechanics.map((m) => (
                  <span key={m} className="rounded-full border border-ink bg-surface text-ink px-2.5 py-0.5 font-medium">
                    {m.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>

            {/* Master Strategy & Winning Playbook */}
            <div className="panel p-4 space-y-3 bg-yellow/15 border-2 border-ink">
              <h4 className="font-display font-extrabold text-sm text-ink flex items-center gap-2">
                <span>🏆 Master Strategy: How I Won & Winning Tips</span>
              </h4>

              {rec.winning_strategies && (
                <div className="text-xs bg-surface p-3 rounded border border-ink/40">
                  <span className="font-bold text-ink block mb-0.5">Tactical Playbook & High-Level Strategy:</span>
                  <p className="text-ink-soft leading-relaxed">{rec.winning_strategies}</p>
                </div>
              )}

              {rec.how_i_won && (
                <div className="text-xs bg-surface p-3 rounded border border-ink/40">
                  <span className="font-bold text-red block mb-0.5">The Victor's Playbook: How I Won My Last Match:</span>
                  <p className="text-ink-soft italic leading-relaxed">"{rec.how_i_won}"</p>
                </div>
              )}

              {rec.winning_tips && (
                <div className="text-xs bg-surface p-3 rounded border border-ink/40">
                  <span className="font-bold text-blue block mb-0.5">Winning Tips for New Players:</span>
                  <p className="text-ink-soft leading-relaxed">{rec.winning_tips}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

