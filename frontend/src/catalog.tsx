import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { fetchGames } from "./api/client";
import type { DataOrigin, GameSummary, GamesResponse } from "./api/types";
import { demoGamesResponse } from "./demo/catalog";

interface CatalogState {
  data: GamesResponse;
  origin: DataOrigin;
  knownGames: GameSummary[];
  targetGames: GameSummary[];
  byName: (n: string) => GameSummary | undefined;
  label: (tag: string) => string;
}

function build(data: GamesResponse, origin: DataOrigin): CatalogState {
  const byName = (n: string) => data.supported_games.find((g) => g.name === n);
  const pick = (names: string[]) => names.map(byName).filter((g): g is GameSummary => !!g);
  return {
    data,
    origin,
    knownGames: pick(data.known_games),
    targetGames: pick(data.target_games),
    byName,
    label: (t) => data.mechanic_vocabulary[t] ?? t.replace(/_/g, " "),
  };
}

const Ctx = createContext<CatalogState>(build(demoGamesResponse(), "demo"));

export function CatalogProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState(() => build(demoGamesResponse(), "demo"));
  useEffect(() => {
    fetchGames()
      .then((r) => setState(build(r.data, r.origin)))
      .catch(() => setState(build(demoGamesResponse(), "demo")));
  }, []);
  return <Ctx.Provider value={state}>{children}</Ctx.Provider>;
}

export const useCatalog = () => useContext(Ctx);
