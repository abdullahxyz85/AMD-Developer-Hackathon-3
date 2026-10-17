import { useEffect, useState } from "react";
import { CatalogProvider } from "./catalog";
import { Meeple } from "./components/ui";
import { CompareView } from "./views/CompareView";
import { GamesView } from "./views/GamesView";
import { LandingView } from "./views/LandingView";
import { LearnView } from "./views/LearnView";
import { PicksView } from "./views/PicksView";
import { ShelfView } from "./views/ShelfView";
import { StudioView } from "./views/StudioView";
import { SubmitView } from "./views/SubmitView";

export type ViewId = "home" | "learn" | "compare" | "games" | "picks" | "shelf" | "studio" | "submit";

interface ViewItem {
  id: ViewId;
  label: string;
  icon: string;
}

const VIEW_ITEMS: ViewItem[] = [
  { id: "learn", label: "Learn a game", icon: "🎓" },
  { id: "compare", label: "Compare players", icon: "⚖️" },
  { id: "games", label: "Game shelf", icon: "🎲" },
  { id: "picks", label: "Picks", icon: "✨" },
  { id: "shelf", label: "My shelf", icon: "📚" },
  { id: "studio", label: "Videos", icon: "🎬" },
  { id: "submit", label: "Submit", icon: "🏆" },
];

function useHashView(): [ViewId, (v: ViewId) => void] {
  const read = (): ViewId => {
    const h = window.location.hash.replace(/^#\/?/, "");
    if (h === "" || h === "home") return "home";
    return (VIEW_ITEMS.find((v) => v.id === h)?.id ?? "learn") as ViewId;
  };
  const [view, setView] = useState<ViewId>(read);
  useEffect(() => {
    const on = () => setView(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return [view, (v) => { window.location.hash = `/${v}`; }];
}

export default function App() {
  const [view, go] = useHashView();
  const [targetGameToTeach, setTargetGameToTeach] = useState<string>("Catan");
  const [knownToTeach, setKnownToTeach] = useState<string[] | undefined>(undefined);

  const currentItem = VIEW_ITEMS.find((v) => v.id === view) || VIEW_ITEMS[0];

  useEffect(() => {
    window.scrollTo(0, 0);
    document.title = view === "home" ? "Board-Game Tutor" : `${currentItem.label} | Board-Game Tutor`;
  }, [view, currentItem.label]);

  function handleTeachGame(name: string, known?: string[]) {
    setTargetGameToTeach(name);
    if (known?.length) setKnownToTeach(known);
    go("learn");
  }

  if (view === "home") {
    return (
      <CatalogProvider>
        <LandingView onTeach={handleTeachGame} go={go} />
      </CatalogProvider>
    );
  }

  function renderCurrentView() {
    switch (view) {
      case "learn":
        return <LearnView initialTarget={targetGameToTeach} initialKnown={knownToTeach} />;
      case "compare":
        return <CompareView />;
      case "games":
        return <GamesView onTeachGame={handleTeachGame} />;
      case "picks":
        return <PicksView onTeachGame={handleTeachGame} />;
      case "shelf":
        return <ShelfView onTeachGame={handleTeachGame} />;
      case "studio":
        return <StudioView />;
      case "submit":
        return <SubmitView />;
      default:
        return <LearnView initialTarget={targetGameToTeach} initialKnown={knownToTeach} />;
    }
  }

  return (
    <CatalogProvider>
      <div className="min-h-screen md:grid md:grid-cols-[16rem_minmax(0,1fr)]">
        <aside className="border-b-2 border-ink bg-surface md:sticky md:top-0 md:h-screen md:border-b-0 md:border-r-2 flex flex-col justify-between">
          <div>
            <a href="#/home" onClick={(e) => { e.preventDefault(); go("home"); }} className="flex items-center gap-2.5 px-5 py-4 md:py-6 border-b border-sunk md:border-b-0">
              <Meeple color="var(--red)" size={32} />
              <div>
                <span className="font-display text-xl font-extrabold leading-none block">Board-Game</span>
                <span className="font-display text-xs font-bold text-red tracking-wider uppercase">Tutor & Wiki</span>
              </div>
            </a>

            <nav aria-label="Main" className="flex gap-1 overflow-x-auto px-3 py-2 md:flex-col md:px-3 md:py-1">
              {VIEW_ITEMS.map((v) => {
                const on = v.id === view;
                return (
                  <a
                    key={v.id}
                    href={`#/${v.id}`}
                    onClick={(e) => { e.preventDefault(); go(v.id); }}
                    aria-current={on ? "page" : undefined}
                    className="whitespace-nowrap rounded-lg px-3.5 py-2 font-display text-sm font-semibold flex items-center gap-2 transition"
                    style={
                      on
                        ? { background: "var(--ink)", color: "var(--paper)" }
                        : { color: "var(--ink)" }
                    }
                  >
                    <span className="text-base">{v.icon}</span>
                    <span>{v.label}</span>
                  </a>
                );
              })}
            </nav>
          </div>

          <p className="hidden px-5 pb-6 text-[11px] text-ink-soft md:block">Built for the AMD Developer Hackathon Act III.</p>
        </aside>

        <main className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-8 md:py-10">
          {renderCurrentView()}
        </main>
      </div>
    </CatalogProvider>
  );
}
