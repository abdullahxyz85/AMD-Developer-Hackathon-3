import type { GameSummary, UserLevel } from "../api/types";
import { Segmented } from "./ui";

const COMPLEXITY_PIPS: Record<string, number> = { low: 1, medium: 2, high: 3 };

function Pips({ level }: { level: string }) {
  const n = COMPLEXITY_PIPS[level] ?? 2;
  return (
    <span className="inline-flex gap-0.5" title={`${level} complexity`} aria-label={`${level} complexity`}>
      {[1, 2, 3].map((i) => (
        <span key={i} className="h-2 w-2 rounded-[2px] border border-ink" style={{ background: i <= n ? "var(--ink)" : "transparent" }} />
      ))}
    </span>
  );
}

export function KnownGamesPicker({
  games,
  selected,
  onToggle,
  accent = "var(--yellow)",
  accentText = "var(--on-yellow)",
  compact = false,
}: {
  games: GameSummary[];
  selected: string[];
  onToggle: (name: string) => void;
  accent?: string;
  accentText?: string;
  compact?: boolean;
}) {
  return (
    <div className={`grid gap-2 ${compact ? "grid-cols-2" : "grid-cols-2 sm:grid-cols-3 lg:grid-cols-4"}`}>
      {games.map((g) => {
        const on = selected.includes(g.name);
        return (
          <button
            key={g.name}
            aria-pressed={on}
            onClick={() => onToggle(g.name)}
            className="game-box flex flex-col justify-start px-3 py-2"
            style={on ? { background: accent, color: accentText } : undefined}
          >
            <span className="flex items-center justify-between gap-2">
              <span className="font-display text-base font-semibold">{g.name}</span>
              <Pips level={g.complexity} />
            </span>
            {!compact && <span className="block text-xs capitalize text-ink-soft" style={on ? { color: accentText } : undefined}>{g.game_type} game</span>}
          </button>
        );
      })}
    </div>
  );
}

export function TargetPicker({
  games,
  value,
  onChange,
}: {
  games: GameSummary[];
  value: string;
  onChange: (name: string) => void;
}) {
  return (
    <div role="radiogroup" aria-label="Game to learn" className="grid gap-3 sm:grid-cols-3">
      {games.map((g) => {
        const on = g.name === value;
        return (
          <button
            key={g.name}
            role="radio"
            aria-checked={on}
            aria-pressed={on}
            onClick={() => onChange(g.name)}
            className="game-box flex flex-col justify-start p-3"
            style={on ? { background: "var(--ink)", color: "var(--paper)" } : undefined}
          >
            <span className="flex items-baseline justify-between">
              <span className="font-display text-xl font-extrabold">{g.name}</span>
              <span className="text-xs">
                {g.player_count_min}–{g.player_count_max} players
              </span>
            </span>
            <span className="mt-1 line-clamp-2 block text-sm opacity-80">{g.description}</span>
          </button>
        );
      })}
    </div>
  );
}

export const LEVELS: { value: UserLevel; label: string }[] = [
  { value: "beginner", label: "New to hobby games" },
  { value: "intermediate", label: "Played a few" },
  { value: "experienced", label: "Seasoned player" },
];

export const GOALS = [
  "understand the first turn",
  "learn how to win",
  "get the full overview",
];

export function LevelGoal({
  level,
  goal,
  onLevel,
  onGoal,
}: {
  level: UserLevel;
  goal: string;
  onLevel: (l: UserLevel) => void;
  onGoal: (g: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
      <Segmented label="Experience" value={level} options={LEVELS} onChange={onLevel} />
      <label className="flex items-center gap-2 text-sm font-bold">
        I want to
        <select
          value={goal}
          onChange={(e) => onGoal(e.target.value)}
          className="rounded-full border-2 border-ink bg-surface px-3 py-1.5 font-normal"
        >
          {GOALS.map((g) => (
            <option key={g}>{g}</option>
          ))}
        </select>
      </label>
    </div>
  );
}
