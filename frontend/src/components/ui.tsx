import type { ReactNode } from "react";
import type { DataOrigin } from "../api/types";

export function OriginBadge({ origin, ms, title }: { origin: DataOrigin; ms?: number; title?: string }) {
  const live = origin === "live";
  return (
    <span
      title={title ?? (live ? "Answered by the live service" : "Answered by the built-in demo data")}
      className="inline-flex items-center gap-1.5 rounded-full border-2 border-ink px-2 py-0.5 text-xs font-bold"
      style={{ background: live ? "var(--green)" : "var(--sunk)", color: live ? "var(--on-accent)" : "var(--ink)" }}
    >
      <span className="h-2 w-2 rounded-full" style={{ background: live ? "var(--on-accent)" : "var(--ink-soft)" }} />
      {live ? "Live" : "Demo"}
      {ms !== undefined && <span className="font-normal tabular-nums">{fmtMs(ms)}</span>}
    </span>
  );
}

export function fmtMs(ms: number) {
  if (ms < 1) return "<1 ms";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  return `${(ms / 1000).toFixed(1)} s`;
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2" role="status">
      <svg className="spin h-4 w-4" viewBox="0 0 24 24" aria-hidden>
        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="3" strokeDasharray="40 20" />
      </svg>
      {label && <span>{label}</span>}
    </span>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  label,
}: {
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="inline-flex flex-wrap rounded-full border-2 border-ink bg-surface p-1">
      {options.map((o) => {
        const on = o.value === value;
        return (
          <button
            key={o.value}
            role="radio"
            aria-checked={on}
            onClick={() => onChange(o.value)}
            className="rounded-full px-3 py-1 text-sm font-bold"
            style={on ? { background: "var(--ink)", color: "var(--paper)" } : undefined}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}

export function Notice({ tone = "info", children }: { tone?: "info" | "warn" | "error"; children: ReactNode }) {
  const color = tone === "error" ? "var(--red)" : tone === "warn" ? "var(--yellow)" : "var(--blue)";
  return (
    <div className="rounded-md border-2 border-ink bg-surface px-3 py-2 text-sm" style={{ borderLeft: `8px solid ${color}` }}>
      {children}
    </div>
  );
}

/** A meeple, used as the player marker throughout. */
export function Meeple({ color, size = 20 }: { color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <path
        d="M32 4a10 10 0 0 1 10 10c0 3-1 5-3 7l14 6c4 2 5 6 3 9l-6-1-4 23H18l-4-23-6 1c-2-3-1-7 3-9l14-6c-2-2-3-4-3-7A10 10 0 0 1 32 4z"
        fill={color}
        stroke="var(--ink)"
        strokeWidth="4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ScoreBar({ value, color = "var(--ink)" }: { value: number; color?: string }) {
  return (
    <span className="inline-block h-2.5 w-20 overflow-hidden rounded-full border-2 border-ink align-middle" aria-hidden>
      <span className="block h-full" style={{ width: `${Math.round(value * 100)}%`, background: color }} />
    </span>
  );
}
