// Shared data contracts. These mirror the Pydantic schemas in the repo:
//   recommendation/schemas.py + recommendation/api.py  (Recommendation engine)
//   RAG/app/schemas.py                                  (RAG service)
// and the lesson contract from the team project guide §7.
// If a backend schema changes, update it here first.

// ── Recommendation engine ────────────────────────────────────────────────
export interface MechanicComparison {
  mechanic: string;
  mechanic_label: string;
  best_known_game: string;
  shared_mechanics: string[];
  key_differences: string[];
  why_it_helps: string;
  score: number;
}

export interface RecommendationResponse {
  target_game: string;
  player_known_games: string[];
  top_overall: string;
  top_overall_score: number;
  per_mechanic: MechanicComparison[];
  warnings: string[];
}

export interface GameSummary {
  name: string;
  description: string;
  game_type: string;
  complexity: string;
  player_count_min: number;
  player_count_max: number;
  primary_mechanics: string[];
  primary_mechanic_labels: string[];
  tags: string[];
  // Extended metadata from BGG & Static
  bgg_id?: number;
  bgg_url?: string;
  image_path?: string;
  bayes_avg_rating?: number;
  num_ratings?: number;
  year_published?: number;
  mfg_playtime?: number;
  game_weight?: number;
  has_video?: boolean;
  video_url?: string;
  components?: string;
  how_to_play?: string;
  winning_strategies?: string;
  how_i_won?: string;
  winning_tips?: string;
  designers?: string;
  publishers?: string;
}

export interface GamesResponse {
  supported_games: GameSummary[];
  mechanic_vocabulary: Record<string, string>;
  target_games: string[];
  known_games: string[];
}

// ── RAG service ──────────────────────────────────────────────────────────
export interface SourceRef {
  title: string;
  url: string;
}

export interface RetrievedPassage {
  game: string;
  section: string;
  layer: string;
  mechanic: string | null;
  text: string;
  score: number;
  source: SourceRef;
}

export interface RetrievalResponse {
  passages: RetrievedPassage[];
  game_resolved: string | null;
  insufficient_evidence: boolean;
  retrieval_mode: string;
}

// ── Lesson (main backend, POST /lesson) ──────────────────────────────────
export type UserLevel = "beginner" | "intermediate" | "experienced";

export interface LessonRequest {
  known_games: string[];
  target_game: string;
  user_level: UserLevel;
  learning_goal: string;
}

export interface LessonSection {
  key: string; // objective | setup | turn_structure | core_mechanics | first_turn
  title: string;
  body: string;
  source_ids?: number[]; // indexes into LessonResponse.sources
}

export interface LessonComparison {
  familiar_game: string;
  shared_mechanic: string;
  key_difference: string;
  why_it_helps: string;
  score?: number;
}

export interface LessonSource {
  title: string;
  url: string;
  section?: string;
  claims_supported?: string[];
}

export interface QuizQuestion {
  question: string;
  options: string[];
  correct_index: number;
  explanation: string;
}

export type SceneType = "dice_production" | "route_claim" | "deck_cycle" | "step_cards";

export interface AnimationStep {
  label: string;
  caption: string;
  duration?: number; // seconds
  highlight?: string[]; // object ids to emphasise
}

export interface AnimationPlan {
  scene_type: SceneType;
  title: string;
  steps: AnimationStep[];
}

export interface LessonResponse {
  lesson_title: string;
  short_summary: string;
  sections: LessonSection[];
  comparisons: LessonComparison[];
  sources: LessonSource[];
  quiz: QuizQuestion[];
  animation_plan: AnimationPlan | null;
  warnings: string[];
}

// ── Follow-up ask (POST /ask) ────────────────────────────────────────────
export interface AskRequest {
  known_games: string[];
  target_game: string;
  question: string;
}

export interface AskResponse {
  answer: string;
  sources: LessonSource[];
  insufficient_evidence: boolean;
}

// ── Visual render (POST /visual, GET /visual/{id}) ───────────────────────
export interface VisualStatus {
  id: string;
  status: "queued" | "rendering" | "done" | "failed";
  video_url?: string | null;
  error?: string | null;
}

// ── Client-side bookkeeping ──────────────────────────────────────────────
export type DataOrigin = "live" | "demo";

export interface Result<T> {
  data: T;
  origin: DataOrigin;
  ms: number;
  /** Set when a live call was attempted and failed, so we fell back to demo. */
  fallbackReason?: string;
}
