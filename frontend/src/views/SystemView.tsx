import { useEffect, useState, useSyncExternalStore } from "react";
import { getLog, onLog, probe } from "../api/client";
import { BUILD_ENDPOINTS, DEMO_FALLBACK, TIMEOUT_MS, getEndpoints, onEndpointsChange, resetEndpoints, setEndpoints, type Endpoints } from "../api/config";
import { Notice, Spinner, fmtMs } from "../components/ui";

const SERVICES: { key: keyof Endpoints; name: string; role: string; example: string; paths: string }[] = [
  { key: "api", name: "Tutor backend", role: "LLM lesson generation on AMD inference", example: "https://tutor-api.example.com", paths: "POST /lesson, /ask, /visual; GET /visual/{id}, /health" },
  { key: "recommend", name: "Recommendation engine", role: "Ranks your games by shared mechanics", example: "http://localhost:8001", paths: "POST /recommend; GET /games" },
  { key: "rag", name: "Rules retrieval", role: "Finds rule passages with citations", example: "http://localhost:8100", paths: "POST /rag/retrieve; GET /health" },
];

type Probe = { ok: boolean; ms: number; detail: string } | "checking" | null;

function useLog() {
  return useSyncExternalStore(
    (cb) => { const off = onLog(cb); return () => { off(); }; },
    () => getLog().length + ":" + (getLog()[0]?.at ?? 0),
  );
}

export function SystemView() {
  const [form, setForm] = useState<Endpoints>(getEndpoints());
  const [probes, setProbes] = useState<Record<string, Probe>>({});
  const [saved, setSaved] = useState(false);
  useLog();
  const log = getLog();

  async function checkAll() {
    const ep = getEndpoints();
    for (const s of SERVICES) {
      if (!ep[s.key]) { setProbes((p) => ({ ...p, [s.key]: null })); continue; }
      setProbes((p) => ({ ...p, [s.key]: "checking" }));
      probe(s.key).then((r) => setProbes((p) => ({ ...p, [s.key]: r })));
    }
  }

  useEffect(() => {
    checkAll();
    const off = onEndpointsChange(() => { setForm(getEndpoints()); checkAll(); });
    return () => { off(); };
  }, []);

  function save(e: React.FormEvent) {
    e.preventDefault();
    setEndpoints(form);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  // Latency summary per service, live calls only
  const stats = SERVICES.map((s) => {
    const live = log.filter((l) => l.service === s.key && l.origin === "live");
    const ok = live.filter((l) => l.ok);
    const ms = ok.map((l) => l.ms).sort((a, b) => a - b);
    const p = (q: number) => (ms.length ? ms[Math.min(ms.length - 1, Math.floor(q * ms.length))] : null);
    return { ...s, calls: live.length, failures: live.length - ok.length, p50: p(0.5), p95: p(0.95) };
  });

  return (
    <div className="space-y-8">
      <header>
        <h1 className="font-display text-4xl font-extrabold sm:text-5xl">System</h1>
        <p className="mt-2 max-w-prose text-lg text-ink-soft">
          Which services the dashboard talks to, whether they're up, and how fast they answered. Anything not connected runs on built-in demo data.
        </p>
      </header>

      <form onSubmit={save} className="grid gap-4 lg:grid-cols-3">
        {SERVICES.map((s) => {
          const pr = probes[s.key];
          return (
            <div key={s.key} className="panel flex flex-col gap-3 p-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h2 className="font-display text-lg font-semibold">{s.name}</h2>
                  <p className="text-sm text-ink-soft">{s.role}</p>
                </div>
                <StatusDot probe={pr} configured={!!getEndpoints()[s.key]} />
              </div>
              <label className="text-sm font-bold" htmlFor={`ep-${s.key}`}>Address</label>
              <input id={`ep-${s.key}`} value={form[s.key]} onChange={(e) => setForm({ ...form, [s.key]: e.target.value })}
                placeholder={s.example} spellCheck={false}
                className="rounded-md border-2 border-ink bg-surface px-3 py-2 text-sm" />
              <p className="text-xs text-ink-soft">{s.paths}</p>
              <p className="text-sm" aria-live="polite">
                {pr === "checking" ? <Spinner label="Checking" /> : pr ? (pr.ok ? `Up in ${fmtMs(pr.ms)}: ${pr.detail}` : `Not responding: ${pr.detail}`) : "Not connected, using demo data"}
              </p>
            </div>
          );
        })}
        <div className="flex flex-wrap items-center gap-3 lg:col-span-3">
          <button className="btn btn-primary">{saved ? "Saved" : "Save addresses"}</button>
          <button type="button" className="btn" onClick={checkAll}>Check again</button>
          <button type="button" className="btn" onClick={resetEndpoints}>Use build defaults</button>
          <span className="text-sm text-ink-soft">Saved in this browser only. Build defaults come from VITE_* variables.</span>
        </div>
      </form>

      <Notice>
        Services must allow this site's origin (CORS). The RAG and recommendation services in the repo already allow all origins.
        {!DEMO_FALLBACK && " Demo fallback is off in this build, so failed calls show errors."}
      </Notice>

      <section className="space-y-3">
        <h2 className="font-display text-2xl font-extrabold">Response times</h2>
        <div className="tile overflow-x-auto">
          <table className="w-full min-w-[30rem] border-collapse text-sm">
            <thead>
              <tr className="border-b-2 border-ink text-left">
                <th className="p-3 font-display">Service</th>
                <th className="p-3 text-right font-display">Live calls</th>
                <th className="p-3 text-right font-display">Failed</th>
                <th className="p-3 text-right font-display">Median</th>
                <th className="p-3 text-right font-display">95th pct.</th>
              </tr>
            </thead>
            <tbody>
              {stats.map((s) => (
                <tr key={s.key} className="border-t border-sunk tabular-nums">
                  <td className="p-3 font-bold">{s.name}</td>
                  <td className="p-3 text-right">{s.calls}</td>
                  <td className="p-3 text-right" style={s.failures ? { color: "var(--red)", fontWeight: 700 } : undefined}>{s.failures}</td>
                  <td className="p-3 text-right">{s.p50 === null ? "—" : fmtMs(s.p50)}</td>
                  <td className="p-3 text-right">{s.p95 === null ? "—" : fmtMs(s.p95)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-ink-soft">Measured in this browser, including network time. Generate a few lessons to fill it in.</p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl font-extrabold">Recent requests</h2>
        {log.length === 0 ? (
          <p className="text-ink-soft">No requests yet. Build a lesson on the Learn page and they'll show up here.</p>
        ) : (
          <div className="panel max-h-96 overflow-auto">
            <table className="w-full border-collapse text-sm">
              <tbody>
                {log.slice(0, 60).map((l, i) => (
                  <tr key={i} className="border-b border-sunk tabular-nums">
                    <td className="px-3 py-1.5 text-ink-soft">{new Date(l.at).toLocaleTimeString()}</td>
                    <td className="px-3 py-1.5 font-bold">{SERVICES.find((s) => s.key === l.service)?.name}</td>
                    <td className="px-3 py-1.5">{l.path}</td>
                    <td className="px-3 py-1.5">
                      <span style={{ color: !l.ok ? "var(--red)" : l.origin === "live" ? "var(--green)" : "var(--ink-soft)", fontWeight: 700 }}>
                        {!l.ok ? `Failed${l.status ? ` ${l.status}` : ""}` : l.origin === "live" ? `Live ${l.status ?? ""}` : "Demo"}
                      </span>
                    </td>
                    <td className="px-3 py-1.5 text-right">{fmtMs(l.ms)}</td>
                    <td className="px-3 py-1.5 text-ink-soft">{l.note}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel max-w-3xl space-y-2 p-4 text-sm">
        <h2 className="font-display text-lg font-semibold">This build</h2>
        <p>Tutor backend: <code>{BUILD_ENDPOINTS.api || "not set"}</code></p>
        <p>Recommendation engine: <code>{BUILD_ENDPOINTS.recommend || "not set"}</code></p>
        <p>Rules retrieval: <code>{BUILD_ENDPOINTS.rag || "not set"}</code></p>
        <p>Demo fallback: {DEMO_FALLBACK ? "on" : "off"}. Request timeout: {TIMEOUT_MS / 1000}s.</p>
      </section>
    </div>
  );
}

function StatusDot({ probe, configured }: { probe: Probe | undefined; configured: boolean }) {
  const [color, text] = !configured
    ? ["var(--sunk)", "Demo"]
    : probe === "checking" || probe === undefined
      ? ["var(--yellow)", "Checking"]
      : probe && probe.ok
        ? ["var(--green)", "Up"]
        : ["var(--red)", "Down"];
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border-2 border-ink px-2 py-0.5 text-xs font-bold">
      <span className="h-2.5 w-2.5 rounded-full border border-ink" style={{ background: color }} /> {text}
    </span>
  );
}
