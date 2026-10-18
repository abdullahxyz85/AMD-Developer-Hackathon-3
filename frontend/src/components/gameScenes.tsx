// Per-game step-through scenes and short key-rule lists.
//
// Each scene draws one game and advances through PHASES fixed stages; the
// lesson's steps (however many there are) are spread across those stages.
// Drawings are trusted templates: the lesson only supplies the captions.

export const PHASES = 4;

/** Map a lesson step to one of the scene's PHASES stages. */
export function phaseFor(step: number, total: number) {
  if (total <= 1) return 0;
  return Math.round((step * (PHASES - 1)) / (total - 1));
}

export const KEY_RULES: Record<string, string[]> = {
  Catan: [
    "Roll: matching hexes pay settlements 1, cities 2",
    "Roll a 7: move the robber; over 7 cards, discard half",
    "First to 10 victory points wins",
  ],
  "Ticket to Ride": [
    "Turn: draw 2 train cards, claim a route, or take tickets",
    "Claim a route with cards matching its colour and length",
    "Unfinished tickets cost points at the end",
  ],
  Dominion: [
    "Turn: Action, then Buy, then Clean-up",
    "Start with 7 Coppers + 3 Estates; draw 5",
    "Ends when Provinces or any 3 supply piles run out",
  ],
  Monopoly: [
    "Pass GO: collect $200",
    "Doubles: roll again (3 in a row sends you to Jail)",
    "Unowned property: buy it, or it goes to auction",
    "Own a full colour set to build houses",
  ],
  Risk: [
    "Reinforce: territories ÷ 3 armies (at least 3)",
    "Attacker rolls up to 3 dice, defender up to 2",
    "Compare highest dice; ties go to the defender",
  ],
  Uno: [
    "Match the top card's colour, number or symbol",
    "Can't play? Draw a card",
    "Say “UNO” at one card, or draw 2 as a penalty",
  ],
  Poker: [
    "Texas Hold'em: 2 private cards + 5 shared cards",
    "Best 5-card hand out of those 7 wins",
    "Each round: check, bet, call, raise or fold",
  ],
  Scrabble: [
    "First word covers the centre ★ (double word)",
    "New words must connect to tiles on the board",
    "Use all 7 tiles in one turn: +50 points",
  ],
  Chess: [
    "White moves first; each piece moves its own way",
    "Checkmate the king to win",
    "Special moves: castling, en passant, promotion",
  ],
  Checkers: [
    "Move diagonally forward on dark squares",
    "Captures are mandatory: jump over the piece",
    "Reach the far row to become a king (moves both ways)",
  ],
};

type SceneProps = { phase: number };

export const GAME_SCENES: Record<string, (p: SceneProps) => React.JSX.Element> = {
  Monopoly: MonopolyScene,
  Risk: RiskScene,
  Uno: UnoScene,
  Poker: PokerScene,
  Scrabble: ScrabbleScene,
  Chess: ChessScene,
  Checkers: CheckersScene,
};

// ── Shared bits ─────────────────────────────────────────────────────────
const FONT = "var(--font-display)";

function Pill({ x, y, text, show = true, color = "var(--yellow)", w = 0 }: { x: number; y: number; text: string; show?: boolean; color?: string; w?: number }) {
  const width = w || Math.max(60, text.length * 7.6 + 22);
  const fg = color === "var(--yellow)" || color === "var(--surface)" ? "var(--on-yellow)" : "var(--on-accent)";
  return (
    <g style={{ opacity: show ? 1 : 0, transform: `translate(${x}px, ${show ? y : y + 10}px)` }}>
      <rect x={-width / 2} y={-13} width={width} height={26} rx={13} fill={color} stroke="var(--ink)" strokeWidth={2} />
      <text textAnchor="middle" y={5} fontSize={13} fontWeight={700} fill={color === "var(--surface)" ? "var(--ink)" : fg} fontFamily={FONT}>{text}</text>
    </g>
  );
}

const PIPS: Record<number, [number, number][]> = {
  1: [[0, 0]],
  2: [[-8, -8], [8, 8]],
  3: [[-8, -8], [0, 0], [8, 8]],
  4: [[-8, -8], [8, -8], [-8, 8], [8, 8]],
  5: [[-8, -8], [8, -8], [0, 0], [-8, 8], [8, 8]],
  6: [[-8, -9], [8, -9], [-8, 0], [8, 0], [-8, 9], [8, 9]],
};

function Die({ x, y, n, color = "var(--surface)", pip = "var(--ink)", size = 32, dim = false }: { x: number; y: number; n: number; color?: string; pip?: string; size?: number; dim?: boolean }) {
  const s = size / 32;
  return (
    <g style={{ transform: `translate(${x}px, ${y}px) scale(${s})`, opacity: dim ? 0.35 : 1 }}>
      <rect x={-16} y={-16} width={32} height={32} rx={6} fill={color} stroke="var(--ink)" strokeWidth={2.5} />
      {PIPS[n].map(([px, py], i) => <circle key={i} cx={px} cy={py} r={3.3} fill={pip} />)}
    </g>
  );
}

// ── Monopoly: roll, move, pass GO, buy, build ───────────────────────────
// 16-space ring on a 5×5 grid, moving clockwise from GO (bottom right).
const M_CELL = 56, M_OX = 70, M_OY = 18;
const RING: [number, number][] = [
  [4, 4], [3, 4], [2, 4], [1, 4], [0, 4], [0, 3], [0, 2], [0, 1],
  [0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [4, 1], [4, 2], [4, 3],
];
const M_SPACES: { label?: string; color?: string }[] = [
  { label: "GO" }, { color: "var(--brick)" }, { label: "?" }, { color: "var(--brick)" },
  { label: "JAIL" }, { color: "var(--red)" }, { color: "var(--yellow)" }, { color: "var(--red)" },
  { label: "FREE" }, { color: "var(--blue)" }, { label: "?" }, { color: "var(--blue)" },
  { label: "TO JAIL" }, { color: "var(--green)" }, { label: "$" }, { color: "var(--green)" },
];
const mCenter = (i: number) => [M_OX + RING[i][0] * M_CELL + M_CELL / 2, M_OY + RING[i][1] * M_CELL + M_CELL / 2] as const;

function MonopolyScene({ phase }: SceneProps) {
  const at = phase === 0 ? 13 : 5; // roll 3 + 5 = 8: from space 13, past GO, to space 5
  const [tx, ty] = mCenter(at);
  const owned = phase >= 3;
  return (
    <svg viewBox="0 0 420 320" className="scene block w-full" role="img" aria-label="Monopoly-style board: a token rolls 8, passes GO, lands on a property and builds houses">
      {M_SPACES.map((s, i) => {
        const [c, r] = RING[i];
        const x = M_OX + c * M_CELL, y = M_OY + r * M_CELL;
        const target = i === 5 || (owned && i === 7);
        return (
          <g key={i}>
            <rect x={x} y={y} width={M_CELL} height={M_CELL} fill="var(--surface)" stroke="var(--ink)" strokeWidth={target && phase >= 2 ? 4 : 2} />
            {s.color && <rect x={x + 2} y={y + 2} width={M_CELL - 4} height={13} fill={s.color} stroke="var(--ink)" strokeWidth={1.2} />}
            {s.label && (
              <text x={x + M_CELL / 2} y={y + M_CELL / 2 + 5} textAnchor="middle" fontSize={s.label.length > 4 ? 10 : 14} fontWeight={800} fill={i === 0 ? "var(--red)" : "var(--ink)"} fontFamily={FONT}>{s.label}</text>
            )}
          </g>
        );
      })}
      {/* houses on the completed set */}
      {[5, 7].map((i) => {
        const [x, y] = mCenter(i);
        return (
          <g key={i} style={{ opacity: owned ? 1 : 0, transition: "opacity 400ms" }}>
            {[-12, 0, 12].map((dx) => (
              <path key={dx} d="M-5 6V-1l5-5 5 5V6z" transform={`translate(${x + dx} ${y + 10})`} fill="var(--green)" stroke="var(--ink)" strokeWidth={1.5} />
            ))}
          </g>
        );
      })}
      {/* token */}
      <g style={{ transform: `translate(${tx}px, ${ty + 6}px)`, transition: "transform 900ms cubic-bezier(.3,.7,.3,1)" }}>
        <circle r={11} fill="var(--blue)" stroke="var(--ink)" strokeWidth={2.5} />
      </g>
      {/* centre: dice, deed card, rent */}
      <g style={{ opacity: phase <= 1 ? 1 : 0, transition: "opacity 300ms" }}>
        <Die x={182} y={130} n={3} />
        <Die x={222} y={130} n={5} />
        <text x={202} y={172} textAnchor="middle" fontSize={15} fontWeight={800} fill="var(--ink)" fontFamily={FONT}>= 8 spaces</text>
      </g>
      <Pill x={mCenter(0)[0] - 4} y={mCenter(0)[1] - 44} text="+$200" show={phase === 1} />
      <g style={{ opacity: phase === 2 ? 1 : 0, transition: "opacity 300ms" }}>
        <rect x={160} y={98} width={84} height={104} rx={6} fill="var(--surface)" stroke="var(--ink)" strokeWidth={2.5} />
        <rect x={164} y={102} width={76} height={22} fill="var(--red)" stroke="var(--ink)" strokeWidth={1.5} />
        <text x={202} y={118} textAnchor="middle" fontSize={11} fontWeight={800} fill="var(--on-accent)" fontFamily={FONT}>TITLE DEED</text>
        <text x={202} y={146} textAnchor="middle" fontSize={12} fill="var(--ink)">Price $140</text>
        <text x={202} y={166} textAnchor="middle" fontSize={12} fill="var(--ink)">Rent $10</text>
        <text x={202} y={190} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--ink)">Buy or auction</text>
      </g>
      <Pill x={210} y={200} text="Full set → houses" show={owned} />
    </svg>
  );
}

// ── Risk: reinforce, roll, compare, conquer ─────────────────────────────
function RiskScene({ phase }: SceneProps) {
  const conquered = phase >= 3;
  const mine = phase === 0 ? 3 : phase === 1 ? 6 : phase === 2 ? 5 : 2;
  const theirs = phase <= 1 ? 2 : phase === 2 ? 1 : 3;
  const attack = [6, 4, 2], defend = [5, 4];
  return (
    <svg viewBox="0 0 420 320" className="scene block w-full" role="img" aria-label="Two neighbouring territories: the attacker rolls three dice against the defender's two">
      <path d="M30 60 L180 40 L205 120 L190 210 L60 230 L20 150 Z" fill="var(--blue)" fillOpacity={0.55} stroke="var(--ink)" strokeWidth={2.5} strokeLinejoin="round" />
      <path d="M205 120 L180 40 L330 50 L395 130 L360 230 L190 210 Z" fill={conquered ? "var(--blue)" : "var(--red)"} fillOpacity={0.55} stroke="var(--ink)" strokeWidth={2.5} strokeLinejoin="round" style={{ transition: "fill 500ms" }} />
      <text x={100} y={90} textAnchor="middle" fontSize={13} fontWeight={800} fill="var(--ink)" fontFamily={FONT}>Your territory</text>
      <text x={290} y={90} textAnchor="middle" fontSize={13} fontWeight={800} fill="var(--ink)" fontFamily={FONT}>{conquered ? "Now yours" : "Enemy"}</text>
      {[{ x: 100, n: mine, c: "var(--blue)" }, { x: 290, n: theirs, c: conquered ? "var(--blue)" : "var(--red)" }].map((a, i) => (
        <g key={i}>
          <circle cx={a.x} cy={135} r={22} fill={a.c} stroke="var(--ink)" strokeWidth={2.5} />
          <text x={a.x} y={142} textAnchor="middle" fontSize={20} fontWeight={800} fill="var(--on-accent)" fontFamily={FONT}>{a.n}</text>
        </g>
      ))}
      <Pill x={100} y={180} text="+3 armies" show={phase === 1} />
      {/* dice duel */}
      <g style={{ opacity: phase === 1 || phase === 2 ? 1 : 0, transition: "opacity 300ms" }}>
        {attack.map((n, i) => <Die key={i} x={150 + i * 40} y={265} n={n} color="var(--blue)" pip="var(--on-accent)" dim={phase === 2 && i === 2} />)}
        {defend.map((n, i) => <Die key={i} x={300 + i * 40} y={265} n={n} color="var(--red)" pip="var(--on-accent)" />)}
        <text x={190} y={302} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--ink)">attacker: up to 3</text>
        <text x={320} y={302} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--ink)">defender: up to 2</text>
      </g>
      <g style={{ opacity: phase === 2 ? 1 : 0, transition: "opacity 300ms" }}>
        <text x={40} y={252} fontSize={12} fontWeight={700} fill="var(--ink)">6 vs 5: you win</text>
        <text x={40} y={270} fontSize={12} fontWeight={700} fill="var(--ink)">4 vs 4: tie →</text>
        <text x={40} y={288} fontSize={12} fontWeight={700} fill="var(--red)">defender wins</text>
      </g>
      <Pill x={210} y={265} text="Territory taken: move armies in" show={conquered} />
    </svg>
  );
}

// ── Uno: match colour or number ─────────────────────────────────────────
type UnoCard = { c: string; t: string };
function UnoFace({ card, x, y, w = 46, h = 68, ring = false }: { card: UnoCard; x: number; y: number; w?: number; h?: number; ring?: boolean }) {
  const wild = card.c === "wild";
  return (
    <g style={{ transform: `translate(${x}px, ${y}px)` }}>
      <rect width={w} height={h} rx={7} fill={wild ? "#1b1b1b" : card.c} stroke="var(--ink)" strokeWidth={ring ? 4 : 2.5} />
      <ellipse cx={w / 2} cy={h / 2} rx={w * 0.36} ry={h * 0.3} fill="var(--surface)" transform={`rotate(-25 ${w / 2} ${h / 2})`} />
      {wild ? (
        ["var(--red)", "var(--yellow)", "var(--green)", "var(--blue)"].map((c, k) => (
          <rect key={k} x={w / 2 - 10 + (k % 2) * 10} y={h / 2 - 10 + Math.floor(k / 2) * 10} width={10} height={10} fill={c} />
        ))
      ) : (
        <text x={w / 2} y={h / 2 + 8} textAnchor="middle" fontSize={22} fontWeight={800} fill="var(--ink)" fontFamily={FONT}>{card.t}</text>
      )}
    </g>
  );
}

function UnoScene({ phase }: SceneProps) {
  const top: UnoCard = { c: "var(--red)", t: "7" };
  const hand: (UnoCard & { ok: boolean })[] = [
    { c: "var(--blue)", t: "7", ok: true },
    { c: "var(--red)", t: "2", ok: true },
    { c: "var(--green)", t: "4", ok: false },
    { c: "var(--yellow)", t: "⊘", ok: false },
    { c: "wild", t: "", ok: true },
  ];
  const played = phase >= 2;
  return (
    <svg viewBox="0 0 420 320" className="scene block w-full" role="img" aria-label="Uno: a discard pile topped by a red 7 and a hand of five cards; matching cards are played">
      {/* draw pile */}
      <g>
        {[4, 2, 0].map((k) => <rect key={k} x={110 + k} y={40 - k} width={58} height={86} rx={8} fill="#1b1b1b" stroke="var(--ink)" strokeWidth={2} />)}
        <text x={139} y={146} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">Draw pile</text>
      </g>
      {/* discard */}
      <UnoFace card={top} x={230} y={38} w={58} h={86} />
      <text x={259} y={146} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">Discard</text>
      {hand.map((card, i) => {
        const onPile = played && i === 1;
        const hidden = phase >= 3 && i !== 0 && !onPile;
        const lift = phase === 1 && card.ok;
        const x = onPile ? 230 : phase >= 3 ? 184 : 64 + i * 60;
        const y = onPile ? 38 : lift ? 186 : 204;
        return (
          <g key={i} style={{ transform: `translate(${x}px, ${y}px)`, opacity: hidden ? 0 : phase === 1 && !card.ok ? 0.35 : 1 }}>
            <UnoFace card={card} x={0} y={0} w={onPile ? 58 : 46} h={onPile ? 86 : 68} ring={lift} />
          </g>
        );
      })}
      <Pill x={206} y={292} text={phase === 1 ? "Same colour, same number, or wild" : "Your hand"} show={phase <= 1} color="var(--surface)" />
      <Pill x={300} y={180} text="Red on red ✓" show={phase === 2} />
      <Pill x={300} y={232} text="UNO!" show={phase >= 3} color="var(--red)" />
    </svg>
  );
}

// ── Poker (Texas Hold'em): deal, flop, turn & river, best five ──────────
type PCard = { r: string; s: string };
const RED_SUITS = new Set(["♥", "♦"]);
function PokerCard({ card, x, y, up, best = false, dim = false }: { card: PCard; x: number; y: number; up: boolean; best?: boolean; dim?: boolean }) {
  return (
    <g style={{ transform: `translate(${x}px, ${y}px)`, opacity: dim ? 0.35 : 1, transition: "opacity 400ms" }}>
      <rect width={44} height={62} rx={5} fill={up ? "var(--surface)" : "var(--blue)"} stroke={best ? "var(--yellow)" : "var(--ink)"} strokeWidth={best ? 4 : 2.2} />
      {up ? (
        <>
          <text x={22} y={28} textAnchor="middle" fontSize={18} fontWeight={800} fill={RED_SUITS.has(card.s) ? "var(--red)" : "var(--ink)"} fontFamily={FONT}>{card.r}</text>
          <text x={22} y={50} textAnchor="middle" fontSize={18} fill={RED_SUITS.has(card.s) ? "var(--red)" : "var(--ink)"}>{card.s}</text>
        </>
      ) : (
        <rect x={6} y={6} width={32} height={50} rx={3} fill="none" stroke="var(--surface)" strokeWidth={1.5} strokeDasharray="4 3" />
      )}
    </g>
  );
}

function PokerScene({ phase }: SceneProps) {
  const board: PCard[] = [{ r: "Q", s: "♦" }, { r: "J", s: "♣" }, { r: "4", s: "♠" }, { r: "10", s: "♥" }, { r: "2", s: "♣" }];
  const hole: PCard[] = [{ r: "A", s: "♠" }, { r: "K", s: "♥" }];
  const shown = phase === 0 ? 0 : phase === 1 ? 3 : 5;
  const best = phase >= 3;
  const inBest = (c: PCard) => ["A", "K", "Q", "J", "10"].includes(c.r);
  return (
    <svg viewBox="0 0 420 320" className="scene block w-full" role="img" aria-label="Poker table: two private cards and five shared cards dealt in stages">
      <ellipse cx={210} cy={150} rx={195} ry={125} fill="var(--green)" fillOpacity={0.45} stroke="var(--ink)" strokeWidth={3} />
      <text x={210} y={56} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">Shared cards</text>
      {board.map((c, i) => (
        <PokerCard key={i} card={c} x={93 + i * 48} y={66} up={i < shown} best={best && inBest(c)} dim={best && !inBest(c)} />
      ))}
      {/* pot */}
      <g style={{ opacity: phase >= 1 ? 1 : 0, transition: "opacity 300ms" }}>
        {[0, 1, 2].map((k) => <ellipse key={k} cx={210} cy={160 - k * 5} rx={16} ry={6} fill="var(--yellow)" stroke="var(--ink)" strokeWidth={1.5} />)}
        <text x={210} y={186} textAnchor="middle" fontSize={11} fontWeight={700} fill="var(--ink)">Pot</text>
      </g>
      {hole.map((c, i) => <PokerCard key={i} card={c} x={162 + i * 50} y={206} up best={best} />)}
      <text x={210} y={290} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">Your 2 private cards</text>
      <Pill x={330} y={160} text="Bet, call or fold" show={phase === 1 || phase === 2} color="var(--surface)" />
      <Pill x={330} y={160} text="Straight: A-K-Q-J-10" show={best} />
    </svg>
  );
}

// ── Scrabble: rack, first word on ★, double-word score, connect ─────────
const S_CELL = 30, S_OX = 75, S_OY = 6;
const LETTER_PTS: Record<string, number> = { B: 3, O: 1, A: 1, R: 1, D: 2, G: 2, M: 3, E: 1, T: 1, S: 1 };
function Tile({ l, x, y, ring = false }: { l: string; x: number; y: number; ring?: boolean }) {
  return (
    <g style={{ transform: `translate(${x}px, ${y}px)` }}>
      <rect width={S_CELL - 3} height={S_CELL - 3} rx={4} fill="var(--yellow)" stroke="var(--ink)" strokeWidth={ring ? 3 : 1.8} />
      <text x={12} y={19} textAnchor="middle" fontSize={15} fontWeight={800} fill="var(--on-yellow)" fontFamily={FONT}>{l}</text>
      <text x={22} y={24} textAnchor="middle" fontSize={7.5} fontWeight={700} fill="var(--on-yellow)">{LETTER_PTS[l] ?? 1}</text>
    </g>
  );
}

function ScrabbleScene({ phase }: SceneProps) {
  const premium: Record<string, string> = { "0,0": "TW", "8,0": "TW", "2,1": "DL", "6,5": "DL", "0,6": "TW", "8,6": "TW", "4,3": "★" };
  const word = "BOARD".split("").map((l, i) => ({ l, c: 2 + i, r: 3 }));
  const down = [{ l: "G", r: 2 }, { l: "M", r: 4 }, { l: "E", r: 5 }].map((t) => ({ ...t, c: 4 }));
  const rack = ["B", "O", "A", "R", "D", "S", "T"];
  const placed = phase >= 1;
  const at = (c: number, r: number) => [S_OX + c * S_CELL + 1.5, S_OY + r * S_CELL + 1.5] as const;
  return (
    <svg viewBox="0 0 420 320" className="scene block w-full" role="img" aria-label="Scrabble-style board: the first word covers the centre star, scores double, and a second word connects to it">
      {Array.from({ length: 7 }, (_, r) =>
        Array.from({ length: 9 }, (_, c) => {
          const p = premium[`${c},${r}`];
          const fill = p === "TW" ? "var(--red)" : p === "DL" ? "var(--blue)" : p === "★" ? "var(--brick)" : "var(--surface)";
          const glow = p === "★" && (phase === 0 || phase === 2);
          return (
            <g key={`${c},${r}`}>
              <rect x={S_OX + c * S_CELL} y={S_OY + r * S_CELL} width={S_CELL} height={S_CELL} fill={fill} fillOpacity={p ? 0.6 : 1} stroke="var(--ink)" strokeWidth={glow ? 3.5 : 1.2} />
              {p && <text x={S_OX + c * S_CELL + 15} y={S_OY + r * S_CELL + 19} textAnchor="middle" fontSize={p === "★" ? 16 : 9} fontWeight={800} fill="var(--ink)">{p}</text>}
            </g>
          );
        }),
      )}
      {placed && word.map((t, i) => { const [x, y] = at(t.c, t.r); return <Tile key={i} l={t.l} x={x} y={y} ring={phase === 2} />; })}
      {phase >= 3 && down.map((t, i) => { const [x, y] = at(t.c, t.r); return <Tile key={i} l={t.l} x={x} y={y} ring />; })}
      {/* rack */}
      <rect x={95} y={246} width={230} height={40} rx={5} fill="var(--brick)" fillOpacity={0.5} stroke="var(--ink)" strokeWidth={2} />
      {rack.map((l, i) => (
        <g key={i} style={{ opacity: placed && i < 5 ? 0 : 1, transition: "opacity 400ms" }}>
          <Tile l={l} x={103 + i * 31} y={252} />
        </g>
      ))}
      <text x={210} y={304} textAnchor="middle" fontSize={12} fontWeight={700} fill="var(--ink)">Your rack: 7 tiles</text>
      <Pill x={210} y={230} text="First word must cover ★" show={phase === 0} />
      <Pill x={210} y={230} text="(3+1+1+1+2) × 2 = 16" show={phase === 2} />
      <Pill x={210} y={230} text="New words connect: GAME" show={phase >= 3} />
    </svg>
  );
}

// ── Chess: knight's L-move, capture, checkmate (scholar's mate) ─────────
const C_CELL = 34, C_OX = 12, C_OY = 24;
const FILES = "abcdefgh";
const sq = (s: string) => [C_OX + FILES.indexOf(s[0]) * C_CELL, C_OY + (8 - Number(s[1])) * C_CELL] as const;
const SOLID: Record<string, string> = { K: "♚", Q: "♛", R: "♜", B: "♝", N: "♞", P: "♟" };
const OUTLINE: Record<string, string> = { K: "♔", Q: "♕", R: "♖", B: "♗", N: "♘", P: "♙" };
const TEXT = "︎"; // render as text, never as emoji

// Fixed board colours: real boards look the same in light and dark themes.
function Board({ children, light = "#ece4d0", dark = "#8f979c" }: { children: React.ReactNode; light?: string; dark?: string }) {
  return (
    <>
      {Array.from({ length: 64 }, (_, i) => {
        const c = i % 8, r = Math.floor(i / 8);
        return <rect key={i} x={C_OX + c * C_CELL} y={C_OY + r * C_CELL} width={C_CELL} height={C_CELL} fill={(c + r) % 2 ? dark : light} />;
      })}
      <rect x={C_OX} y={C_OY} width={8 * C_CELL} height={8 * C_CELL} fill="none" stroke="var(--ink)" strokeWidth={2.5} />
      {children}
    </>
  );
}

function ChessScene({ phase }: SceneProps) {
  const white = ["Ra1", "Nb1", "Bc1", "Ke1", "Ng1", "Rh1", "Bc4", "Pa2", "Pb2", "Pc2", "Pd2", "Pe4", "Pf2", "Pg2", "Ph2"];
  const black = ["Ra8", "Bc8", "Qd8", "Ke8", "Bf8", "Rh8", "Nc6", "Nf6", "Pa7", "Pb7", "Pc7", "Pd7", "Pe5", "Pg7", "Ph7"];
  if (phase < 2) black.push("Pf7");
  const queen = phase >= 2 ? "f7" : "h5";
  // White = cream solid glyph under a black outline glyph; black = solid glyph.
  // Fixed colours so pieces read the same in light and dark themes.
  const piece = (code: string, side: "w" | "b", key: string) => {
    const [x, y] = sq(code.slice(1));
    return (
      <g key={key} style={{ transform: `translate(${x + C_CELL / 2}px, ${y + C_CELL - 7}px)` }}>
        <text textAnchor="middle" fontSize={28} fill={side === "w" ? "#f5f1e6" : "#161616"}>{SOLID[code[0]]}{TEXT}</text>
        {side === "w" && <text textAnchor="middle" fontSize={28} fill="#161616">{OUTLINE[code[0]]}{TEXT}</text>}
      </g>
    );
  };
  const [kx, ky] = sq("e8");
  return (
    <svg viewBox="0 0 420 320" className="scene block w-full" role="img" aria-label="Chess board: a knight's L-shaped moves, then the queen captures on f7 for checkmate">
      <Board>
        {phase === 1 && ["f3", "h3", "e2"].map((s) => { const [x, y] = sq(s); return <circle key={s} cx={x + C_CELL / 2} cy={y + C_CELL / 2} r={7} fill="var(--green)" stroke="var(--ink)" strokeWidth={1.5} />; })}
        {phase >= 3 && <rect x={kx + 2} y={ky + 2} width={C_CELL - 4} height={C_CELL - 4} fill="none" stroke="var(--red)" strokeWidth={4} />}
        {white.map((p) => piece(p, "w", p))}
        {black.map((p) => piece(p, "b", p))}
        {piece(`Q${queen}`, "w", "wq")}
      </Board>
      <Pill x={352} y={48} text="White first" show={phase === 0} w={92} />
      <Pill x={352} y={48} text="Knight: L-shape" show={phase === 1} w={110} />
      <Pill x={352} y={48} text="Queen takes f7" show={phase === 2} w={110} />
      <Pill x={352} y={48} text="Checkmate!" show={phase >= 3} color="var(--red)" w={96} />
    </svg>
  );
}

// ── Checkers: diagonal step, mandatory jump, crown a king ───────────────
function CheckersScene({ phase }: SceneProps) {
  const hero = phase === 0 ? [2, 5] : phase === 1 ? [3, 4] : phase === 2 ? [5, 2] : [7, 0];
  const others: { c: number; r: number; red: boolean; gone?: boolean }[] = [
    { c: 0, r: 7, red: true }, { c: 4, r: 7, red: true }, { c: 6, r: 5, red: true }, { c: 1, r: 6, red: true },
    { c: 4, r: 3, red: false, gone: phase >= 2 }, { c: 1, r: 0, red: false }, { c: 3, r: 0, red: false }, { c: 0, r: 1, red: false }, { c: 2, r: 1, red: false },
  ];
  const disc = (c: number, r: number, red: boolean, king = false, key = "") => (
    <g key={key} style={{ transform: `translate(${C_OX + c * C_CELL + C_CELL / 2}px, ${C_OY + r * C_CELL + C_CELL / 2}px)`, transition: "transform 700ms cubic-bezier(.3,.7,.3,1)" }}>
      <circle r={13} fill={red ? "var(--red)" : "#1b1b1b"} stroke={red ? "var(--ink)" : "#f2f2f2"} strokeWidth={2} />
      <circle r={8} fill="none" stroke={red ? "var(--on-accent)" : "#f2f2f2"} strokeWidth={1.2} opacity={0.6} />
      {king && <text y={5} textAnchor="middle" fontSize={14} fill="var(--yellow)">♚{TEXT}</text>}
    </g>
  );
  return (
    <svg viewBox="0 0 420 320" className="scene block w-full" role="img" aria-label="Checkers board: a red piece moves diagonally, jumps a black piece, and is crowned king">
      <Board light="#efe6cf" dark="#2f5d3f">
        {others.filter((o) => !o.gone).map((o, i) => disc(o.c, o.r, o.red, false, `o${i}`))}
        {disc(hero[0], hero[1], true, phase >= 3, "hero")}
      </Board>
      <Pill x={352} y={48} text="Diagonal, forward" show={phase === 1} w={118} />
      <Pill x={352} y={48} text="Jump = capture" show={phase === 2} w={110} />
      <Pill x={352} y={78} text="(mandatory)" show={phase === 2} color="var(--surface)" w={92} />
      <Pill x={352} y={48} text="King!" show={phase >= 3} w={70} />
    </svg>
  );
}
