import { useEffect, useState } from "react";
import { addSubmission, getSubmissions, subscribeStorage } from "../api/storage";
import { useCatalog } from "../catalog";

export function SubmitView() {
  const { data } = useCatalog();
  const [, setVersion] = useState(0);

  // Form state
  const [name, setName] = useState("");
  const [year, setYear] = useState(new Date().getFullYear());
  const [minPlayers, setMinPlayers] = useState(2);
  const [maxPlayers, setMaxPlayers] = useState(4);
  const [playtime, setPlaytime] = useState(60);
  const [weight, setWeight] = useState(2.5);
  const [categories, setCategories] = useState("Strategy; Economic; Sci-Fi");
  const [mechanics, setMechanics] = useState("Worker Placement; Hand Management");
  const [description, setDescription] = useState("");
  const [howIWon, setHowIWon] = useState("");
  const [winningTips, setWinningTips] = useState("");
  const [author, setAuthor] = useState("TabletopStrategist");

  const [submittedToast, setSubmittedToast] = useState(false);

  useEffect(() => {
    return subscribeStorage(() => setVersion((v) => v + 1));
  }, []);

  const submissions = getSubmissions();

  // Duplicate Check
  const isDuplicate = data.supported_games.some(
    (g) => g.name.toLowerCase() === name.trim().toLowerCase()
  );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;

    addSubmission({
      name: name.trim(),
      year_published: year,
      min_players: minPlayers,
      max_players: maxPlayers,
      mfg_playtime: playtime,
      game_weight: weight,
      categories,
      mechanics,
      description,
      how_i_won: howIWon,
      winning_tips: winningTips,
      submitted_by: author,
    });

    setSubmittedToast(true);
    setName("");
    setDescription("");
    setHowIWon("");
    setWinningTips("");
    setTimeout(() => setSubmittedToast(false), 3000);
  }

  return (
    <div className="space-y-6">
      <header className="panel p-6 sm:p-8 space-y-3 bg-surface border-2 border-ink">
        <div className="inline-flex items-center gap-2 rounded-full border-2 border-ink bg-yellow px-3 py-0.5 text-xs font-bold text-ink">
          <span>🏆 Community Wiki</span>
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-ink">
          Submit A Game & Winning Strategy
        </h1>
        <p className="text-ink-soft text-sm sm:text-base max-w-2xl">
          Share new board games and master strategy playbooks with the community. Every submitted game includes "The Victor's Playbook: How I Won" so beginners can learn winning tactics right away.
        </p>
      </header>

      {submittedToast && (
        <div className="panel p-4 bg-green text-white font-bold text-sm border-2 border-ink">
          🎉 Successfully added to the community knowledge base!
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left: Submission Form (8 cols) */}
        <div className="lg:col-span-8 tile p-6 sm:p-8 space-y-6 bg-surface">
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Title with live duplicate validation */}
            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="font-bold text-ink text-xs">Game Title *</label>
                {name.trim() && (
                  <span
                    className={`text-[11px] font-bold ${
                      isDuplicate ? "text-red" : "text-green"
                    }`}
                  >
                    {isDuplicate ? "⚠️ Already in core catalog" : "✓ New game title"}
                  </span>
                )}
              </div>
              <input
                type="text"
                required
                placeholder="e.g. Dune: Imperium, Ark Nova, Scythe..."
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-paper border-2 border-ink rounded-lg px-3 py-2 text-sm text-ink focus:outline-none"
              />
            </div>

            {/* Specs row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              <div>
                <label className="font-bold text-ink-soft">Year Published:</label>
                <input
                  type="number"
                  value={year}
                  onChange={(e) => setYear(parseInt(e.target.value) || 2024)}
                  className="w-full bg-paper border-2 border-ink rounded-lg px-2.5 py-1.5 text-ink mt-1"
                />
              </div>
              <div>
                <label className="font-bold text-ink-soft">Players (Min - Max):</label>
                <div className="flex gap-1 mt-1">
                  <input
                    type="number"
                    min={1}
                    max={20}
                    value={minPlayers}
                    onChange={(e) => setMinPlayers(parseInt(e.target.value) || 2)}
                    className="w-1/2 bg-paper border-2 border-ink rounded-lg p-1.5 text-center text-ink"
                  />
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={maxPlayers}
                    onChange={(e) => setMaxPlayers(parseInt(e.target.value) || 4)}
                    className="w-1/2 bg-paper border-2 border-ink rounded-lg p-1.5 text-center text-ink"
                  />
                </div>
              </div>
              <div>
                <label className="font-bold text-ink-soft">Playtime (Mins):</label>
                <input
                  type="number"
                  value={playtime}
                  onChange={(e) => setPlaytime(parseInt(e.target.value) || 60)}
                  className="w-full bg-paper border-2 border-ink rounded-lg px-2.5 py-1.5 text-ink mt-1"
                />
              </div>
              <div>
                <label className="font-bold text-ink-soft">Weight (1.0 to 5.0):</label>
                <input
                  type="number"
                  step="0.1"
                  min="1.0"
                  max="5.0"
                  value={weight}
                  onChange={(e) => setWeight(parseFloat(e.target.value) || 2.5)}
                  className="w-full bg-paper border-2 border-ink rounded-lg px-2.5 py-1.5 text-ink mt-1"
                />
              </div>
            </div>

            {/* Categories & Mechanics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
              <div>
                <label className="font-bold text-ink-soft">Categories (semicolon-separated):</label>
                <input
                  type="text"
                  value={categories}
                  onChange={(e) => setCategories(e.target.value)}
                  className="w-full bg-paper border-2 border-ink rounded-lg px-3 py-1.5 text-ink mt-1"
                />
              </div>
              <div>
                <label className="font-bold text-ink-soft">Mechanics (semicolon-separated):</label>
                <input
                  type="text"
                  value={mechanics}
                  onChange={(e) => setMechanics(e.target.value)}
                  className="w-full bg-paper border-2 border-ink rounded-lg px-3 py-1.5 text-ink mt-1"
                />
              </div>
            </div>

            {/* Author */}
            <div className="text-xs">
              <label className="font-bold text-ink-soft">Your Gamer Tag / Username:</label>
              <input
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="TabletopStrategist"
                className="w-full bg-paper border-2 border-ink rounded-lg px-3 py-1.5 text-ink mt-1"
              />
            </div>

            {/* Description */}
            <div className="text-xs">
              <label className="font-bold text-ink-soft">Game Description & Premise:</label>
              <textarea
                rows={3}
                placeholder="Explain the setting, objective, and core game loop..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-paper border-2 border-ink rounded-lg p-2.5 text-ink mt-1 leading-relaxed"
              />
            </div>

            {/* Strategy Playbook Section */}
            <div className="panel p-4 space-y-3 bg-yellow/15 border-2 border-ink text-xs">
              <div className="font-display font-extrabold text-sm text-ink flex items-center gap-2">
                <span>👑 Master Strategy: How I Won & Winning Tips</span>
              </div>
              <div>
                <label className="font-bold text-ink">How I Won My Last Match (Strategy Playbook):</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Secured the desert track early, starved opponents of titanium..."
                  value={howIWon}
                  onChange={(e) => setHowIWon(e.target.value)}
                  className="w-full bg-surface border border-ink rounded p-2 text-ink mt-1"
                />
              </div>
              <div>
                <label className="font-bold text-ink">Winning Tips for New Players:</label>
                <textarea
                  rows={2}
                  placeholder="e.g. Never neglect your early round production; keep cash liquid..."
                  value={winningTips}
                  onChange={(e) => setWinningTips(e.target.value)}
                  className="w-full bg-surface border border-ink rounded p-2 text-ink mt-1"
                />
              </div>
            </div>

            <button type="submit" className="btn btn-primary w-full justify-center text-sm py-2.5">
              Publish Game & Strategy Playbook to Wiki
            </button>
          </form>
        </div>

        {/* Right: Community Feed (4 cols) */}
        <div className="lg:col-span-4 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b-2 border-ink">
            <h3 className="font-display font-extrabold text-base text-ink flex items-center gap-2">
              <span>🌐 Community Contributions</span>
            </h3>
            <span className="text-xs font-bold text-ink-soft">{submissions.length} submitted</span>
          </div>

          <div className="space-y-3 max-h-[680px] overflow-y-auto pr-1">
            {submissions.map((s) => (
              <div key={s.id} className="tile p-4 space-y-2 bg-surface">
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-display font-bold text-sm text-ink">{s.name}</h4>
                    <div className="text-[11px] text-ink-soft">
                      @{s.submitted_by} • Weight {s.game_weight.toFixed(1)}/5 • {s.min_players}-{s.max_players}p
                    </div>
                  </div>
                  <span className="text-[10px] rounded bg-sunk px-1.5 py-0.5 font-bold border border-ink">
                    {s.year_published}
                  </span>
                </div>

                {s.how_i_won && (
                  <div className="bg-paper p-2 rounded border border-ink/30 text-xs">
                    <span className="font-bold text-red block text-[11px]">🏆 How Victor Won:</span>
                    <p className="text-ink-soft italic text-[11px] line-clamp-2">"{s.how_i_won}"</p>
                  </div>
                )}

                {s.winning_tips && (
                  <div className="bg-paper p-2 rounded border border-ink/30 text-xs">
                    <span className="font-bold text-blue block text-[11px]">💡 Winning Tip:</span>
                    <p className="text-ink-soft text-[11px] line-clamp-2">{s.winning_tips}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
