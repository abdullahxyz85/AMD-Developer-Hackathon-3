import { useState } from "react";
import { generateLesson, type LessonBundle } from "../api/client";
import type { UserLevel } from "../api/types";
import { useCatalog } from "../catalog";
import { AskTutor, Comparisons, LessonBody, PipelineTrace, Quiz, Sources } from "../components/Lesson";
import { GOALS, KnownGamesPicker, LevelGoal, TargetPicker } from "../components/ProfilePicker";
import { VisualPlayer } from "../components/VisualPlayer";
import { Notice, Spinner } from "../components/ui";

export function LearnView() {
  const { knownGames, targetGames } = useCatalog();
  const [known, setKnown] = useState<string[]>(["Monopoly", "Chess"]);
  const [target, setTarget] = useState("Catan");
  const [level, setLevel] = useState<UserLevel>("beginner");
  const [goal, setGoal] = useState(GOALS[0]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [bundle, setBundle] = useState<LessonBundle | null>(null);

  const toggle = (n: string) => setKnown((k) => (k.includes(n) ? k.filter((x) => x !== n) : [...k, n]));

  async function teach() {
    setBusy(true);
    setError(null);
    try {
      const b = await generateLesson({ known_games: known, target_game: target, user_level: level, learning_goal: goal });
      setBundle(b);
      requestAnimationFrame(() => document.getElementById("lesson")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const ready = known.length >= 1 && !!target;

  return (
    <div className="space-y-10">
      <section className="space-y-6">
        <h1 className="max-w-3xl font-display text-4xl font-extrabold sm:text-5xl">
          Learn a new game through the ones you already play.
        </h1>

        <div className="space-y-3">
          <h2 className="font-display text-xl font-semibold">Games you know</h2>
          <KnownGamesPicker games={knownGames} selected={known} onToggle={toggle} />
          {known.length < 2 && <p className="text-sm text-ink-soft">Pick at least two for the best comparisons.</p>}
        </div>

        <div className="space-y-3">
          <h2 className="font-display text-xl font-semibold">Game to learn</h2>
          <TargetPicker games={targetGames} value={target} onChange={setTarget} />
        </div>

        <LevelGoal level={level} goal={goal} onLevel={setLevel} onGoal={setGoal} />

        <div className="flex items-center gap-4">
          <button className="btn btn-primary px-6 py-3 text-lg" disabled={!ready || busy} onClick={teach}>
            {busy ? <Spinner label="Building your lesson" /> : `Teach me ${target}`}
          </button>
          {!ready && <span className="text-sm text-ink-soft">Choose at least one game you know.</span>}
        </div>
        {error && <Notice tone="error">The lesson couldn't be built: {error}. Check the service addresses on the System page.</Notice>}
      </section>

      {bundle && (
        <section id="lesson" className="scroll-mt-6 space-y-6">
          <div className="panel px-4 py-3">
            <PipelineTrace bundle={bundle} />
            {bundle.fallbackReason && (
              <p className="mt-2 text-xs text-ink-soft">A live service didn't respond ({bundle.fallbackReason}), so demo data filled in.</p>
            )}
          </div>

          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)]">
            <div className="space-y-8">
              <LessonBody lesson={bundle.lesson} />
              <div className="hidden lg:block">
                <Quiz key={"d" + bundle.totalMs} questions={bundle.lesson.quiz} />
              </div>
            </div>
            <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start">
              <VisualPlayer plan={bundle.lesson.animation_plan} />
              <Comparisons lesson={bundle.lesson} />
              <Sources sources={bundle.lesson.sources} />
            </aside>
          </div>
          <div className="lg:hidden">
            <Quiz key={"m" + bundle.totalMs} questions={bundle.lesson.quiz} />
          </div>
          <AskTutor key={target} known={known} target={bundle.recommendation.data.target_game} />
        </section>
      )}
    </div>
  );
}
