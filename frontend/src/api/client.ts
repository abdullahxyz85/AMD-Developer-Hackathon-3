import type {
  AskRequest,
  AskResponse,
  GamesResponse,
  LessonRequest,
  LessonResponse,
  RecommendationResponse,
  Result,
  RetrievalResponse,
  VisualStatus,
  AnimationPlan,
} from "./types";
import { DEMO_FALLBACK, TIMEOUT_MS, getEndpoints, type Endpoints } from "./config";
import { demoGamesResponse } from "../demo/catalog";
import { demoRecommend } from "../demo/recommender";
import { demoRetrieve } from "../demo/rag";
import { composeAnswer, composeLesson } from "../demo/lesson";

export class ApiError extends Error {
  status: number | null;
  constructor(message: string, status: number | null) {
    super(message);
    this.status = status;
  }
}

async function http<T>(service: keyof Endpoints, path: string, init?: RequestInit, timeout = TIMEOUT_MS): Promise<{ data: T; ms: number }> {
  const base = getEndpoints()[service];
  if (!base) throw new ApiError("not configured", null);
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  const t0 = performance.now();
  let status: number | null = null;
  try {
    const res = await fetch(base + path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      signal: ctrl.signal,
    });
    status = res.status;
    const body = await res.json().catch(() => null);
    const ms = performance.now() - t0;
    if (!res.ok) {
      const detail = body && typeof body.detail === "string" ? body.detail : `HTTP ${res.status}`;
      throw new ApiError(`${service} ${path}: ${detail}`, status);
    }
    return { data: body as T, ms };
  } catch (e) {
    if (e instanceof ApiError) throw e;
    const msg = ctrl.signal.aborted ? `timed out after ${Math.round(timeout / 1000)}s` : "unreachable (network or CORS)";
    // Name the failing service so the error points at the right server, e.g. "recommend /recommend (http://localhost:8001): unreachable".
    throw new ApiError(`${service} ${path} (${base}): ${msg}`, status);
  } finally {
    clearTimeout(timer);
  }
}

const post = (body: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(body) });

/** Try the live service; fall back to the offline demo implementation. */
async function withFallback<T>(
  service: keyof Endpoints,
  live: () => Promise<{ data: T; ms: number }>,
  demo: () => T,
): Promise<Result<T>> {
  const configured = !!getEndpoints()[service];
  let reason: string | undefined;
  if (configured) {
    try {
      const r = await live();
      return { data: r.data, origin: "live", ms: r.ms };
    } catch (e) {
      // A 4xx from a live service is a real answer (e.g. unknown game) — surface it.
      if (e instanceof ApiError && e.status && e.status >= 400 && e.status < 500) throw e;
      if (!DEMO_FALLBACK) throw e;
      reason = (e as Error).message;
    }
  }
  const t0 = performance.now();
  const data = demo();
  const ms = performance.now() - t0;
  return { data, origin: "demo", ms, fallbackReason: reason };
}

// ── Public API ──────────────────────────────────────────────────────────
export function fetchGames(): Promise<Result<GamesResponse>> {
  return withFallback("recommend", () => http<GamesResponse>("recommend", "/games", undefined, 8000), demoGamesResponse);
}

export function recommend(known_games: string[], target_game: string): Promise<Result<RecommendationResponse>> {
  return withFallback(
    "recommend",
    () => http<RecommendationResponse>("recommend", "/recommend", post({ known_games, target_game })),
    () => demoRecommend(known_games, target_game),
  );
}

export function retrieve(game: string, query: string, focus_mechanics: string[] = [], k = 8): Promise<Result<RetrievalResponse>> {
  return withFallback(
    "rag",
    () => http<RetrievalResponse>("rag", "/rag/retrieve", post({ game, query, focus_mechanics, k })),
    () => demoRetrieve(game, query, focus_mechanics, k),
  );
}

export interface LessonBundle {
  lesson: LessonResponse;
  recommendation: Result<RecommendationResponse>;
  retrieval: Result<RetrievalResponse> | null;
  /** "backend" when POST /lesson produced it; "composed" when built here from recommender + RAG. */
  generator: "backend" | "composed";
  lessonMs: number;
  totalMs: number;
  fallbackReason?: string;
}

/**
 * Lesson pipeline (guide §5):
 *  1. recommender → ranked comparisons
 *  2. if the tutor backend is configured, POST /lesson (LLM does retrieval + generation)
 *  3. otherwise retrieve evidence from RAG using the recommender's mechanics and
 *     compose a grounded lesson in the browser.
 */
export async function generateLesson(req: LessonRequest): Promise<LessonBundle> {
  const t0 = performance.now();
  const recommendation = await recommend(req.known_games, req.target_game);
  let reason: string | undefined;

  if (getEndpoints().api) {
    try {
      const r = await http<LessonResponse>("api", "/lesson", post(req));
      return {
        lesson: normalizeLesson(r.data),
        recommendation,
        retrieval: null,
        generator: "backend",
        lessonMs: r.ms,
        totalMs: performance.now() - t0,
      };
    } catch (e) {
      if (!DEMO_FALLBACK) throw e;
      reason = (e as Error).message;
    }
  }

  const focus = recommendation.data.per_mechanic.map((m) => m.mechanic);
  const query = `${req.learning_goal} objective setup turn ${focus.join(" ").replace(/_/g, " ")}`;
  const retrieval = await retrieve(req.target_game, query, focus, 12);
  const t1 = performance.now();
  const lesson = composeLesson(req, recommendation.data, retrieval.data);
  return {
    lesson,
    recommendation,
    retrieval,
    generator: "composed",
    lessonMs: performance.now() - t1,
    totalMs: performance.now() - t0,
    fallbackReason: reason ?? recommendation.fallbackReason ?? retrieval.fallbackReason,
  };
}

/** Defensive defaults so a slightly-off backend payload can't crash the page. */
function normalizeLesson(l: Partial<LessonResponse>): LessonResponse {
  return {
    lesson_title: l.lesson_title ?? "Your lesson",
    short_summary: l.short_summary ?? "",
    sections: Array.isArray(l.sections) ? l.sections : [],
    comparisons: Array.isArray(l.comparisons) ? l.comparisons : [],
    sources: Array.isArray(l.sources) ? l.sources : [],
    quiz: Array.isArray(l.quiz) ? l.quiz.filter((q) => q && Array.isArray(q.options) && q.options.length > 1) : [],
    animation_plan: l.animation_plan ?? null,
    warnings: Array.isArray(l.warnings) ? l.warnings : [],
  };
}

export async function ask(req: AskRequest): Promise<Result<AskResponse>> {
  if (getEndpoints().api) {
    try {
      const r = await http<AskResponse>("api", "/ask", post(req));
      return { data: r.data, origin: "live", ms: r.ms };
    } catch (e) {
      if (!DEMO_FALLBACK) throw e;
    }
  }
  const t0 = performance.now();
  const rag = await retrieve(req.target_game, req.question, [], 4);
  return { data: composeAnswer(rag.data), origin: rag.origin, ms: performance.now() - t0, fallbackReason: rag.fallbackReason };
}

/** Start a server-side Manim render. Returns null when no backend renderer is available. */
export async function startRender(plan: AnimationPlan): Promise<VisualStatus | null> {
  if (!getEndpoints().api) return null;
  try {
    const r = await http<VisualStatus>("api", "/visual", post(plan), 15000);
    return r.data;
  } catch {
    return null;
  }
}

export async function renderStatus(id: string): Promise<VisualStatus | null> {
  try {
    const r = await http<VisualStatus>("api", `/visual/${encodeURIComponent(id)}`, undefined, 10000);
    return r.data;
  } catch {
    return null;
  }
}

export function resolveUrl(u: string): string {
  if (/^https?:\/\//.test(u)) return u;
  const base = getEndpoints().api;
  return base ? base + (u.startsWith("/") ? u : "/" + u) : u;
}
