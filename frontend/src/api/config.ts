// Service endpoints. Build-time values come from VITE_* env vars; anyone can
// override them at runtime on the System page (saved in this browser only),
// so a deployed build can be pointed at a new backend without a rebuild.

export interface Endpoints {
  api: string; // main tutor backend: /lesson /ask /quiz /visual
  recommend: string; // recommendation engine: /recommend /games
  rag: string; // RAG service: /rag/retrieve /rag/games /health
}

const KEY = "bgt.endpoints.v1";
const env = import.meta.env;

const clean = (u?: string) => (u ?? "").trim().replace(/\/+$/, "");

export const BUILD_ENDPOINTS: Endpoints = {
  api: clean(env.VITE_API_URL),
  recommend: clean(env.VITE_RECOMMEND_URL),
  rag: clean(env.VITE_RAG_URL),
};

export const DEMO_FALLBACK = (env.VITE_DEMO_FALLBACK ?? "true") !== "false";
export const TIMEOUT_MS = Number(env.VITE_TIMEOUT_MS) || 60000;

function read(): Partial<Endpoints> {
  try {
    return JSON.parse(localStorage.getItem(KEY) ?? "{}");
  } catch {
    return {};
  }
}

let current: Endpoints = { ...BUILD_ENDPOINTS, ...read() };
const listeners = new Set<() => void>();

export function getEndpoints(): Endpoints {
  return current;
}

export function setEndpoints(next: Endpoints) {
  current = { api: clean(next.api), recommend: clean(next.recommend), rag: clean(next.rag) };
  try {
    localStorage.setItem(KEY, JSON.stringify(current));
  } catch {
    /* storage unavailable: keep in memory */
  }
  listeners.forEach((l) => l());
}

export function resetEndpoints() {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
  current = { ...BUILD_ENDPOINTS };
  listeners.forEach((l) => l());
}

export function onEndpointsChange(fn: () => void) {
  listeners.add(fn);
  return () => listeners.delete(fn);
}
