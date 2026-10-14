// TypeScript port of recommendation/similarity.py + recommender.py.
// Used only when the recommendation service isn't reachable, so the demo
// still shows real, explainable personalization.
import type { MechanicComparison, RecommendationResponse } from "../api/types";
import { allMechanics, getGame, mechanicLabel, type GameRecord } from "./catalog";

function weight(target: GameRecord, m: string): number {
  if (target.primary_mechanics.includes(m)) return 1.5;
  if (target.secondary_mechanics.includes(m)) return 1.0;
  return 0;
}

export function weightedSimilarity(known: GameRecord, target: GameRecord): number {
  const tm = [...allMechanics(target)];
  const total = tm.reduce((s, m) => s + weight(target, m), 0);
  if (!total) return 0;
  const km = allMechanics(known);
  const matched = tm.filter((m) => km.has(m)).reduce((s, m) => s + weight(target, m), 0);
  return matched / total;
}

function rank(known: GameRecord[], target: GameRecord) {
  return known
    .map((g) => [g, weightedSimilarity(g, target)] as const)
    .sort((a, b) => b[1] - a[1]);
}

function shared(a: GameRecord, b: GameRecord): string[] {
  const bm = allMechanics(b);
  return [...allMechanics(a)].filter((m) => bm.has(m)).sort();
}

function differences(known: GameRecord, target: GameRecord): string[] {
  const out: string[] = [];
  const km = allMechanics(known);
  const tm = allMechanics(target);
  [...tm].filter((m) => !km.has(m)).sort().forEach((m) =>
    out.push(`${target.name} uses ${m.replace(/_/g, " ")}, which ${known.name} does not have`));
  [...km].filter((m) => !tm.has(m)).sort().forEach((m) =>
    out.push(`${known.name} uses ${m.replace(/_/g, " ")}, which ${target.name} does not have`));
  if (known.complexity !== target.complexity)
    out.push(`${target.name} is ${target.complexity} complexity (vs ${known.name}'s ${known.complexity})`);
  const [k0, k1] = known.player_count;
  const [t0, t1] = target.player_count;
  if (k0 !== t0 || k1 !== t1)
    out.push(`${target.name} supports ${t0}–${t1} players (vs ${known.name}'s ${k0}–${k1})`);
  return out;
}

const WHY: Record<string, string> = {
  "Monopoly|Catan|resource_management":
    "Like Monopoly's property income, Catan settlements produce resources each turn based on dice — think of hexes as colour-coded property groups.",
  "Monopoly|Catan|trading":
    "Catan's player trading mirrors Monopoly's deal-making, but resources are commodities (wood, ore) rather than money.",
  "Monopoly|Catan|economic":
    "Both games have an economic loop where early investment (buying property / building settlements) generates passive income that funds future growth.",
  "Poker|Catan|probability":
    "Poker players already reason about dice odds; in Catan, numbers 6 and 8 roll most often — the same bell-curve thinking applies.",
  "Risk|Catan|territory_control":
    "Risk's army placement and Catan's road/settlement building both use geographic position to control resources and block opponents.",
  "Monopoly|Ticket to Ride|set_collection":
    "Collecting matching colored train cards is just like gathering a color monopoly — you hoard until you have enough to act.",
  "Poker|Dominion|hand_management":
    "Managing your Dominion hand each turn — deciding what to play and when — mirrors choosing which poker hand to reveal based on what you've drawn.",
  "Uno|Dominion|hand_management":
    "Both Uno and Dominion reward knowing your hand and playing cards in the right order to chain effects.",
};

function why(known: GameRecord, target: GameRecord, m: string, sh: string[]): string {
  const k = `${known.name}|${target.name}|${m}`;
  if (WHY[k]) return WHY[k];
  const s = sh.length ? sh.slice(0, 2).join(", ") : "some mechanics";
  return `${known.name}'s experience with ${m.replace(/_/g, " ")} provides a useful mental model for ${target.name}'s version (both share: ${s}).`;
}

export function demoRecommend(knownNames: string[], targetName: string): RecommendationResponse {
  const target = getGame(targetName);
  if (!target) throw new Error(`Target game '${targetName}' is not in the catalog.`);
  const warnings: string[] = [];
  const known = knownNames.map(getGame).filter((g): g is GameRecord => !!g);
  const unknown = knownNames.filter((n) => !getGame(n));
  if (unknown.length) warnings.push(`These games are not in the catalog and were skipped: ${unknown.join(", ")}`);
  if (!known.length) {
    warnings.push("No recognized known games were provided. Recommendations will be generic.");
    return { target_game: target.name, player_known_games: knownNames, top_overall: "(none)", top_overall_score: 0, per_mechanic: [], warnings };
  }
  const ranked = rank(known, target);
  const per: MechanicComparison[] = [];
  const covered = new Set<string>();
  for (const m of target.primary_mechanics) {
    const candidates = known.filter((g) => allMechanics(g).has(m));
    if (!candidates.length) {
      warnings.push(`None of your known games cover '${mechanicLabel(m)}'. The tutor will explain this mechanic from scratch.`);
      continue;
    }
    const [best, score] = rank(candidates, target)[0];
    const sh = shared(best, target);
    per.push({
      mechanic: m,
      mechanic_label: mechanicLabel(m),
      best_known_game: best.name,
      shared_mechanics: sh,
      key_differences: differences(best, target),
      why_it_helps: why(best, target, m, sh),
      score: Math.round(score * 1000) / 1000,
    });
    covered.add(m);
  }
  for (const m of target.secondary_mechanics) {
    if (!covered.has(m) && !known.some((g) => allMechanics(g).has(m)))
      warnings.push(`Your known games don't cover '${mechanicLabel(m)}' (a secondary mechanic of ${target.name}).`);
  }
  return {
    target_game: target.name,
    player_known_games: known.map((g) => g.name),
    top_overall: ranked[0][0].name,
    top_overall_score: Math.round(ranked[0][1] * 1000) / 1000,
    per_mechanic: per,
    warnings,
  };
}
