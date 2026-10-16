import { Fragment, useState, type ReactNode } from "react";
import type { LessonBundle } from "../api/client";
import { ask } from "../api/client";
import type { AskResponse, LessonResponse, LessonSource, QuizQuestion, Result } from "../api/types";
import { Notice, OriginBadge, ScoreBar, Spinner, fmtMs } from "./ui";

/** Minimal, safe inline formatting: **bold** and paragraphs. No HTML injection. */
function Rich({ text }: { text: string }) {
  return (
    <>
      {text.split(/\n{2,}/).map((para, i) => (
        <p key={i} className="mb-3 last:mb-0">
          {para.split(/(\*\*[^*]+\*\*)/).map((chunk, j) =>
            chunk.startsWith("**") ? <strong key={j}>{chunk.slice(2, -2)}</strong> : <Fragment key={j}>{chunk}</Fragment>,
          )}
        </p>
      ))}
    </>
  );
}

function Cite({ ids, sources }: { ids?: number[]; sources: LessonSource[] }) {
  if (!ids?.length) return null;
  const uniq = [...new Set(ids)].filter((i) => sources[i]);
  return (
    <span className="ml-1 inline-flex gap-1 align-super text-[11px]">
      {uniq.map((i) => (
        <a key={i} href={`#src-${i}`} className="rounded-full border border-ink px-1.5 font-bold no-underline hover:bg-ink hover:text-paper" title={sources[i].section ?? sources[i].title}>
          {i + 1}
        </a>
      ))}
    </span>
  );
}

export function PipelineTrace({ bundle }: { bundle: LessonBundle }) {
  const steps: { name: string; detail: ReactNode }[] = [
    {
      name: "Match your games",
      detail: <OriginBadge origin={bundle.recommendation.origin} ms={bundle.recommendation.ms} />,
    },
    bundle.retrieval
      ? {
          name: "Find the rules",
          detail: (
            <span className="inline-flex items-center gap-2">
              <OriginBadge origin={bundle.retrieval.origin} ms={bundle.retrieval.ms} />
              <span className="text-xs text-ink-soft">{bundle.retrieval.data.passages.length} passages, {bundle.retrieval.data.retrieval_mode}</span>
            </span>
          ),
        }
      : { name: "Find the rules", detail: <span className="text-xs text-ink-soft">done by the tutor backend</span> },
    {
      name: bundle.generator === "backend" ? "Write the lesson (LLM)" : "Assemble the lesson",
      detail: bundle.generator === "backend" ? <OriginBadge origin="live" ms={bundle.lessonMs} /> : (
        <span className="text-xs text-ink-soft" title="No tutor backend configured: lesson assembled in the browser from retrieved evidence only">from evidence, {fmtMs(bundle.lessonMs)}</span>
      ),
    },
  ];
  return (
    <ol className="flex flex-wrap items-center gap-x-2 gap-y-2 text-sm">
      {steps.map((s, i) => (
        <li key={s.name} className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-ink font-display text-xs font-bold">{i + 1}</span>
          <span className="font-bold">{s.name}</span>
          {s.detail}
          {i < steps.length - 1 && <span aria-hidden className="mx-1 h-0.5 w-6 bg-ink" />}
        </li>
      ))}
      <li className="ml-auto text-sm text-ink-soft">Total {fmtMs(bundle.totalMs)}</li>
    </ol>
  );
}

export function LessonBody({ lesson, accent = "var(--red)" }: { lesson: LessonResponse; accent?: string }) {
  return (
    <article className="space-y-5">
      <header>
        <h2 className="font-display text-3xl font-extrabold sm:text-4xl">{lesson.lesson_title}</h2>
        {lesson.short_summary && <p className="mt-2 max-w-prose text-lg text-ink-soft">{lesson.short_summary}</p>}
      </header>
      {lesson.sections.map((s) => (
        <section key={s.key} className="max-w-prose">
          <h3 className="mb-2 flex items-center gap-2 font-display text-xl font-semibold">
            <span className="h-3 w-3 rounded-sm border-2 border-ink" style={{ background: accent }} aria-hidden />
            {s.title}
            <Cite ids={s.source_ids} sources={lesson.sources} />
          </h3>
          <div className="prose-lesson text-[16.5px] leading-relaxed">
            <Rich text={s.body} />
          </div>
        </section>
      ))}
      {lesson.warnings.length > 0 && (
        <div className="max-w-prose space-y-2">
          {lesson.warnings.map((w, i) => (
            <Notice key={i} tone="warn">{w}</Notice>
          ))}
        </div>
      )}
    </article>
  );
}

export function Comparisons({ lesson, accent = "var(--yellow)", accentText = "var(--on-yellow)" }: { lesson: LessonResponse; accent?: string; accentText?: string }) {
  if (!lesson.comparisons.length) return null;
  return (
    <section className="panel p-4">
      <h3 className="font-display text-lg font-semibold">Bridges from games you know</h3>
      <ul className="mt-3 space-y-3">
        {lesson.comparisons.map((c, i) => (
          <li key={i} className="border-t-2 border-sunk pt-3 first:border-0 first:pt-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-full border-2 border-ink px-2 py-0.5 text-sm font-bold" style={{ background: accent, color: accentText }}>{c.familiar_game}</span>
              <span className="text-sm">for</span>
              <span className="font-bold">{c.shared_mechanic}</span>
              {c.score !== undefined && (
                <span className="ml-auto flex items-center gap-2 text-xs tabular-nums text-ink-soft">
                  <ScoreBar value={c.score} /> {Math.round(c.score * 100)}%
                </span>
              )}
            </div>
            <p className="mt-1 text-sm">{c.why_it_helps}</p>
            {c.key_difference && <p className="mt-1 text-sm text-ink-soft">Different: {c.key_difference}.</p>}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Sources({ sources }: { sources: LessonSource[] }) {
  if (!sources.length) return null;
  return (
    <section className="panel p-4">
      <h3 className="font-display text-lg font-semibold">Where these rules come from</h3>
      <ol className="mt-2 space-y-1.5 text-sm">
        {sources.map((s, i) => (
          <li key={i} id={`src-${i}`} className="flex gap-2">
            <span className="w-5 shrink-0 font-bold tabular-nums">{i + 1}.</span>
            <span>
              {s.url ? (
                <a href={s.url} target="_blank" rel="noreferrer" className="font-bold underline decoration-2 underline-offset-2">{s.title}</a>
              ) : (
                <span className="font-bold">{s.title}</span>
              )}
              {s.section && <span className="text-ink-soft">, {s.section.replace(/_/g, " ")}</span>}
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function Quiz({ questions }: { questions: QuizQuestion[] }) {
  const [answers, setAnswers] = useState<Record<number, number>>({});
  if (!questions.length) return null;
  const done = Object.keys(answers).length;
  const right = questions.filter((q, i) => answers[i] === q.correct_index).length;
  return (
    <section className="tile p-5">
      <div className="flex items-baseline justify-between">
        <h3 className="font-display text-2xl font-extrabold">Check yourself</h3>
        <span className="text-sm tabular-nums">
          {done === questions.length ? `${right} of ${questions.length} right` : `${done} of ${questions.length} answered`}
        </span>
      </div>
      <ol className="mt-4 space-y-5">
        {questions.map((q, i) => {
          const picked = answers[i];
          const answered = picked !== undefined;
          return (
            <li key={i}>
              <p className="font-bold">{i + 1}. {q.question}</p>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {q.options.map((o, j) => {
                  const isRight = j === q.correct_index;
                  const bg = !answered ? undefined : isRight ? "var(--green)" : j === picked ? "var(--red)" : undefined;
                  return (
                    <button
                      key={j}
                      disabled={answered}
                      onClick={() => setAnswers({ ...answers, [i]: j })}
                      className="game-box px-3 py-2 text-left text-sm disabled:cursor-default"
                      style={bg ? { background: bg, color: "var(--on-accent)" } : undefined}
                      aria-pressed={j === picked}
                    >
                      {o}
                    </button>
                  );
                })}
              </div>
              {answered && (
                <p className="mt-2 text-sm" role="status">
                  <strong>{picked === q.correct_index ? "Right. " : "Not quite. "}</strong>
                  {q.explanation}
                </p>
              )}
            </li>
          );
        })}
      </ol>
      {done === questions.length && (
        <button className="btn mt-4 text-sm" onClick={() => setAnswers({})}>Try again</button>
      )}
    </section>
  );
}

const SUGGESTIONS: Record<string, string[]> = {
  Catan: ["What happens when I roll a 7?", "How do ports change trading?", "How many points is a city?"],
  "Ticket to Ride": ["What are locomotive cards?", "When does the game end?", "How are routes scored?"],
  Dominion: ["What happens when my deck runs out?", "How many cards do I buy per turn?", "When should I buy Provinces?"],
};

export function AskTutor({ known, target }: { known: string[]; target: string }) {
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [thread, setThread] = useState<{ q: string; r?: Result<AskResponse>; err?: string }[]>([]);

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setBusy(true);
    setQ("");
    const idx = thread.length;
    setThread((t) => [...t, { q: question }]);
    try {
      const r = await ask({ known_games: known, target_game: target, question });
      setThread((t) => t.map((x, i) => (i === idx ? { ...x, r } : x)));
    } catch (e) {
      setThread((t) => t.map((x, i) => (i === idx ? { ...x, err: (e as Error).message } : x)));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel p-4">
      <h3 className="font-display text-lg font-semibold">Ask about {target}</h3>
      <div className="mt-3 space-y-4">
        {thread.map((t, i) => (
          <div key={i} className="space-y-1.5">
            <p className="font-bold">{t.q}</p>
            {t.err && <Notice tone="error">Couldn't answer: {t.err}</Notice>}
            {!t.r && !t.err && <Spinner label="Looking it up" />}
            {t.r && (
              <div className={t.r.data.insufficient_evidence ? "text-ink-soft" : ""}>
                <p className="text-[15px]">{t.r.data.answer}</p>
                <div className="mt-1 flex flex-wrap items-center gap-2 text-xs">
                  <OriginBadge origin={t.r.origin} ms={t.r.ms} />
                  {t.r.data.sources.map((s, j) => (
                    <a key={j} href={s.url} target="_blank" rel="noreferrer" className="underline">
                      {s.title}{s.section ? `, ${s.section}` : ""}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
      {!thread.length && (
        <div className="mt-2 flex flex-wrap gap-2">
          {(SUGGESTIONS[target] ?? []).map((s) => (
            <button key={s} className="rounded-full border-2 border-ink px-3 py-1 text-sm hover:bg-sunk" onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}
      <form className="mt-3 flex gap-2" onSubmit={(e) => { e.preventDefault(); send(q); }}>
        <label className="sr-only" htmlFor="ask">Your question</label>
        <input id="ask" value={q} onChange={(e) => setQ(e.target.value)} placeholder={`Ask a rules question about ${target}`}
          className="min-w-0 flex-1 rounded-full border-2 border-ink bg-surface px-4 py-2" />
        <button className="btn btn-primary" disabled={busy || !q.trim()}>Ask</button>
      </form>
    </section>
  );
}
