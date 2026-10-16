import { useState } from "react";
import type { GameSummary } from "../api/types";
import { savePlay } from "../api/storage";

interface Props {
  game: GameSummary | null;
  onClose: () => void;
  onSaved?: () => void;
}

export function LogPlayModal({ game, onClose, onSaved }: Props) {
  const [rating, setRating] = useState(8.5);
  const [notes, setNotes] = useState("");
  const [savedToast, setSavedToast] = useState(false);

  if (!game) return null;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!game) return;

    savePlay({
      bgg_id: game.bgg_id,
      name: game.name,
      rating,
      notes,
    });

    setSavedToast(true);
    setTimeout(() => {
      setSavedToast(false);
      onSaved?.();
      onClose();
    }, 700);
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="log-play-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(0, 0, 0, 0.65)", backdropFilter: "blur(4px)" }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="relative w-full max-w-md tile p-6 space-y-5 bg-surface">
        <div className="flex items-center justify-between border-b-2 border-ink pb-3">
          <div className="flex items-center gap-2">
            <span className="text-xl">🎲</span>
            <h3 id="log-play-title" className="font-display text-xl font-extrabold text-ink">
              Log Game Play
            </h3>
          </div>
          <button
            onClick={onClose}
            className="rounded-full border-2 border-ink p-1 hover:bg-sunk text-ink font-bold text-sm"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs font-bold text-ink-soft">Game</label>
            <div className="font-display font-extrabold text-lg text-ink">{game.name}</div>
          </div>

          <div>
            <div className="flex justify-between text-xs font-bold text-ink mb-1">
              <span>Your Rating:</span>
              <span className="text-red font-display text-sm font-extrabold">{rating.toFixed(1)} / 10</span>
            </div>
            <input
              type="range"
              min="1.0"
              max="10.0"
              step="0.5"
              value={rating}
              onChange={(e) => setRating(parseFloat(e.target.value))}
              className="w-full accent-red cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-ink-soft">
              <span>1.0 (Awful)</span>
              <span>5.0 (Average)</span>
              <span>10.0 (Masterpiece)</span>
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-ink-soft">Play Notes / Memorable Moments</label>
            <textarea
              rows={3}
              placeholder="e.g. Played with 4 players. Dominated the ore tiles and won with Largest Army..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              className="w-full mt-1 p-2.5 rounded-lg border-2 border-ink bg-paper text-xs text-ink focus:outline-none focus:border-red"
            />
          </div>

          <div className="pt-2 flex items-center justify-end gap-2">
            <button type="button" onClick={onClose} className="btn text-xs">
              Cancel
            </button>
            <button type="submit" className="btn btn-primary text-xs">
              {savedToast ? "Saved to Shelf! ✓" : "Save Play to Shelf"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

