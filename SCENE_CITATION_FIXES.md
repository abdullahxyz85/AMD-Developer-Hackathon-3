# Game scenes and citation bookkeeping

Based on origin/main at 69bacb7. No frontend files changed.
Updated with origin/main through d23bf68 before handoff. Upstream already added
inline citation normalization; merged resolution keeps that behavior and preserves
inline reference order, plus the regression test for a missing known reference.

Monopoly shares dice_rolling with Catan, but the dice_production template contains
Catan-specific hexes, settlements and robber art. Fallback selection now requires
the correct target game as well as mechanic tags. LLM-selected scenes are also
constrained: Catan -> dice_production, Ticket to Ride -> route_claim, Dominion ->
deck_cycle; other games use neutral step_cards. Incompatible LLM scene choices
retain validated captions but lose game-specific art/highlights.

Lesson validation now unions inline [pN] references into evidence_ids only when
those exact IDs exist in the request's evidence map. This repairs the intermittent
missing-ID error without fabricating a source, rewriting claims or accepting
unknown IDs. Checks for both comparison games, quiz indices, target and schema
remain enabled. This does not prove factual entailment of cited passages.

Validation: python -m unittest tutor.test_prompts test_game_scenes -q
15 tests pass, covering incorrect LLM scenes, fallback scenes, valid inline
reference repair and rejection of unknown inline references.
Direct Monopoly fallback render produced a decodable MP4 (159 frames). Renderer
log decoding now tolerates non-UTF8 Windows diagnostics instead of failing its
subprocess reader thread. Live model/UI retesting of these changes is still pending.

Previously generated videos are immutable and are not rewritten. Restart the
backend and generate a new lesson/video after merging. Retest Chess -> Monopoly
and a Catan profile; old job URLs may still show old artwork.
