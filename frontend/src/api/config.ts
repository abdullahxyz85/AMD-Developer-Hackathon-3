// Service endpoints, from VITE_* env vars (frontend/.env). They are baked in at
// build time, so restart `npm run dev` or rebuild after changing them.

export interface Endpoints {
  api: string; // main tutor backend: /lesson /ask /quiz /visual
  recommend: string; // recommendation engine: /recommend /games
  rag: string; // RAG service: /rag/retrieve /rag/games /health
}

const env = import.meta.env;

const clean = (u?: string) => (u ?? "").trim().replace(/\/+$/, "");

export const BUILD_ENDPOINTS: Endpoints = {
  api: clean(env.VITE_API_URL),
  recommend: clean(env.VITE_RECOMMEND_URL),
  rag: clean(env.VITE_RAG_URL),
};

export const DEMO_FALLBACK = (env.VITE_DEMO_FALLBACK ?? "true") !== "false";
export const TIMEOUT_MS = Number(env.VITE_TIMEOUT_MS) || 60000;

export function getEndpoints(): Endpoints {
  return BUILD_ENDPOINTS;
}
