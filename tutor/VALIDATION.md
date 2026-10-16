# Role 4 validation and handoff

User-supplied terminal results reviewed on 16 October 2026:

- Live local recommendation + RAG + AMD Gemma-4-31B-IT generated valid lessons
  for Monopoly/Chess and Poker/Risk profiles learning Catan resource management.
- Analogy changed from Monopoly to Risk. Both outputs included three quizzes.
- After adding familiar-game retrieval, a further live Risk run passed validation
  and cited passages for both games.
- Local RAG index: 74 fact-card chunks, zero curated-rule chunks.
- Offline contract checks: 10 tests pass using synthetic evidence and real
  recommendation functions. No latency, throughput or learning benefit measured.

The last live comparison mentioned 10 victory points without including its
objective passage in evidence_ids. Prompt now explicitly requests a clause-level
citation audit. This final prompt revision has not yet been tested live.
Reference validation is structural; factual entailment still needs human review.

## Integration owner

Use prepare_context(rec, rag, familiar_retrievals=[...]), build_messages(context),
then validate_lesson(response_text, context). Pass the lesson AND evidence map
to the UI. tutor.run demonstrates the API calls; it is not a deployed lesson
endpoint. Output schema is proposed, pending frontend/video agreement.

## Hardware owner

Run both profiles with --provider amd and the exact live model ID. Keep the
shared key in RADEON_API_KEY, never browser code. Review every claim against
its cited passages, record latency and failures, and coordinate shared quota.

## RAG/video owners

Confirm curated rules are available and check fact-card accuracy/edition details.
Animation schema remains a separate integration task; no generated Python is
executed by this module.
