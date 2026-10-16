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
        <h1 className="font-display text-4xl font-extrabold sm:text-5xl">System & AI</h1>
        <p className="mt-2 max-w-prose text-lg text-ink-soft">
          Which services the dashboard talks to, whether they're up, and how fast they answered. Configure AMD ROCm / Gemma or cloud inference endpoints.
        </p>
      </header>

      {/* AI Model & Inference Configuration (from static) */}
      <AIConfigSection />

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

import { getAIConfig, saveAIConfig } from "../api/storage";

function AIConfigSection() {
  const [cfg, setCfg] = useState(getAIConfig());
  const [testing, setTesting] = useState(false);
  const [pingResult, setPingResult] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const presets = [
    { label: "AMD Gemma (ROCm)", model: "amd/gemma-2b-it-rocm", url: "http://127.0.0.1:8001/v1" },
    { label: "Qwen 2.5 7B", model: "Qwen/Qwen2.5-Coder-7B-Instruct", url: "http://127.0.0.1:8001/v1" },
    { label: "Llama 3.1 8B", model: "meta-llama/Llama-3.1-8B-Instruct", url: "http://127.0.0.1:8001/v1" },
    { label: "Mistral 7B", model: "mistralai/Mistral-7B-Instruct-v0.3", url: "http://127.0.0.1:8001/v1" },
    { label: "Local Ollama", model: "gemma:2b", url: "http://localhost:11434" },
  ];

  function applyPreset(p: (typeof presets)[0]) {
    setCfg((prev) => ({
      ...prev,
      modelName: p.model,
      serverUrl: p.url,
    }));
  }

  function handleSave(e: React.FormEvent) {
    e.preventDefault();
    saveAIConfig(cfg);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  async function testConnection() {
    setTesting(true);
    setPingResult(null);
    try {
      const res = await fetch(`${cfg.serverUrl.replace(/\/+$/, "")}/health`, {
        signal: AbortSignal.timeout(4000),
      }).catch(() => null);

      if (res && res.ok) {
        setPingResult("Connected successfully! Service is live.");
      } else {
        // Fallback test to base URL
        const res2 = await fetch(cfg.serverUrl, {
          signal: AbortSignal.timeout(3000),
        }).catch(() => null);
        if (res2) {
          setPingResult(`Endpoint reachable (Status ${res2.status})`);
        } else {
          setPingResult("Endpoint not reachable (check CORS and server address).");
        }
      }
    } catch (e: any) {
      setPingResult(`Connection test timed out: ${e.message}`);
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="tile p-6 space-y-5 bg-surface border-2 border-ink">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b-2 border-ink pb-3">
        <div className="flex items-center gap-2.5">
          <span className="text-xl">🤖</span>
          <div>
            <h2 className="font-display font-extrabold text-xl text-ink">AI Model & AMD Hardware Inference</h2>
            <p className="text-xs text-ink-soft">Configure the LLM engine for tutoring and lesson generation</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-ink-soft">Active Model:</span>
          <span className="rounded-full border border-ink bg-yellow px-2.5 py-0.5 text-xs font-bold text-ink">
            {cfg.modelName}
          </span>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-4 text-xs">
        {/* Provider selection */}
        <div>
          <label className="font-bold text-ink">Inference Engine / Provider:</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-1.5">
            {[
              { id: "amd", label: "AMD Cloud / ROCm" },
              { id: "zai", label: "z.ai Cloud" },
              { id: "ollama", label: "Local Ollama" },
              { id: "custom", label: "Custom vLLM" },
            ].map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => setCfg({ ...cfg, provider: p.id as any })}
                className="py-2 px-3 rounded-lg border-2 border-ink font-bold transition text-center"
                style={{
                  background: cfg.provider === p.id ? "var(--ink)" : "var(--paper)",
                  color: cfg.provider === p.id ? "var(--paper)" : "var(--ink)",
                }}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Server URL & API Key */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="font-bold text-ink">Server Endpoint URL:</label>
            <input
              type="text"
              value={cfg.serverUrl}
              onChange={(e) => setCfg({ ...cfg, serverUrl: e.target.value })}
              placeholder="http://127.0.0.1:8001/v1"
              className="w-full mt-1 p-2 rounded-lg border-2 border-ink bg-paper font-mono text-xs text-ink"
            />
          </div>
          <div>
            <label className="font-bold text-ink">API Key (optional / token):</label>
            <input
              type="password"
              value={cfg.apiKey}
              onChange={(e) => setCfg({ ...cfg, apiKey: e.target.value })}
              placeholder="Paste team key if required"
              className="w-full mt-1 p-2 rounded-lg border-2 border-ink bg-paper font-mono text-xs text-ink"
            />
          </div>
        </div>

        {/* Model Name & Presets */}
        <div>
          <div className="flex justify-between items-center mb-1">
            <label className="font-bold text-ink">Model Name / Path:</label>
            <span className="text-ink-soft">Quick Presets:</span>
          </div>
          <input
            type="text"
            value={cfg.modelName}
            onChange={(e) => setCfg({ ...cfg, modelName: e.target.value })}
            placeholder="amd/gemma-2b-it-rocm"
            className="w-full p-2 rounded-lg border-2 border-ink bg-paper font-mono text-xs text-ink mb-2"
          />

          <div className="flex flex-wrap gap-1.5">
            {presets.map((p) => (
              <button
                key={p.label}
                type="button"
                onClick={() => applyPreset(p)}
                className="rounded-full border border-ink bg-paper hover:bg-sunk px-2.5 py-1 text-[11px] font-bold text-ink"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Temperature & Tokens */}
        <div className="grid grid-cols-2 gap-4 pt-1">
          <div>
            <label className="font-bold text-ink">Temperature: {cfg.temperature}</label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={cfg.temperature}
              onChange={(e) => setCfg({ ...cfg, temperature: parseFloat(e.target.value) })}
              className="w-full accent-red mt-1"
            />
          </div>
          <div>
            <label className="font-bold text-ink">Max Output Tokens: {cfg.maxTokens}</label>
            <input
              type="number"
              min="500"
              max="32000"
              step="500"
              value={cfg.maxTokens}
              onChange={(e) => setCfg({ ...cfg, maxTokens: parseInt(e.target.value) || 2000 })}
              className="w-full p-1.5 rounded-lg border-2 border-ink bg-paper font-mono text-xs text-ink mt-1"
            />
          </div>
        </div>

        {/* Action row */}
        <div className="pt-2 flex flex-wrap items-center justify-between gap-3 border-t-2 border-sunk">
          <div className="flex items-center gap-2">
            <button type="submit" className="btn btn-primary text-xs">
              {saved ? "Saved Settings ✓" : "Save AI Settings"}
            </button>
            <button
              type="button"
              onClick={testConnection}
              disabled={testing}
              className="btn text-xs"
            >
              {testing ? "Testing..." : "Test Connection"}
            </button>
          </div>
          {pingResult && (
            <span className="text-xs font-bold text-ink">
              {pingResult}
            </span>
          )}
        </div>
      </form>
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

