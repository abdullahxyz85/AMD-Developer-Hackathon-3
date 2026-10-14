import { useEffect, useRef, useState } from "react";
import type { AnimationPlan, SceneType, VisualStatus } from "../api/types";
import { renderStatus, resolveUrl, startRender } from "../api/client";
import { Spinner } from "./ui";

// The lesson's animation_plan is treated as untrusted data: only known
// scene_types map to the trusted templates below; anything else gets
// plain step cards. No model output is ever executed.
const SUPPORTED: SceneType[] = ["dice_production", "route_claim", "deck_cycle", "step_cards"];

function validPlan(p: AnimationPlan | null): AnimationPlan | null {
  if (!p || !Array.isArray(p.steps) || !p.steps.length) return null;
  const steps = p.steps
    .filter((s) => s && typeof s.caption === "string")
    .slice(0, 12)
    .map((s, i) => ({
      label: String(s.label ?? `Step ${i + 1}`).slice(0, 24),
      caption: String(s.caption).slice(0, 280),
      duration: Math.min(Math.max(Number(s.duration) || 2.5, 1), 8),
      highlight: Array.isArray(s.highlight) ? s.highlight.map(String) : [],
    }));
  if (!steps.length) return null;
  return { scene_type: SUPPORTED.includes(p.scene_type) ? p.scene_type : "step_cards", title: String(p.title ?? "How it works"), steps };
}

export function VisualPlayer({ plan: rawPlan }: { plan: AnimationPlan | null }) {
  const plan = validPlan(rawPlan);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [render, setRender] = useState<VisualStatus | null>(null);
  const [mode, setMode] = useState<"interactive" | "video">("interactive");
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    setStep(0);
    setPlaying(!window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, [rawPlan]);

  // Ask the backend renderer for a Manim video, if one exists.
  useEffect(() => {
    let cancelled = false;
    setRender(null);
    setMode("interactive");
    if (!plan) return;
    (async () => {
      const job = await startRender(plan);
      if (!job || cancelled) return;
      setRender(job);
      let s = job;
      for (let i = 0; i < 60 && !cancelled && (s.status === "queued" || s.status === "rendering"); i++) {
        await new Promise((r) => setTimeout(r, 2000));
        const next = await renderStatus(job.id);
        if (!next) break;
        s = next;
        if (!cancelled) setRender(next);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rawPlan]);

  useEffect(() => {
    if (!plan || !playing) return;
    const d = (plan.steps[step].duration ?? 2.5) * 1000;
    timer.current = window.setTimeout(() => {
      if (step < plan.steps.length - 1) setStep(step + 1);
      else setPlaying(false);
    }, d);
    return () => clearTimeout(timer.current);
  }, [plan, step, playing]);

  if (!plan) {
    return (
      <div className="panel p-4 text-sm text-ink-soft">
        No visual for this lesson yet. The renderer only draws mechanics it has a template for.
      </div>
    );
  }

  const cur = plan.steps[step];
  const hl = new Set(cur.highlight);
  const video = render?.status === "done" && render.video_url ? resolveUrl(render.video_url) : null;

  return (
    <figure className="tile overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b-2 border-ink px-4 py-2">
        <figcaption className="font-display text-lg font-semibold">{plan.title}</figcaption>
        {render && (render.status === "queued" || render.status === "rendering") && (
          <span className="text-xs text-ink-soft"><Spinner label="Rendering video" /></span>
        )}
        {video && (
          <div className="flex gap-1 text-xs font-bold">
            {(["interactive", "video"] as const).map((m) => (
              <button key={m} onClick={() => setMode(m)} className="rounded-full border-2 border-ink px-2 py-0.5 capitalize"
                style={mode === m ? { background: "var(--ink)", color: "var(--paper)" } : undefined}>
                {m === "video" ? "Manim video" : "Step-through"}
              </button>
            ))}
          </div>
        )}
      </div>

      {mode === "video" && video ? (
        <video src={video} controls autoPlay className="aspect-video w-full bg-black" />
      ) : (
        <>
          <div className="bg-sunk">
            {plan.scene_type === "dice_production" && <DiceScene step={step} hl={hl} />}
            {plan.scene_type === "route_claim" && <RouteScene step={step} hl={hl} />}
            {plan.scene_type === "deck_cycle" && <DeckScene step={step} hl={hl} />}
            {plan.scene_type === "step_cards" && <CardsScene label={cur.label} index={step} total={plan.steps.length} />}
          </div>
          <p className="min-h-[4.5rem] px-4 pt-3 text-[15px]" aria-live="polite">
            {cur.caption}
          </p>
          <div className="flex items-center gap-3 px-4 pb-4 pt-2">
            <button className="btn px-3 py-1 text-sm" onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0} aria-label="Previous step">
              ‹
            </button>
            <button
              className="btn btn-primary px-4 py-1 text-sm"
              onClick={() => {
                if (!playing && step === plan.steps.length - 1) setStep(0);
                setPlaying(!playing);
              }}
            >
              {playing ? "Pause" : step === plan.steps.length - 1 ? "Replay" : "Play"}
            </button>
            <button className="btn px-3 py-1 text-sm" onClick={() => setStep(Math.min(plan.steps.length - 1, step + 1))} disabled={step === plan.steps.length - 1} aria-label="Next step">
              ›
            </button>
            <ol className="ml-auto flex gap-1.5" aria-label="Steps">
              {plan.steps.map((s, i) => (
                <li key={i}>
                  <button
                    onClick={() => { setStep(i); setPlaying(false); }}
                    aria-current={i === step}
                    title={s.label}
                    className="h-3 w-3 rounded-full border-2 border-ink"
                    style={{ background: i <= step ? "var(--ink)" : "transparent" }}
                  >
                    <span className="sr-only">{s.label}</span>
                  </button>
                </li>
              ))}
            </ol>
          </div>
        </>
      )}
      {render?.status === "failed" && (
        <p className="px-4 pb-3 text-xs text-ink-soft">Video render failed, so you're seeing the step-through version.</p>
      )}
    </figure>
  );
}

// ── Shared bits ─────────────────────────────────────────────────────────
const cls = (on: boolean, any: boolean) => (any && !on ? "dim" : "");

function hexPoints(cx: number, cy: number, r: number) {
  return Array.from({ length: 6 }, (_, k) => {
    const a = ((-90 + 60 * k) * Math.PI) / 180;
    return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`;
  }).join(" ");
}
function vertex(cx: number, cy: number, r: number, k: number) {
  const a = ((-90 + 60 * k) * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)] as const;
}

function Die({ x, y, n, roll }: { x: number; y: number; n: number; roll: boolean }) {
  const P: Record<number, [number, number][]> = {
    3: [[-9, -9], [0, 0], [9, 9]],
    4: [[-9, -9], [9, -9], [-9, 9], [9, 9]],
    5: [[-9, -9], [9, -9], [0, 0], [-9, 9], [9, 9]],
  };
  return (
    <g style={{ transform: `translate(${x}px, ${y}px) rotate(${roll ? 0 : -25}deg)` }}>
      <rect x={-18} y={-18} width={36} height={36} rx={7} fill="var(--surface)" stroke="var(--ink)" strokeWidth={2.5} />
      {P[n].map(([px, py], i) => <circle key={i} cx={px} cy={py} r={3.6} fill="var(--ink)" />)}
    </g>
  );
}

function House({ x, y, color, city = false }: { x: number; y: number; color: string; city?: boolean }) {
  const d = city
    ? "M-12 8V-4l6-6 6 6V-2h12V8z"
    : "M-8 8V-2l8-8 8 8V8z";
  return <path d={d} transform={`translate(${x} ${y})`} fill={color} stroke="var(--ink)" strokeWidth={2.2} strokeLinejoin="round" />;
}

function Badge({ x, y, text, show, color = "var(--surface)" }: { x: number; y: number; text: string; show: boolean; color?: string }) {
  const fg = color === "var(--yellow)" ? "var(--on-yellow)" : "var(--ink)";
  return (
    <g style={{ opacity: show ? 1 : 0, transform: `translate(${x}px, ${show ? y : y + 10}px)` }}>
      <rect x={-30} y={-13} width={60} height={26} rx={13} fill={color} stroke="var(--ink)" strokeWidth={2} />
      <text textAnchor="middle" y={5} fontSize={13} fontWeight={700} fill={fg} fontFamily="var(--font-display)">{text}</text>
    </g>
  );
}

// ── Catan: dice production ──────────────────────────────────────────────
const R = 46;
const RES: Record<string, string> = { grain: "var(--yellow)", wool: "var(--wool)", brick: "var(--brick)", wood: "var(--green)", ore: "var(--ore)" };
const HEXES = [
  { id: "c", res: "ore", n: 5, a: null as number | null },
  { id: "hex-8", res: "grain", n: 8, a: 0 },
  { id: "h1", res: "wool", n: 3, a: 60 },
  { id: "hex-6", res: "brick", n: 6, a: 120 },
  { id: "h3", res: "wood", n: 10, a: 180 },
  { id: "hex-8b", res: "wood", n: 8, a: 240 },
  { id: "h5", res: "grain", n: 4, a: 300 },
].map((h) => {
  const cx = 210, cy = 160;
  if (h.a === null) return { ...h, x: cx, y: cy };
  const r = (h.a * Math.PI) / 180;
  return { ...h, x: cx + Math.sqrt(3) * R * Math.cos(r), y: cy + Math.sqrt(3) * R * Math.sin(r) };
});

function DiceScene({ step, hl }: { step: number; hl: Set<string> }) {
  const byId = Object.fromEntries(HEXES.map((h) => [h.id, h]));
  const h8 = byId["hex-8"], h8b = byId["hex-8b"], h6 = byId["hex-6"], h3 = byId["h1"];
  const s1 = vertex(h8.x, h8.y, R, 0); // red settlement, top of grain 8
  const c1 = vertex(h8b.x, h8b.y, R, 3); // blue city, bottom of wood 8
  const s2 = vertex(h6.x, h6.y, R, 2); // blue settlement on brick 6
  const producing = step >= 1 && step <= 2;
  const robberAt = step >= 4 ? h8 : h3;
  const any = hl.size > 0;
  const odds = step === 3;

  return (
    <svg viewBox="0 0 420 320" className="scene block w-full" role="img" aria-label="Catan board: seven resource hexes with number tokens, two dice, settlements and the robber">
      {HEXES.map((h) => {
        const is8 = h.n === 8;
        const on =
          (hl.has("hex-8") && is8) || (hl.has("hex-6") && h.n === 6) || (hl.has("settlements") && is8) || hl.has(h.id) || (hl.has("robber") && h === robberAt);
        const glow = (producing && is8) || (odds && (h.n === 6 || h.n === 8));
        return (
          <g key={h.id} className={cls(on, any && !hl.has("dice"))}>
            <polygon points={hexPoints(h.x, h.y, R - 1.5)} fill={RES[h.res]} stroke="var(--ink)" strokeWidth={glow ? 5 : 2.5} strokeLinejoin="round" />
            <circle cx={h.x} cy={h.y} r={15} fill="var(--surface)" stroke="var(--ink)" strokeWidth={2} />
            <text x={h.x} y={h.y + 5.5} textAnchor="middle" fontSize={16} fontWeight={800} fontFamily="var(--font-display)"
              fill={h.n === 6 || h.n === 8 ? "var(--red)" : "var(--ink)"}>{h.n}</text>
          </g>
        );
      })}
      <House x={s1[0]} y={s1[1]} color="var(--red)" />
      <House x={c1[0]} y={c1[1]} color="var(--blue)" city />
      <House x={s2[0]} y={s2[1]} color="var(--blue)" />
      <Badge x={s1[0] + 40} y={s1[1] - 14} text="+1 grain" show={step === 2} />
      <Badge x={c1[0] - 44} y={c1[1] + 16} text="+2 wood" show={step === 2} />

      {/* robber */}
      <g style={{ transform: `translate(${robberAt.x + 20}px, ${robberAt.y - 4}px)` }} className={step === 4 ? "" : any && !hl.has("robber") ? "dim" : ""}>
        <ellipse cx={0} cy={18} rx={10} ry={4} fill="var(--ink)" opacity={0.3} />
        <path d="M0 -16a7 7 0 0 1 7 7c0 2-1 4-2 5 4 2 6 7 6 14v8H-11v-8c0-7 2-12 6-14-1-1-2-3-2-5a7 7 0 0 1 7-7z" fill="var(--ink-soft)" stroke="var(--ink)" strokeWidth={2} />
      </g>

      {/* dice */}
      <g className={any && !hl.has("dice") && step !== 4 ? "dim" : ""}>
        <Die x={42} y={44} n={3} roll={step !== 4} />
        <Die x={86} y={50} n={step === 4 ? 4 : 5} roll={step !== 4} />
        <text x={64} y={92} textAnchor="middle" fontSize={14} fontWeight={700} fill="var(--ink)" fontFamily="var(--font-display)">
          = {step === 4 ? 7 : 8}
        </text>
      </g>
      {odds && (
        <g>
          {[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((n, i) => {
            const ways = 6 - Math.abs(7 - n);
            return (
              <g key={n}>
                <rect x={300 + i * 10} y={300 - ways * 10} width={8} height={ways * 10} fill={n === 6 || n === 8 ? "var(--red)" : n === 7 ? "var(--ink-soft)" : "var(--ink)"} />
              </g>
            );
          })}
          <text x={355} y={316} textAnchor="middle" fontSize={10} fill="var(--ink)">2 … 7 … 12</text>
        </g>
      )}
    </svg>
  );
}

// ── Ticket to Ride: claim a route ───────────────────────────────────────
const CITIES = { Portside: [70, 70], Kestrel: [330, 50], Millbrook: [200, 180], Ashby: [370, 190] } as const;
type City = keyof typeof CITIES;
const ROUTES: { from: City; to: City; color: string; len: number; id: string }[] = [
  { id: "a", from: "Portside", to: "Kestrel", color: "var(--red)", len: 4 },
  { id: "route", from: "Portside", to: "Millbrook", color: "var(--blue)", len: 3 },
  { id: "c", from: "Millbrook", to: "Ashby", color: "var(--green)", len: 2 },
  { id: "d", from: "Kestrel", to: "Ashby", color: "var(--yellow)", len: 2 },
];

function RouteScene({ step, hl }: { step: number; hl: Set<string> }) {
  const any = hl.size > 0;
  const claimed = step >= 2;
  const hand = [
    { c: "var(--blue)", use: true },
    { c: "var(--blue)", use: true },
    { c: "loco", use: true },
    { c: "var(--yellow)", use: false },
    { c: "var(--green)", use: false },
  ];
  return (
    <svg viewBox="0 0 440 330" className="scene block w-full" role="img" aria-label="Map with four cities and coloured routes, and a hand of train cards">
      {ROUTES.map((r) => {
        const [x1, y1] = CITIES[r.from];
        const [x2, y2] = CITIES[r.to];
        const ang = (Math.atan2(y2 - y1, x2 - x1) * 180) / Math.PI;
        const dist = Math.hypot(x2 - x1, y2 - y1) - 36;
        const seg = dist / r.len;
        const target = r.id === "route";
        const on = target && (hl.has("route") || hl.has("trains"));
        return (
          <g key={r.id} className={cls(on, any && !hl.has("hand") && !hl.has("score"))}
            transform={`translate(${x1} ${y1}) rotate(${ang}) translate(18 0)`}>
            {Array.from({ length: r.len }, (_, i) => (
              <rect key={i} x={i * seg + 2} y={-8} width={seg - 4} height={16} rx={3}
                fill={target && claimed ? "var(--red)" : r.color}
                fillOpacity={target && claimed ? 1 : 0.55}
                stroke="var(--ink)" strokeWidth={2}
                style={target && claimed ? { transitionDelay: `${i * 120}ms` } : undefined} />
            ))}
          </g>
        );
      })}
      {(Object.keys(CITIES) as City[]).map((c) => (
        <g key={c}>
          <circle cx={CITIES[c][0]} cy={CITIES[c][1]} r={11} fill="var(--surface)" stroke="var(--ink)" strokeWidth={2.5} />
          <text x={CITIES[c][0]} y={CITIES[c][1] + (c === "Millbrook" || c === "Ashby" ? 30 : -17)} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">{c}</text>
        </g>
      ))}
      {step === 3 && (
        <g>
          <Badge x={120} y={150} text="Taken" show color="var(--surface)" />
          <path d="M150 140l14-10" stroke="var(--ink)" strokeWidth={2} />
        </g>
      )}
      <Badge x={145} y={112} text="+4 pts" show={step === 4} color="var(--yellow)" />

      {/* hand */}
      <g className={any && !hl.has("hand") && step !== 1 ? "dim" : ""}>
        {hand.map((card, i) => {
          const gone = claimed && card.use;
          const lift = step === 1 && card.use;
          return (
            <g key={i} style={{ transform: `translate(${120 + i * 42}px, ${gone ? 250 : lift ? 262 : 272}px)`, opacity: gone ? 0 : 1 }}>
              <rect width={36} height={52} rx={5} fill={card.c === "loco" ? "var(--surface)" : card.c} stroke="var(--ink)" strokeWidth={2.5} />
              {card.c === "loco" && (
                <g>
                  {["var(--red)", "var(--yellow)", "var(--green)", "var(--blue)"].map((c, k) => (
                    <rect key={k} x={6} y={8 + k * 9} width={24} height={7} fill={c} />
                  ))}
                </g>
              )}
            </g>
          );
        })}
      </g>
    </svg>
  );
}

// ── Dominion: deck cycle ────────────────────────────────────────────────
function Pile({ x, y, label, count, on, dim }: { x: number; y: number; label: string; count?: number; on?: boolean; dim?: boolean }) {
  return (
    <g className={dim ? "dim" : on ? "" : ""} transform={`translate(${x} ${y})`}>
      {[2, 1, 0].map((k) => (
        <rect key={k} x={k * 3} y={-k * 3} width={58} height={80} rx={6} fill="var(--surface)" stroke="var(--ink)" strokeWidth={on ? 3.5 : 2} />
      ))}
      <text x={29} y={44} textAnchor="middle" fontSize={20} fontWeight={800} fontFamily="var(--font-display)" fill="var(--ink)">{count ?? ""}</text>
      <text x={29} y={102} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">{label}</text>
    </g>
  );
}

function DeckScene({ step, hl }: { step: number; hl: Set<string> }) {
  const any = hl.size > 0;
  const cards = [
    { name: "Copper", c: "var(--brick)", kind: "treasure" },
    { name: "Copper", c: "var(--brick)", kind: "treasure" },
    { name: "Village", c: "var(--surface)", kind: "action" },
    { name: "Estate", c: "var(--green)", kind: "victory" },
    { name: "Copper", c: "var(--brick)", kind: "treasure" },
  ];
  const discarded = step >= 3;
  const reshuffled = step >= 4;
  return (
    <svg viewBox="0 0 440 330" className="scene block w-full" role="img" aria-label="Deck, hand of five cards, shared supply and discard pile">
      <Pile x={24} y={40} label="Your deck" count={reshuffled ? 11 : 0} on={hl.has("deck")} dim={any && !hl.has("deck") && !hl.has("hand")} />
      <Pile x={358} y={40} label="Discard" count={reshuffled ? 0 : discarded ? 11 : 5} on={hl.has("discard")} dim={any && !hl.has("discard") && !hl.has("deck")} />
      {/* supply */}
      <g className={any && !hl.has("supply") ? "dim" : ""}>
        {[
          { n: "Silver", cost: 3, c: "var(--ore)" },
          { n: "Smithy", cost: 4, c: "var(--surface)" },
          { n: "Province", cost: 8, c: "var(--green)" },
        ].map((s, i) => {
          const pick = step === 2 && s.n === "Silver";
          return (
            <g key={s.n} transform={`translate(${130 + i * 62} 30)`}>
              <rect width={52} height={70} rx={5} fill={s.c} stroke="var(--ink)" strokeWidth={pick ? 4 : 2} className={pick ? "pulse" : ""} />
              <text x={26} y={40} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--ink)">{s.n}</text>
              <circle cx={12} cy={60} r={8} fill="var(--yellow)" stroke="var(--ink)" strokeWidth={1.5} />
              <text x={12} y={64} textAnchor="middle" fontSize={10} fontWeight={800} fill="var(--ink)">{s.cost}</text>
            </g>
          );
        })}
        <text x={222} y={118} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">Shared supply</text>
      </g>
      {/* hand */}
      <g>
        {cards.map((card, i) => {
          const isAction = card.kind === "action";
          const on = (hl.has("hand") && step === 0) || (hl.has("action") && isAction) || (step === 2 && card.kind === "treasure");
          const x = discarded ? 362 : 82 + i * 56;
          const y = discarded ? 44 : isAction && step >= 1 ? 160 : 190;
          return (
            <g key={i} className={any && !on && !discarded ? "dim" : ""}
              style={{ transform: `translate(${x}px, ${y}px)`, opacity: discarded && !reshuffled ? 0.0 : reshuffled ? 0 : 1, transitionDelay: discarded ? `${i * 70}ms` : undefined }}>
              <rect width={50} height={72} rx={5} fill={card.c} stroke="var(--ink)" strokeWidth={2.5} />
              <text x={25} y={40} textAnchor="middle" fontSize={10.5} fontWeight={700} fill="var(--ink)">{card.name}</text>
            </g>
          );
        })}
        {!discarded && <text x={222} y={292} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">Your hand</text>}
      </g>
      <Badge x={222} y={150} text="3 coins" show={step === 2} color="var(--yellow)" />
      {reshuffled && (
        <g>
          <path d="M385 140 C 385 260, 60 260, 54 140" fill="none" stroke="var(--ink)" strokeWidth={3} strokeDasharray="6 6" markerEnd="url(#arr)" />
          <defs>
            <marker id="arr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
              <path d="M0 0L10 5L0 10z" fill="var(--ink)" />
            </marker>
          </defs>
          <text x={220} y={252} textAnchor="middle" fontSize={13} fontWeight={700} fill="var(--ink)">shuffle discards into a new deck</text>
        </g>
      )}
    </svg>
  );
}

function CardsScene({ label, index, total }: { label: string; index: number; total: number }) {
  return (
    <div className="flex aspect-[4/3] items-center justify-center p-6">
      <div className="tile flex h-full w-full max-w-xs flex-col items-center justify-center gap-2 text-center">
        <span className="text-sm text-ink-soft">Step {index + 1} of {total}</span>
        <span className="font-display text-3xl font-extrabold">{label}</span>
      </div>
    </div>
  );
}
