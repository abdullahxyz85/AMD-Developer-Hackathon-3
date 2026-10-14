// Offline keyword retrieval over the same "Layer A" fact cards the RAG
// service builds from games.json (RAG/scripts/load_games.py). Only used when
// the RAG service isn't reachable.
import type { RetrievalResponse, RetrievedPassage } from "../api/types";
import { GAMES, getGame, mechanicLabel, type GameRecord } from "./catalog";

const STOP = new Set(
  "a an the is are do does i you my to of in on and or what how when where can for with it if be at as by this that your".split(" "),
);

function tokens(s: string): string[] {
  return s.toLowerCase().replace(/[^a-z0-9\s]/g, " ").split(/\s+/).filter((t) => t && !STOP.has(t));
}

function cards(g: GameRecord): RetrievedPassage[] {
  const source = { title: `${g.name} — BoardGameGeek`, url: g.bgg_url ?? "" };
  const base = { game: g.name, layer: "fact_card", score: 0, source };
  const out: RetrievedPassage[] = [
    { ...base, section: "overview", mechanic: null, text: `${g.name} — Overview: ${g.description}` },
  ];
  for (const [m, text] of Object.entries(g.key_mechanics_explained ?? {})) {
    out.push({ ...base, section: "mechanic", mechanic: m, text: `${g.name} — ${mechanicLabel(m)}: ${text}` });
  }
  if (g.notes) out.push({ ...base, section: "notes", mechanic: null, text: `${g.name} — Notes: ${g.notes}` });
  return out;
}

export function demoRetrieve(game: string, query: string, focus: string[] = [], k = 6): RetrievalResponse {
  const g = getGame(game) ?? GAMES.find((x) => x.name.toLowerCase().includes(game.toLowerCase()));
  if (!g) return { passages: [], game_resolved: null, insufficient_evidence: true, retrieval_mode: "keyword (offline demo)" };
  const q = new Set(tokens(query));
  const scored = cards(g).map((p) => {
    const t = tokens(p.text);
    const hits = t.filter((x) => q.has(x)).length;
    let s = q.size ? hits / Math.sqrt(t.length + 1) : 0;
    if (p.mechanic && focus.includes(p.mechanic)) s += 1;
    if (p.mechanic && q.has(p.mechanic.split("_")[0])) s += 0.4;
    return { ...p, raw: s };
  });
  const max = Math.max(...scored.map((p) => p.raw), 0.0001);
  const passages = scored
    .sort((a, b) => b.raw - a.raw)
    .slice(0, k)
    .map(({ raw, ...p }) => ({ ...p, score: Math.round((raw / max) * 100) / 100 }));
  const best = Math.max(...scored.map((p) => p.raw));
  return {
    passages,
    game_resolved: g.name,
    insufficient_evidence: best < 0.15,
    retrieval_mode: "keyword (offline demo)",
  };
}
