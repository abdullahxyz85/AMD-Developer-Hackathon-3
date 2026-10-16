import { useState } from "react";
import { useCatalog } from "../catalog";
import { allMechanics, getGame } from "../demo/catalog";
import { OriginBadge } from "../components/ui";

export function GamesView() {
  const { data, origin, label } = useCatalog();
  const [sel, setSel] = useState<string | null>(null);
  const games = data.supported_games;
  // Columns: every mechanic used by at least one game, most common first.
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
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-4xl font-extrabold sm:text-5xl">The game shelf</h1>
          <p className="mt-2 max-w-prose text-lg text-ink-soft">
            Every supported game and the mechanics it's tagged with. Shared dots are what the tutor uses to build comparisons.
          </p>
        </div>
        <OriginBadge origin={origin} />
      </header>

      <div className="flex flex-wrap gap-4 text-sm">
        <span className="inline-flex items-center gap-2"><span className="h-3.5 w-3.5 rounded-full border-2 border-ink bg-ink" /> Core mechanic</span>
        <span className="inline-flex items-center gap-2"><span className="h-3.5 w-3.5 rounded-full border-2 border-ink" /> Secondary mechanic</span>
        <span className="inline-flex items-center gap-2"><span className="h-3.5 w-3.5 rounded-sm border-2 border-ink bg-red" /> Game you can learn</span>
      </div>

      <div className="tile overflow-x-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr>
              <th className="sticky left-0 z-10 bg-surface p-3 text-left font-display">Game</th>
              {cols.map((m) => (
                <th key={m} scope="col" className="relative h-40 w-10 min-w-10 p-0">
                  <span className="absolute bottom-2 left-1/2 origin-left -rotate-55 whitespace-nowrap text-xs font-bold">{label(m)}</span>
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
                <tr key={g.name} className="border-t-2 border-sunk hover:bg-sunk" style={sel === g.name ? { background: "var(--sunk)" } : undefined}>
                  <th className="sticky left-0 z-10 bg-surface p-0 text-left">
                    <button onClick={() => setSel(sel === g.name ? null : g.name)} className="flex w-full items-center gap-2 px-3 py-2 font-display font-semibold" aria-expanded={sel === g.name}>
                      {isTarget && <span className="h-3 w-3 rounded-sm border-2 border-ink bg-red" aria-label="learnable" />}
                      {g.name}
                    </button>
                  </th>
                  {cols.map((m) => {
                    const prim = g.primary_mechanics.includes(m);
                    const sec = !prim && !!rec?.secondary_mechanics.includes(m);
                    return (
                      <td key={m} className="p-1 text-center">
                        {(prim || sec) && (
                          <span className="mx-auto block h-3.5 w-3.5 rounded-full border-2 border-ink" style={{ background: prim ? "var(--ink)" : "transparent" }}
                            title={`${g.name}: ${label(m)} (${prim ? "core" : "secondary"})`} />
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
          {selRec?.bgg_url && (
            <a href={selRec.bgg_url} target="_blank" rel="noreferrer" className="mt-4 inline-block font-bold underline decoration-2 underline-offset-2">
              View on BoardGameGeek
            </a>
          )}
        </section>
      )}
    </div>
  );
}
