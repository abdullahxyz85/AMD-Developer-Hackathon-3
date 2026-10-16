// Composes a schema-valid LessonResponse from recommender + retrieval output.
// Used when the main /lesson backend (LLM) isn't configured: every sentence is
// taken from retrieved passages or recommender explanations — nothing invented.
import type {
  AnimationPlan,
  AskResponse,
  LessonComparison,
  LessonRequest,
  LessonResponse,
  LessonSection,
  LessonSource,
  QuizQuestion,
  RecommendationResponse,
  RetrievalResponse,
  RetrievedPassage,
} from "../api/types";
import { mechanicLabel } from "./catalog";

const strip = (t: string) =>
  t
    .replace(/^[^—:\n]{1,40}—\s*[^:\n]{1,40}:\s*/, "")
    // fact-card metadata sentences read badly in a lesson
    .replace(/\s*(Complexity|Tags):[^.]*\.(?=\s|$)/g, "")
    .trim();

class SourceBook {
  list: LessonSource[] = [];
  add(p: RetrievedPassage): number {
    const section = p.mechanic ? `${p.section}: ${mechanicLabel(p.mechanic)}` : p.section;
    let i = this.list.findIndex((s) => s.url === p.source.url && s.section === section);
    if (i < 0) {
      this.list.push({ title: p.source.title, url: p.source.url, section, claims_supported: [] });
      i = this.list.length - 1;
    }
    return i;
  }
}

function find(ps: RetrievedPassage[], pred: (p: RetrievedPassage) => boolean) {
  return ps.find(pred);
}

export function composeLesson(
  req: LessonRequest,
  rec: RecommendationResponse,
  rag: RetrievalResponse,
): LessonResponse {
  const ps = rag.passages;
  const book = new SourceBook();
  const warnings = [...rec.warnings];
  const target = rec.target_game;
  const sections: LessonSection[] = [];
  const cite = (p?: RetrievedPassage) => (p ? [book.add(p)] : []);

  // Objective
  const overview = find(ps, (p) => p.section === "objective") ?? find(ps, (p) => p.section === "overview");
  const vp = find(ps, (p) => p.mechanic === "victory_points");
  if (overview || vp) {
    sections.push({
      key: "objective",
      title: "What you're trying to do",
      body: [overview && strip(overview.text), vp && strip(vp.text)].filter(Boolean).join(" "),
      source_ids: [...cite(overview), ...cite(vp)],
    });
  }

  // Setup
  const setup = find(ps, (p) => p.section === "setup");
  if (setup) {
    sections.push({ key: "setup", title: "Setting up", body: strip(setup.text), source_ids: cite(setup) });
  } else {
    warnings.push(`Setup rules for ${target} aren't in the knowledge base yet — follow the official rulebook for setup.`);
  }

  // Core mechanics, ordered by how well the player's games anchor them
  const teachable = rec.per_mechanic
    .filter((m) => m.mechanic !== "turn_based" && m.mechanic !== "victory_points")
    .sort((a, b) => b.score - a.score);
  const depth = req.user_level === "beginner" ? 2 : req.user_level === "intermediate" ? 3 : teachable.length;
  const mechBodies: string[] = [];
  const mechSrc: number[] = [];
  for (const m of teachable.slice(0, depth)) {
    const p = find(ps, (x) => x.mechanic === m.mechanic);
    const diff = m.key_differences.find((d) => d.startsWith(target)) ?? m.key_differences[0];
    let s = `**${m.mechanic_label}** — think ${m.best_known_game}. ${m.why_it_helps}`;
    if (p) s += ` The rule: ${strip(p.text)}`;
    if (diff && req.user_level !== "beginner") s += ` Watch out: ${diff}.`;
    mechBodies.push(s);
    mechSrc.push(...cite(p));
  }
  // Mechanics no known game covers: teach from scratch, up to the same depth
  const coveredTags = new Set(rec.per_mechanic.map((m) => m.mechanic));
  const fresh = ps.filter(
    (p, i, all) =>
      p.mechanic &&
      !coveredTags.has(p.mechanic) &&
      p.mechanic !== "turn_based" &&
      p.mechanic !== "victory_points" &&
      all.findIndex((x) => x.mechanic === p.mechanic) === i,
  );
  const room = Math.max(1, depth - mechBodies.length);
  for (const p of fresh.slice(0, room)) {
    mechBodies.push(`**${mechanicLabel(p.mechanic!)}** — new to you, so from scratch: ${strip(p.text)}`);
    mechSrc.push(...cite(p));
  }
  if (mechBodies.length) {
    sections.push({ key: "core_mechanics", title: "The core ideas", body: mechBodies.join("\n\n"), source_ids: mechSrc });
  }

  // Turn structure
  const turn = find(ps, (p) => p.section === "turn_structure") ?? find(ps, (p) => p.mechanic === "turn_based");
  if (turn) {
    const anchor = rec.per_mechanic.find((m) => m.mechanic === "turn_based");
    const lead = anchor ? `You already know taking turns from ${anchor.best_known_game}; here's what one turn looks like in ${target}. ` : "";
    sections.push({ key: "turn_structure", title: "A turn, step by step", body: lead + strip(turn.text), source_ids: cite(turn) });
  }

  // Comparisons
  const usedDiffs = new Set<string>();
  const pickDiff = (ds: string[]) => {
    const d = ds.find((x) => x.startsWith(target) && !usedDiffs.has(x)) ?? ds.find((x) => !usedDiffs.has(x)) ?? "";
    if (d) usedDiffs.add(d);
    return d;
  };
  const comparisons: LessonComparison[] = rec.per_mechanic.map((m) => ({
    familiar_game: m.best_known_game,
    shared_mechanic: m.mechanic_label,
    key_difference: pickDiff(m.key_differences),
    why_it_helps: m.why_it_helps,
    score: m.score,
  }));

  if (!sections.length || rag.insufficient_evidence) {
    warnings.push(`Not enough rule evidence was found for ${target}. Treat this lesson as incomplete.`);
  }

  const known = rec.player_known_games.join(" and ") || "your games";
  return {
    lesson_title: `${target}, explained through ${known}`,
    short_summary:
      rec.top_overall !== "(none)"
        ? `${rec.top_overall} is your closest match (${Math.round(rec.top_overall_score * 100)}% of ${target}'s mechanics). We'll lean on it first, then cover what's new.`
        : `None of your games overlap much with ${target}, so we'll start from the basics.`,
    sections,
    comparisons,
    sources: book.list,
    quiz: QUIZ[target] ?? [],
    animation_plan: animationPlan(target, rec),
    warnings,
  };
}

// ── Visual plans (constrained schema → trusted SVG templates) ───────────
export function animationPlan(target: string, rec?: RecommendationResponse): AnimationPlan | null {
  const anchor = (m: string) => rec?.per_mechanic.find((x) => x.mechanic === m)?.best_known_game;
  if (target === "Catan") {
    const a = anchor("resource_management");
    return {
      scene_type: "dice_production",
      title: "How a dice roll produces resources",
      steps: [
        { label: "Roll", caption: "The active player rolls two dice. Here they total 8.", duration: 2.2, highlight: ["dice"] },
        { label: "Match", caption: "Every hex numbered 8 produces this turn — not just hexes near the roller.", duration: 2.4, highlight: ["hex-8"] },
        { label: "Collect", caption: `Each settlement touching a producing hex takes 1 card; a city takes 2.${a ? ` Like rent in ${a}, but everyone can collect on anyone's roll.` : ""}`, duration: 3, highlight: ["settlements"] },
        { label: "Odds", caption: "6 and 8 are printed red because they roll most often. Settle next to them.", duration: 2.6, highlight: ["hex-6", "hex-8"] },
        { label: "Robber", caption: "A 7 produces nothing: the robber moves, blocks a hex and steals one card.", duration: 2.8, highlight: ["robber"] },
      ],
    };
  }
  if (target === "Ticket to Ride") {
    const a = anchor("set_collection");
    return {
      scene_type: "route_claim",
      title: "Claiming a route",
      steps: [
        { label: "Collect", caption: `Draw train cards to build up matching colours.${a ? ` Same instinct as completing a set in ${a}.` : ""}`, duration: 2.6, highlight: ["hand"] },
        { label: "Match", caption: "This route is 3 blue spaces long, so you need 3 blue cards (locomotives are wild).", duration: 2.6, highlight: ["route"] },
        { label: "Claim", caption: "Spend the cards and place your trains. That's your whole turn.", duration: 2.4, highlight: ["route", "trains"] },
        { label: "Blocked", caption: "Once claimed, no one else can use that route.", duration: 2.4, highlight: ["route"] },
        { label: "Score", caption: "Longer routes score more. Finished destination tickets add a bonus; unfinished ones subtract.", duration: 2.8, highlight: ["score"] },
      ],
    };
  }
  if (target === "Dominion") {
    const a = anchor("hand_management");
    return {
      scene_type: "deck_cycle",
      title: "One turn of deck building",
      steps: [
        { label: "Draw", caption: `You drew the last 5 cards of your own deck.${a ? ` Reading your hand works like ${a}.` : ""}`, duration: 2.2, highlight: ["hand"] },
        { label: "Action", caption: "Play Action cards first — they can draw more cards or add buying power.", duration: 2.4, highlight: ["action"] },
        { label: "Buy", caption: "Add up Treasure and buy one card from the shared supply.", duration: 2.4, highlight: ["supply"] },
        { label: "Discard", caption: "Your new card and the hand you played go to your discard pile.", duration: 2.4, highlight: ["discard"] },
        { label: "Reshuffle", caption: "Your deck is empty, so shuffle the discards into a new deck. The Silver you bought can now show up in future hands.", duration: 3, highlight: ["deck"] },
      ],
    };
  }
  return null;
}

// ── Quiz bank, grounded in games.json key_mechanics_explained ───────────
export const QUIZ: Record<string, QuizQuestion[]> = {
  Catan: [
    {
      question: "Someone else rolls a 6. You have a settlement on a 6 hex. What happens?",
      options: ["Nothing — only the roller collects", "You take 1 matching resource card", "You take 2 cards", "You move the robber"],
      correct_index: 1,
      explanation: "Every settlement adjacent to a producing hex collects 1 card on any player's roll. A city would collect 2.",
    },
    {
      question: "What does rolling a 7 do?",
      options: ["Every hex produces", "The roller takes an extra turn", "The robber moves and steals one resource", "All players trade with the bank"],
      correct_index: 2,
      explanation: "A 7 activates the robber: it moves to a hex, the roller steals one resource from a player there, and players holding more than 7 cards discard half.",
    },
    {
      question: "How many victory points do you need to win?",
      options: ["7", "10", "12", "Whoever has the most cards"],
      correct_index: 1,
      explanation: "First to 10 victory points wins. Settlements are worth 1, cities 2, and Longest Road / Largest Army 2 each.",
    },
  ],
  "Ticket to Ride": [
    {
      question: "How many actions do you take on one turn?",
      options: ["One", "Two", "Three", "As many as you can afford"],
      correct_index: 0,
      explanation: "You do exactly one action: draw train cards, claim a route, or draw destination tickets.",
    },
    {
      question: "Another player claimed the route you needed. Can you still use it?",
      options: ["Yes, by paying them", "Yes, routes are shared", "No — find another path", "Only with locomotives"],
      correct_index: 2,
      explanation: "Once a route is claimed, no other player can use it. Blocking is part of the strategy.",
    },
    {
      question: "What happens to a destination ticket you didn't finish?",
      options: ["It's discarded with no effect", "It scores negative points", "It scores half points", "You keep it for next game"],
      correct_index: 1,
      explanation: "Incomplete destination tickets subtract their value at the end of the game.",
    },
  ],
  Dominion: [
    {
      question: "What's the order of a Dominion turn?",
      options: ["Buy, then play actions, then draw", "Play actions, buy, then clean up and draw 5", "Draw, discard, buy", "Play any cards in any order"],
      correct_index: 1,
      explanation: "Action phase, then Buy phase, then discard everything and draw 5 fresh cards.",
    },
    {
      question: "Why can buying too many Provinces early hurt you?",
      options: ["They cost more over time", "Victory cards do nothing in your hand", "Other players can steal them", "They end your turn"],
      correct_index: 1,
      explanation: "Victory cards are dead cards in hand. Buy them too early and your deck stops producing money and actions.",
    },
    {
      question: "When does the game end?",
      options: ["After 20 turns", "When someone has 10 points", "When Provinces run out or any three supply piles are empty", "When a player's deck runs out"],
      correct_index: 2,
      explanation: "The game ends when the Province pile is empty or any three supply piles are empty.",
    },
  ],
};

// ── Follow-up answer from evidence only ─────────────────────────────────
export function composeAnswer(rag: RetrievalResponse): AskResponse {
  if (rag.insufficient_evidence || !rag.passages.length) {
    return {
      answer: "I don't have reliable rules for that. Try rephrasing, or check the official rulebook.",
      sources: [],
      insufficient_evidence: true,
    };
  }
  const top = rag.passages.filter((p) => p.score >= 0.5).slice(0, 2);
  const use = top.length ? top : rag.passages.slice(0, 1);
  const book = new SourceBook();
  use.forEach((p) => book.add(p));
  return {
    answer: use.map((p) => strip(p.text)).join(" "),
    sources: book.list,
    insufficient_evidence: false,
  };
}
