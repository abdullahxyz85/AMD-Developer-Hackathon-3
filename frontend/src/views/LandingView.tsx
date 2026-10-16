import { useMemo, useState } from "react";
import type { ViewId } from "../App";
import { useCatalog } from "../catalog";
import { VisualPlayer } from "../components/VisualPlayer";
import { Meeple, ScoreBar } from "../components/ui";
import { getGame } from "../demo/catalog";
import { animationPlan } from "../demo/lesson";
import { demoRecommend } from "../demo/recommender";

const REPO_URL = "https://github.com/abdullahxyz85/AMD-Developer-Hackathon-3";

// The three games with full lessons, visuals and quizzes.
const SHOWCASE = ["Catan", "Ticket to Ride", "Dominion"];
const HERO_KNOWN = ["Monopoly", "Chess", "Poker", "Risk", "Uno", "Scrabble", "Checkers"];

const PLAYER_A = { name: "Player A", knows: ["Monopoly", "Risk"], color: "var(--blue)", text: "var(--on-accent)" };
const PLAYER_B = { name: "Player B", knows: ["Poker", "Chess"], color: "var(--yellow)", text: "var(--on-yellow)" };

interface Props {
  onTeach: (target: string, known: string[]) => void;
  go: (v: ViewId) => void;
}

export function LandingView({ onTeach, go }: Props) {
  const link = (v: ViewId) => ({
    href: `#/${v}`,
    onClick: (e: React.MouseEvent) => {
      e.preventDefault();
      go(v);
    },
  });

  return (
    <div className="min-h-screen">
      <TopBar link={link} />
      <main>
        <Hero onTeach={onTeach} />
        <HowItWorks />
        <TwoPlayers link={link} />
        <SeeIt />
        <Grounded />
        <UnderTheHood />
        <FinalCall onTeach={onTeach} link={link} />
      </main>
      <Footer link={link} />
    </div>
  );
}

type LinkFn = (v: ViewId) => { href: string; onClick: (e: React.MouseEvent) => void };

// ── Top bar ─────────────────────────────────────────────────────────────
function TopBar({ link }: { link: LinkFn }) {
  return (
    <header className="border-b-2 border-ink bg-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-8">
        <a {...link("home")} className="flex items-center gap-2.5">
          <Meeple color="var(--red)" size={30} />
          <span className="font-display text-lg font-extrabold leading-none">Board-Game Tutor</span>
        </a>
        <nav aria-label="Page" className="flex items-center gap-1 sm:gap-5">
          <a href="#how" onClick={scrollTo("how")} className="hidden font-display font-semibold hover:underline sm:inline">How it works</a>
          <a href="#players" onClick={scrollTo("players")} className="hidden font-display font-semibold hover:underline md:inline">Two players</a>
          <a {...link("learn")} className="btn btn-primary px-4 py-1.5 text-sm">Open the tutor</a>
        </nav>
      </div>
    </header>
  );
}

function scrollTo(id: string) {
  return (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
}

function Section({ id, children, className = "" }: { id?: string; children: React.ReactNode; className?: string }) {
  return (
    <section id={id} className={`scroll-mt-4 border-b-2 border-ink ${className}`}>
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-8 sm:py-20">{children}</div>
    </section>
  );
}

// ── Hero: a live translation of the target game into the player's games ─
function Hero({ onTeach }: { onTeach: Props["onTeach"] }) {
  const { label } = useCatalog();
  const [known, setKnown] = useState<string[]>(["Monopoly"]);
  const [target, setTarget] = useState("Catan");

  const rec = useMemo(() => (known.length ? demoRecommend(known, target) : null), [known, target]);
  const game = getGame(target);
  const mechanics = game?.primary_mechanics ?? [];
  const curated = rec?.per_mechanic.find((m) => !m.why_it_helps.includes("provides a useful mental model"));

  const toggle = (n: string) => setKnown((k) => (k.includes(n) ? k.filter((x) => x !== n) : [...k, n]));

  return (
    <Section className="bg-paper">
      <div className="grid items-start gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,30rem)] lg:gap-14">
        <div className="space-y-6 lg:pt-6">
          <h1 className="font-display text-[2.6rem] font-extrabold leading-[1.02] sm:text-6xl">
            Learn a new board game through the ones you already play.
          </h1>
          <p className="max-w-xl text-lg text-ink-soft sm:text-xl">
            Tell the tutor which games you know. It explains the new one in their terms, from the real rules, with a step-by-step visual and a quick quiz at the end.
          </p>
          <p className="max-w-xl text-ink-soft">
            Try it here: pick what you've played and see how the tutor would map the new game onto it.
          </p>
        </div>

        <div className="tile p-5 sm:p-6" aria-live="polite">
          <fieldset>
            <legend className="font-display text-lg font-semibold">I've played</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {HERO_KNOWN.map((n) => {
                const on = known.includes(n);
                return (
                  <button key={n} aria-pressed={on} onClick={() => toggle(n)}
                    className="game-box px-3 py-1 font-display text-sm font-semibold"
                    style={on ? { background: "var(--yellow)", color: "var(--on-yellow)" } : undefined}>
                    {n}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <fieldset className="mt-5">
            <legend className="font-display text-lg font-semibold">and I want to learn</legend>
            <div role="radiogroup" aria-label="Game to learn" className="mt-2 flex flex-wrap gap-2">
              {SHOWCASE.map((n) => {
                const on = n === target;
                return (
                  <button key={n} role="radio" aria-checked={on} onClick={() => setTarget(n)}
                    className="rounded-full border-2 border-ink px-3 py-1 font-display text-sm font-semibold"
                    style={on ? { background: "var(--ink)", color: "var(--paper)" } : { background: "var(--surface)" }}>
                    {n}
                  </button>
                );
              })}
            </div>
          </fieldset>

          <div className="mt-6 border-t-2 border-ink pt-4">
            {!rec ? (
              <p className="text-ink-soft">Pick at least one game you've played.</p>
            ) : (
              <>
                <p className="font-display text-xl font-semibold leading-snug">
                  {rec.top_overall === "(none)"
                    ? `None of those overlap with ${target}, so the tutor starts from the basics.`
                    : `${rec.top_overall} already covers ${Math.round(rec.top_overall_score * 100)}% of what ${target} asks of you.`}
                </p>
                <ul className="mt-4 space-y-2">
                  {mechanics.map((m) => {
                    const hit = rec.per_mechanic.find((x) => x.mechanic === m);
                    return (
                      <li key={m} className="flex items-center justify-between gap-3 text-[15px]">
                        <span className="font-bold">{label(m)}</span>
                        {hit ? (
                          <span className="rounded-full border-2 border-ink px-2 py-0.5 text-sm font-bold" style={{ background: "var(--yellow)", color: "var(--on-yellow)" }}>
                            like {hit.best_known_game}
                          </span>
                        ) : (
                          <span className="rounded-full border-2 border-dashed border-ink px-2 py-0.5 text-sm">new to you</span>
                        )}
                      </li>
                    );
                  })}
                </ul>
                {curated && <p className="mt-4 text-[15px] text-ink-soft">{curated.why_it_helps}</p>}
              </>
            )}
            <button className="btn btn-primary mt-5 w-full justify-center py-3 text-lg" disabled={!known.length} onClick={() => onTeach(target, known)}>
              Teach me {target}
            </button>
          </div>
        </div>
      </div>
    </Section>
  );
}

// ── How it works: a real three-step sequence ────────────────────────────
const STEPS = [
  {
    title: "Tell it what you play",
    body: "Pick the games you already know, the game you want to learn, and how much hobby-game experience you have.",
    color: "var(--yellow)",
    fg: "var(--on-yellow)",
  },
  {
    title: "It finds the overlap",
    body: "A recommendation engine compares mechanics and picks, for each rule of the new game, which of your games explains it best.",
    color: "var(--blue)",
    fg: "var(--on-accent)",
  },
  {
    title: "It teaches from the rulebook",
    body: "Rule passages are retrieved with their sources, then an AI tutor writes a lesson built on your games, with a visual and a short quiz.",
    color: "var(--red)",
    fg: "var(--on-accent)",
  },
];

function HowItWorks() {
  return (
    <Section id="how" className="bg-surface">
      <h2 className="font-display text-4xl font-extrabold sm:text-5xl">How it works</h2>
      <ol className="mt-10 grid gap-8 md:grid-cols-3 md:gap-6">
        {STEPS.map((s, i) => (
          <li key={s.title} className="relative">
            <span className="flex h-12 w-12 items-center justify-center rounded-full border-2 border-ink font-display text-xl font-extrabold"
              style={{ background: s.color, color: s.fg, boxShadow: "0 3px 0 var(--ink)" }}>
              {i + 1}
            </span>
            {i < STEPS.length - 1 && <span aria-hidden className="absolute left-14 right-0 top-6 hidden h-0.5 bg-ink md:block" />}
            <h3 className="mt-4 font-display text-2xl font-semibold">{s.title}</h3>
            <p className="mt-2 max-w-sm text-ink-soft">{s.body}</p>
          </li>
        ))}
      </ol>
    </Section>
  );
}

// ── Two players: the personalization proof ──────────────────────────────
function TwoPlayers({ link }: { link: LinkFn }) {
  const { label } = useCatalog();
  const target = "Catan";
  const a = useMemo(() => demoRecommend(PLAYER_A.knows, target), []);
  const b = useMemo(() => demoRecommend(PLAYER_B.knows, target), []);
  const mechanics = getGame(target)?.primary_mechanics ?? [];

  return (
    <Section id="players" className="bg-paper">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)] lg:gap-14">
        <div className="space-y-4">
          <h2 className="font-display text-4xl font-extrabold sm:text-5xl">Same game, two different lessons.</h2>
          <p className="text-lg text-ink-soft">
            Two people learning {target} don't need the same tutorial. Here's how the tutor anchors each rule for a Monopoly and Risk player versus a Poker and Chess player.
          </p>
          <a {...link("compare")} className="btn">Compare your own players</a>
        </div>

        <div className="tile overflow-x-auto p-4 sm:p-6">
          <h3 className="pb-3 font-display text-lg font-semibold">Learning {target}: what each rule is compared to</h3>
          <table className="w-full border-collapse text-left text-sm sm:text-base">
            <thead>
              <tr className="border-b-2 border-ink">
                <th scope="col" className="py-2 pr-3 font-display">Rule</th>
                {[PLAYER_A, PLAYER_B].map((p) => (
                  <th key={p.name} scope="col" className="py-2 pr-3 font-display">
                    <span className="inline-flex items-center gap-1.5"><Meeple color={p.color} size={18} />{p.name}</span>
                    <span className="block text-xs font-normal text-ink-soft">knows {p.knows.join(" and ")}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mechanics.map((m) => (
                <tr key={m} className="border-b border-sunk">
                  <th scope="row" className="py-2.5 pr-3 font-bold">{label(m)}</th>
                  {[[a, PLAYER_A], [b, PLAYER_B]].map(([rec, p], i) => {
                    const hit = (rec as typeof a).per_mechanic.find((x) => x.mechanic === m);
                    const pl = p as typeof PLAYER_A;
                    return (
                      <td key={i} className="py-2.5 pr-3">
                        {hit ? (
                          <span className="rounded-full border-2 border-ink px-2 py-0.5 text-sm font-bold" style={{ background: pl.color, color: pl.text }}>
                            {hit.best_known_game}
                          </span>
                        ) : (
                          <span className="text-ink-soft">from scratch</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
              <tr>
                <th scope="row" className="pt-3 pr-3 font-bold">Overlap</th>
                {[a, b].map((r, i) => (
                  <td key={i} className="pt-3 pr-3 text-sm tabular-nums">
                    <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
                      <ScoreBar value={r.top_overall_score} color={i ? PLAYER_B.color : PLAYER_A.color} />
                      <span>{Math.round(r.top_overall_score * 100)}% via {r.top_overall}</span>
                    </span>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </Section>
  );
}

// ── Visual ──────────────────────────────────────────────────────────────
function SeeIt() {
  const plan = useMemo(() => animationPlan("Catan", demoRecommend(["Monopoly"], "Catan")), []);
  return (
    <Section className="bg-surface">
      <div className="grid items-center gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,28rem)] lg:gap-14">
        <div className="space-y-4 lg:order-2">
          <h2 className="font-display text-4xl font-extrabold sm:text-5xl">See the rule happen.</h2>
          <p className="text-lg text-ink-soft">
            Some rules are easier to watch than to read. Each lesson comes with a short visual you can step through at your own pace, and the backend can render the same plan as a Manim animation.
          </p>
          <p className="text-ink-soft">This one shows how a single dice roll in Catan pays out resources to every player.</p>
        </div>
        <div className="lg:order-1">
          <VisualPlayer plan={plan} />
        </div>
      </div>
    </Section>
  );
}

// ── Grounding ───────────────────────────────────────────────────────────
function Grounded() {
  return (
    <Section className="bg-paper">
      <div className="grid gap-10 lg:grid-cols-2 lg:gap-14">
        <div className="space-y-4">
          <h2 className="font-display text-4xl font-extrabold sm:text-5xl">Every rule has a source.</h2>
          <p className="text-lg text-ink-soft">
            The tutor only teaches what it can find in its rules library, and each part of a lesson links to where it came from.
          </p>
          <p className="text-lg text-ink-soft">
            When it can't find the answer, it says so and points you to the rulebook instead of guessing.
          </p>
        </div>
        <div className="space-y-4">
          <div className="panel p-5">
            <p className="font-display text-lg font-semibold">What happens when I roll a 7?</p>
            <p className="mt-2 text-[15px]">
              A roll of 7 activates the robber: move it to a hex, steal one resource from a player on it, and that hex produces nothing until the robber moves.
              <a href="https://boardgamegeek.com/boardgame/13/catan" target="_blank" rel="noreferrer"
                className="ml-1 rounded-full border border-ink px-1.5 align-super text-[11px] font-bold no-underline hover:bg-ink hover:text-paper"
                title="Catan, BoardGameGeek: Dice Rolling">1</a>
            </p>
            <p className="mt-3 text-sm text-ink-soft">1. Catan, BoardGameGeek: Dice Rolling</p>
          </div>
          <div className="panel p-5" style={{ borderLeft: "8px solid var(--yellow)" }}>
            <p className="font-display text-lg font-semibold">What changes in the Seafarers expansion?</p>
            <p className="mt-2 text-[15px] text-ink-soft">I don't have reliable rules for that. Check the official rulebook.</p>
          </div>
        </div>
      </div>
    </Section>
  );
}

// ── Under the hood ──────────────────────────────────────────────────────
const PARTS = [
  {
    name: "Recommendation engine",
    body: "Scores each of your games against the new one, mechanic by mechanic, and explains why each comparison helps.",
  },
  {
    name: "Rules retrieval",
    body: "Hybrid keyword and vector search over curated rule cards, returning passages with citations and an 'I don't know' signal.",
  },
  {
    name: "AI tutor on AMD",
    body: "An LLM served from AMD's developer cloud writes the lesson. Its output is checked against a strict schema before you see it.",
  },
  {
    name: "Animations",
    body: "Lesson visuals follow a fixed set of scene templates, so they stay accurate. Manim renders them as video.",
  },
];

function UnderTheHood() {
  return (
    <Section className="bg-surface">
      <h2 className="font-display text-4xl font-extrabold sm:text-5xl">What's under the hood</h2>
      <div className="mt-10 grid gap-x-10 gap-y-8 sm:grid-cols-2">
        {PARTS.map((p) => (
          <div key={p.name} className="border-t-2 border-ink pt-4">
            <h3 className="font-display text-2xl font-semibold">{p.name}</h3>
            <p className="mt-2 max-w-md text-ink-soft">{p.body}</p>
          </div>
        ))}
      </div>
    </Section>
  );
}

// ── Final call to action ────────────────────────────────────────────────
function FinalCall({ onTeach, link }: { onTeach: Props["onTeach"]; link: LinkFn }) {
  return (
    <section className="border-b-2 border-ink" style={{ background: "var(--ink)", color: "var(--paper)" }}>
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-8 sm:py-20">
        <h2 className="max-w-2xl font-display text-4xl font-extrabold sm:text-5xl">Your next game night starts here.</h2>
        <p className="mt-3 max-w-xl text-lg opacity-80">Pick a game to learn. You'll choose the games you know on the next screen.</p>
        <div className="mt-8 flex flex-wrap gap-3">
          {SHOWCASE.map((g) => (
            <button key={g} className="btn px-5 py-2.5 text-lg" style={{ background: "var(--paper)", color: "var(--ink)", borderColor: "var(--paper)", boxShadow: "0 3px 0 var(--red)" }}
              onClick={() => onTeach(g, ["Monopoly", "Chess"])}>
              Learn {g}
            </button>
          ))}
          <a {...link("games")} className="btn px-5 py-2.5 text-lg" style={{ background: "transparent", color: "var(--paper)", borderColor: "var(--paper)", boxShadow: "none" }}>
            Browse all games
          </a>
        </div>
      </div>
    </section>
  );
}

// ── Footer ──────────────────────────────────────────────────────────────
function Footer({ link }: { link: LinkFn }) {
  const items: [ViewId, string][] = [
    ["learn", "Learn a game"],
    ["compare", "Compare players"],
    ["games", "Game shelf"],
    ["picks", "Picks for you"],
    ["shelf", "My shelf"],
    ["studio", "Videos"],
    ["submit", "Submit a game"],
  ];
  return (
    <footer className="bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col gap-6 px-4 py-10 sm:flex-row sm:items-start sm:justify-between sm:px-8">
        <div className="space-y-2">
          <span className="flex items-center gap-2">
            <Meeple color="var(--red)" size={24} />
            <span className="font-display font-extrabold">Board-Game Tutor</span>
          </span>
          <p className="max-w-xs text-sm text-ink-soft">Built for the AMD Developer Hackathon Act III.</p>
          <a href={REPO_URL} target="_blank" rel="noreferrer" className="inline-block text-sm font-bold underline decoration-2 underline-offset-2">Source on GitHub</a>
        </div>
        <nav aria-label="In the app">
          <ul className="grid grid-cols-2 gap-x-8 gap-y-2 text-sm">
            {items.map(([id, name]) => (
              <li key={id}><a {...link(id)} className="hover:underline">{name}</a></li>
            ))}
          </ul>
        </nav>
      </div>
    </footer>
  );
}
