# Role 4: personalized tutor prompts (v1)

Run commands from the repository root. Requires Python and Pydantic 2 (already
used by recommendation/RAG). Existing modules are unchanged.

## AMD Token Factory (default provider)

Uses the supplied event manual's base URL and OpenAI-compatible chat endpoint.
No local LLM/GPU or extra SDK is needed. Set the team key only in your terminal:

```powershell
$secret = Read-Host "AMD API key" -AsSecureString
$env:RADEON_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
python -m tutor.run --list-models
python -m tutor.run --known Monopoly Chess --target Catan --goal "explain resource management" --model "EXACT_ID_FROM_MODEL_LIST"
```

Model names change; use the live list, not a guessed Gemma ID. Generation uses
json_object mode (the manual does not promise strict schema for every model)
followed by local Lesson validation. No automatic retries consume team quota.
If rate-limited, coordinate with teammates and respect Retry-After before retrying.
Never commit or paste the key into source files. See VALIDATION.md for observed
live cloud results and remaining limitations.

## Hardware test: live services

Start recommendation on port 8001 and RAG on port 8100 following their READMEs.
The RAG index must be built first. Start Ollama with a model supported by your
actual hardware; `--model` is configurable, not a final model selection.

```powershell
python -m tutor.run --known Monopoly Chess --target Catan --goal "understand the objective" --dry-run
python -m tutor.run --provider ollama --known Monopoly Chess --target Catan --goal "understand the objective" --model llama3.2:3b
python -m tutor.run --provider ollama --known Poker Risk --target Catan --goal "understand the objective" --model llama3.2:3b
python -m tutor.run --provider ollama --known Monopoly --target Catan --question "What happens when I roll a 7?" --model llama3.2:3b
```

Dry-run still needs the data APIs, but does not call the LLM. Override
`--recommend-url`, `--rag-url`, `--ollama-url` when ports or router prefixes differ.
The runner prints a validated lesson and its evidence map. Invalid JSON, schema,
citations, target, comparisons or quiz indexes fail visibly; do not display the
unvalidated output. Service/network errors also fail visibly (no fabricated demo).
No model SDK, model download or GPU is needed to import/build prompts.

## Backend integration

```python
from tutor.prompts import prepare_context, build_messages, validate_lesson

# rec: actual POST /recommend response
# rag: actual POST /rag/retrieve response; pass rec.per_mechanic mechanic tags
# familiar_rags: retrieve rules for best_known_game values in rec.per_mechanic
context = prepare_context(rec, rag, learning_goal="understand the first turn",
                          familiar_retrievals=familiar_rags)
messages = build_messages(context)
# Send messages to your model; then:
lesson = validate_lesson(model_response_text, context)
```

If context.insufficient_evidence is true, skip inference and use
`insufficient_lesson(context)`, as demonstrated in run.py. For follow-up answers
set `question=...` and retrieve evidence for that question. Quiz generation is
included in the lesson schema. Each claim-bearing item references p1/p2/etc.;
the accompanying evidence map preserves source title, URL, section, and layer.
This is a proposed Role 4 output contract, not an already-agreed frontend/video
contract. Animation JSON is deliberately pending coordination with video owner.

Recommendation why_it_helps text is passed through as teaching guidance, never
authoritative rules. Some existing comparisons need human review (for example
Poker/dice analogies). Supplied evidence, including familiar-game rules where
needed for comparisons, must support the factual claims. Missing comparisons
should be omitted rather than invented. A false RAG insufficient_evidence flag
does not guarantee topic coverage.

## Offline contract checks and review

```powershell
python -m unittest tutor.test_prompts -v
```

test_prompts.sample_context() supplies two real recommendation profiles plus
explicitly synthetic rule evidence. It is for contract testing only, not a
production source or a measured model output. No live RAG/model test is implied.

Hardware/RAG reviewers should run both profiles above against actual services
and record model, device, runtime, latency, output validity, unsupported claims,
analogy usefulness and differences between profiles. Try an absent-topic question
and a passage containing instruction-like text. The system prompt separates data
from instructions, but prompt-injection resistance and factual support are not
guaranteed by schema validation. A known evidence ID proves reference integrity,
not semantic entailment. Review every rule and quiz answer against its passage.
Do not report GPU throughput or quality until actually measured.
