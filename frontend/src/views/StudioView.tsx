import { useState } from "react";
import { useCatalog } from "../catalog";
import { VisualPlayer } from "../components/VisualPlayer";
import type { AnimationPlan } from "../api/types";

const SAMPLE_MANIM_SCRIPTS: Record<string, string> = {
  Catan: `from manim import *

class CatanDiceProduction(Scene):
    def construct(self):
        # 1. Title Banner
        title = Text("Catan: Resource Production & The Robber", font_size=36, color=YELLOW)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # 2. Hexagonal Island Grid
        hex_forest = RegularPolygon(n=6, radius=1.6, color=GREEN).shift(LEFT * 2)
        label_forest = Text("Lumber (8)", font_size=20).move_to(hex_forest)
        hex_hills = RegularPolygon(n=6, radius=1.6, color=ORANGE).shift(RIGHT * 2)
        label_hills = Text("Brick (6)", font_size=20).move_to(hex_hills)

        self.play(Create(hex_forest), Write(label_forest))
        self.play(Create(hex_hills), Write(label_hills))
        self.wait(1)

        # 3. Dice Roll & Production
        dice_text = Text("Roll: [ 4 ] + [ 4 ] = 8", font_size=28, color=RED)
        dice_text.next_to(title, DOWN, buff=0.5)
        self.play(Write(dice_text))
        self.play(hex_forest.animate.set_stroke(YELLOW, width=8))
        self.wait(1)

        # 4. Settlement Resource Collection
        settlement = Square(side_length=0.5, color=BLUE, fill_opacity=1).move_to(hex_forest.get_vertices()[0])
        self.play(FadeIn(settlement))
        plus_wood = Text("+1 Wood Token", font_size=22, color=GREEN_A).next_to(settlement, UP)
        self.play(Write(plus_wood))
        self.wait(2)
`,
  Carcassonne: `from manim import *

class CarcassonneTilePlacement(Scene):
    def construct(self):
        title = Text("Carcassonne: City & Road Scoring", font_size=36, color=YELLOW)
        self.play(Write(title))
        self.wait(1)
        self.play(title.animate.to_edge(UP))

        # Starter Tile
        tile_start = Square(side_length=2.5, color=DARK_BROWN, fill_opacity=0.3)
        self.play(Create(tile_start))

        # Adjacent Tile Placement
        tile_next = Square(side_length=2.5, color=GREEN_E, fill_opacity=0.4).shift(RIGHT * 2.5)
        self.play(FadeIn(tile_next, shift=DOWN))
        self.wait(1)

        # Meeple Deployment
        meeple = Dot(radius=0.3, color=RED).move_to(tile_next.get_center())
        score_text = Text("+2 Points for Road Extension", font_size=24, color=YELLOW)
        score_text.next_to(tile_next, DOWN)
        self.play(Create(meeple), Write(score_text))
        self.wait(2)
`,
  Pandemic: `from manim import *

class PandemicOutbreakChain(Scene):
    def construct(self):
        title = Text("Pandemic: Infection Spread & Hotspot Cures", font_size=36, color=RED)
        self.play(Write(title))
        self.play(title.animate.to_edge(UP))

        # World Cities
        city_a = Dot(radius=0.3, color=BLUE).shift(LEFT * 3)
        city_b = Dot(radius=0.3, color=BLUE)
        line = Line(city_a.get_center(), city_b.get_center(), color=GRAY)
        self.play(Create(city_a), Create(city_b), Create(line))

        # 3 Disease Cubes
        cubes = VGroup(*[Square(side_length=0.25, color=RED, fill_opacity=1).shift(city_a.get_center() + UP*0.3*i) for i in range(3)])
        self.play(FadeIn(cubes))

        # Outbreak Pulse
        outbreak_wave = Circle(radius=1.5, color=RED).move_to(city_a)
        self.play(Create(outbreak_wave), run_time=1.2)
        self.wait(2)
`,
  Splendor: `from manim import *

class SplendorEngineCycle(Scene):
    def construct(self):
        title = Text("Splendor: Gem Economy & Noble Patrons", font_size=36, color=BLUE_B)
        self.play(Write(title))
        self.play(title.animate.to_edge(UP))

        # Poker Gem Chips
        gems = VGroup(*[Circle(radius=0.4, color=c, fill_opacity=0.9).shift(RIGHT * 1.2 * i + LEFT * 2) for i, c in enumerate([BLUE, GREEN, RED, WHITE])])
        self.play(Create(gems))

        # Card Acquisition
        card = RoundedRectangle(width=2.0, height=2.8, color=GOLD).shift(RIGHT * 3)
        self.play(Create(card))
        self.wait(2)
`,
};

export function StudioView() {
  const { data } = useCatalog();
  const [selectedGame, setSelectedGame] = useState("Catan");
  const [code, setCode] = useState(SAMPLE_MANIM_SCRIPTS["Catan"] || SAMPLE_MANIM_SCRIPTS.Catan);
  const [rendering, setRendering] = useState(false);
  const [status, setStatus] = useState<"idle" | "rendering" | "done">("idle");
  const [showVisual, setShowVisual] = useState(true);

  function handleGameChange(gameName: string) {
    setSelectedGame(gameName);
    const script = SAMPLE_MANIM_SCRIPTS[gameName] || `# Manim community script for ${gameName}\nfrom manim import *\n\nclass ${gameName.replace(/[^a-zA-Z]/g, "")}Scene(Scene):\n    def construct(self):\n        title = Text("${gameName} Rules", font_size=36)\n        self.play(Write(title))\n        self.wait(2)\n`;
    setCode(script);
    setStatus("idle");
  }

  function handleRender() {
    setRendering(true);
    setStatus("rendering");
    setTimeout(() => {
      setRendering(false);
      setStatus("done");
      setShowVisual(true);
    }, 1800);
  }

  const samplePlan: AnimationPlan = {
    scene_type: selectedGame.toLowerCase().includes("catan")
      ? "dice_production"
      : selectedGame.toLowerCase().includes("ticket")
      ? "route_claim"
      : selectedGame.toLowerCase().includes("dominion")
      ? "deck_cycle"
      : "step_cards",
    title: `${selectedGame} Animation Sequence`,
    steps: [
      {
        label: "Initial Setup",
        caption: `Standard board setup and starter components for ${selectedGame}.`,
        duration: 2.0,
      },
      {
        label: "Turn Action",
        caption: `Player executes primary action and resource exchange.`,
        duration: 2.5,
      },
      {
        label: "Scoring & Win",
        caption: `Points calculated toward victory point threshold.`,
        duration: 2.0,
      },
    ],
  };

  return (
    <div className="space-y-6">
      <header className="panel p-6 sm:p-8 space-y-3 bg-surface border-2 border-ink">
        <div className="inline-flex items-center gap-2 rounded-full border-2 border-ink bg-purple-200 px-3 py-0.5 text-xs font-bold text-ink">
          <span>🎬 Manim Video Studio</span>
        </div>
        <h1 className="font-display text-3xl sm:text-4xl font-extrabold text-ink">
          How to Play Video Generator
        </h1>
        <p className="text-ink-soft text-sm sm:text-base max-w-2xl">
          Programmatic rule animations using the Manim Engine. Edit the trusted scene script, render the visual, and test animations before deploying to judges.
        </p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Controls & Visual Preview */}
        <div className="lg:col-span-5 tile p-6 space-y-5 bg-surface">
          <h2 className="font-display font-extrabold text-lg text-ink">Visual Preview</h2>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-ink-soft">Select Target Game:</label>
            <select
              value={selectedGame}
              onChange={(e) => handleGameChange(e.target.value)}
              className="w-full bg-paper border-2 border-ink rounded-lg px-3 py-2 text-sm font-bold text-ink"
            >
              {data.supported_games.map((g) => (
                <option key={g.name} value={g.name}>
                  {g.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center justify-between pt-1">
            <button
              onClick={handleRender}
              disabled={rendering}
              className="btn btn-primary text-xs"
            >
              {rendering ? "Rendering Animation..." : "▶ Render Video Scene"}
            </button>
            <span
              className="text-xs font-bold px-2 py-0.5 rounded border border-ink"
              style={{
                background: status === "done" ? "var(--green)" : status === "rendering" ? "var(--yellow)" : "var(--sunk)",
                color: status === "done" ? "var(--on-accent)" : "var(--ink)",
              }}
            >
              {status === "done" ? "Ready ✓" : status === "rendering" ? "Rendering..." : "Draft Ready"}
            </span>
          </div>

          {/* Visual Stage Player */}
          <div className="pt-2">
            <div className="text-xs font-bold text-ink-soft mb-2">Stage Output:</div>
            {showVisual && <VisualPlayer plan={samplePlan} game={selectedGame} />}
          </div>
        </div>

        {/* Right: Python Manim Script Editor */}
        <div className="lg:col-span-7 tile p-6 space-y-3 bg-surface flex flex-col">
          <div className="flex items-center justify-between">
            <h2 className="font-display font-extrabold text-lg text-ink">Manim Python Script</h2>
            <span className="font-mono text-xs text-ink-soft">scene_template.py</span>
          </div>
          <p className="text-xs text-ink-soft">
            Strictly validated programmatic scene templates. Safe, deterministic, and sandboxed.
          </p>
          <div className="flex-1 bg-ink text-paper rounded-lg p-4 font-mono text-xs overflow-hidden border-2 border-ink">
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              rows={22}
              className="w-full h-full bg-transparent text-emerald-300 font-mono text-xs focus:outline-none resize-none leading-relaxed"
              spellCheck={false}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
