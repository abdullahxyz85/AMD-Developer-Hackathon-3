import { useEffect, useState, useSyncExternalStore } from "react";
import { getEndpoints, onEndpointsChange } from "./api/config";
import { CatalogProvider } from "./catalog";
import { Meeple } from "./components/ui";
import { CompareView } from "./views/CompareView";
import { GamesView } from "./views/GamesView";
import { LearnView } from "./views/LearnView";
import { SystemView } from "./views/SystemView";

const VIEWS = [
  { id: "learn", label: "Learn a game", el: <LearnView /> },
  { id: "compare", label: "Compare players", el: <CompareView /> },
  { id: "games", label: "Game shelf", el: <GamesView /> },
  { id: "system", label: "System", el: <SystemView /> },
] as const;
type ViewId = (typeof VIEWS)[number]["id"];

// Hash routing keeps every view linkable on any static host, no rewrites needed.
function useHashView(): [ViewId, (v: ViewId) => void] {
  const read = (): ViewId => {
    const h = window.location.hash.replace(/^#\/?/, "");
    return (VIEWS.find((v) => v.id === h)?.id ?? "learn") as ViewId;
  };
  const [view, setView] = useState<ViewId>(read);
  useEffect(() => {
    const on = () => setView(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return [view, (v) => { window.location.hash = `/${v}`; }];
}

function useConnectedCount() {
  return useSyncExternalStore(
    (cb) => { const off = onEndpointsChange(cb); return () => { off(); }; },
    () => Object.values(getEndpoints()).filter(Boolean).length,
  );
}

export default function App() {
  const [view, go] = useHashView();
  const connected = useConnectedCount();
  const current = VIEWS.find((v) => v.id === view)!;

  useEffect(() => {
    window.scrollTo(0, 0);
    document.title = `${current.label} | Board-Game Tutor`;
  }, [view, current.label]);

  return (
    <CatalogProvider>
      <div className="min-h-screen md:grid md:grid-cols-[15rem_minmax(0,1fr)]">
        <aside className="border-b-2 border-ink bg-surface md:sticky md:top-0 md:h-screen md:border-b-0 md:border-r-2">
          <div className="flex items-center gap-2.5 px-5 py-4 md:py-6">
            <Meeple color="var(--red)" size={30} />
            <span className="font-display text-xl font-extrabold leading-none">Board-Game<br className="hidden md:block" /> Tutor</span>
          </div>
          <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 pb-3 md:flex-col md:px-3">
            {VIEWS.map((v) => {
              const on = v.id === view;
              return (
                <a
                  key={v.id}
                  href={`#/${v.id}`}
                  onClick={(e) => { e.preventDefault(); go(v.id); }}
                  aria-current={on ? "page" : undefined}
                  className="whitespace-nowrap rounded-full px-4 py-2 font-display font-semibold"
                  style={on ? { background: "var(--ink)", color: "var(--paper)" } : undefined}
                >
                  {v.label}
                </a>
              );
            })}
          </nav>
          <div className="hidden px-5 pt-6 text-sm md:block">
            <a href="#/system" onClick={(e) => { e.preventDefault(); go("system"); }} className="block rounded-md border-2 border-ink p-3 hover:bg-sunk">
              <span className="font-bold">{connected === 0 ? "Demo mode" : `${connected} of 3 services connected`}</span>
              <span className="mt-1 block text-ink-soft">
                {connected === 0 ? "Runs on bundled game data. Connect your services here." : "Anything not connected uses demo data."}
              </span>
            </a>
            <p className="mt-6 text-xs text-ink-soft">Built for the AMD Developer Hackathon Act III.</p>
          </div>
        </aside>
        <main className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-8 md:py-12">{current.el}</main>
      </div>
    </CatalogProvider>
  );
}
