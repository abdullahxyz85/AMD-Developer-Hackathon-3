import { useState } from "react";
import { generateLesson, type LessonBundle } from "../api/client";
import type { UserLevel } from "../api/types";
import { useCatalog } from "../catalog";
import { Comparisons, LessonBody } from "../components/Lesson";
import { KnownGamesPicker, TargetPicker } from "../components/ProfilePicker";
import { Meeple, Notice, OriginBadge, Segmented, Spinner } from "../components/ui";
import { LEVELS } from "../components/ProfilePicker";

const A = { name: "Player A", color: "var(--blue)", text: "var(--on-accent)" };
const B = { name: "Player B", color: "var(--yellow)", text: "var(--on-yellow)" };

export function CompareView() {
  const { knownGames, targetGames, byName, label } = useCatalog();
  const [knownA, setKnownA] = useState(["Monopoly", "Risk"]);
  const [knownB, setKnownB] = useState(["Poker", "Chess"]);
  const [target, setTarget] = useState("Catan");
  const [level, setLevel] = useState<UserLevel>("intermediate");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [res, setRes] = useState<[LessonBundle, LessonBundle] | null>(null);

  const tog = (set: typeof setKnownA) => (n: string) => set((k) => (k.includes(n) ? k.filter((x) => x !== n) : [...k, n]));

  async function run() {
    setBusy(true);
    setErr(null);
    try {
      const goal = "understand the first turn";
      const [a, b] = await Promise.all([
        generateLesson({ known_games: knownA, target_game: target, user_level: level, learning_goal: goal }),
        generateLesson({ known_games: knownB, target_game: target, user_level: level, learning_goal: goal }),
      ]);
      setRes([a, b]);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const mechanics = byName(target)?.primary_mechanics ?? [];

  return (
    <div className="space-y-8">
      <header className="space-y-2">
        <h1 className="font-display text-4xl font-extrabold sm:text-5xl">Same game, two players.</h1>
        <p className="max-w-prose text-lg text-ink-soft">
          Give two players different backgrounds and watch the tutor change its examples and teaching order.
        </p>
      </header>

      <TargetPicker games={targetGames} value={target} onChange={setTarget} />

      <div className="grid gap-6 md:grid-cols-2">
        {([[A, knownA, setKnownA], [B, knownB, setKnownB]] as const).map(([p, k, set]) => (
          <div key={p.name} className="panel p-4" style={{ borderTop: `8px solid ${p.color}` }}>
            <h2 className="mb-3 flex items-center gap-2 font-display text-xl font-semibold">
              <Meeple color={p.color} size={24} /> {p.name} knows
            </h2>
            <KnownGamesPicker games={knownGames} selected={k} onToggle={tog(set)} accent={p.color} accentText={p.text} compact />
          </div>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <Segmented label="Experience" value={level} options={LEVELS} onChange={setLevel} />
        <button className="btn btn-primary px-6 py-3 text-lg" onClick={run} disabled={busy || !knownA.length || !knownB.length}>
          {busy ? <Spinner label="Teaching both" /> : `Teach both ${target}`}
        </button>
      </div>
      {err && <Notice tone="error">Couldn't build both lessons: {err}</Notice>}

      {res && (
        <>
          <section className="tile overflow-x-auto p-5">
            <h2 className="font-display text-2xl font-extrabold">What changed</h2>
            <p className="mt-1 text-sm text-ink-soft">
              Each row is a core mechanic of {target}. The cell shows which of the player's games the tutor uses to explain it.
            </p>
            <table className="mt-4 w-full min-w-[32rem] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b-2 border-ink">
                  <th className="py-2 pr-4 font-display">Mechanic</th>
                  <th className="py-2 pr-4 font-display"><span className="inline-flex items-center gap-1.5"><Meeple color={A.color} size={16} />{A.name}</span></th>
                  <th className="py-2 font-display"><span className="inline-flex items-center gap-1.5"><Meeple color={B.color} size={16} />{B.name}</span></th>
                </tr>
              </thead>
              <tbody>
                {mechanics.map((m) => {
                  const a = res[0].recommendation.data.per_mechanic.find((x) => x.mechanic === m);
                  const b = res[1].recommendation.data.per_mechanic.find((x) => x.mechanic === m);
                  const differ = a?.best_known_game !== b?.best_known_game;
                  return (
                    <tr key={m} className="border-b border-sunk">
                      <td className="py-2 pr-4 font-bold">{label(m)}</td>
                      {[a, b].map((x, i) => (
                        <td key={i} className="py-2 pr-4">
                          {x ? (
                            <span className="rounded-full border-2 border-ink px-2 py-0.5 font-bold" style={{ background: differ ? (i ? B.color : A.color) : "var(--surface)", color: differ ? (i ? B.text : A.text) : "var(--ink)" }}>
                              {x.best_known_game}
                            </span>
                          ) : (
                            <span className="text-ink-soft">taught from scratch</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  );
                })}
                <tr>
                  <td className="py-2 pr-4 font-bold">Closest overall</td>
                  {res.map((r, i) => (
                    <td key={i} className="py-2 pr-4">
                      {r.recommendation.data.top_overall}{" "}
                      <span className="tabular-nums text-ink-soft">({Math.round(r.recommendation.data.top_overall_score * 100)}% overlap)</span>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </section>

          <div className="grid gap-8 lg:grid-cols-2">
            {res.map((r, i) => {
              const p = i ? B : A;
              return (
                <div key={i} className="space-y-4">
                  <div className="flex items-center gap-2">
                    <Meeple color={p.color} size={28} />
                    <span className="font-display text-lg font-semibold">{p.name}'s lesson</span>
                    <span className="ml-auto"><OriginBadge origin={r.recommendation.origin} ms={r.totalMs} /></span>
                  </div>
                  <div className="panel p-5" style={{ borderTop: `8px solid ${p.color}` }}>
                    <LessonBody lesson={r.lesson} accent={p.color} />
                  </div>
                  <Comparisons lesson={r.lesson} accent={p.color} accentText={p.text} />
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
