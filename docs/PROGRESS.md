# Development Progress

Tracks implementation status in the new admin-facing format.

---

## Current Status

Project stage: MVP development, partially through Step 1

Target vertical slice:

document -> retrieval -> answer -> verification

Current reality:
- retrieval is working
- source passage splitting is working
- backend query flow is working
- local LLM answer generation and verification are improved with `qwen2.5:7b`, but still not reliably schema-compliant

Overall status:
- [x] Step 1 foundation is substantially implemented
- [x] Retrieval and indexing are operational
- [x] Inspectability/debug artifact persistence is operational
- [x] Shared structured-generation enforcement layer now exists for answer + verifier JSON/schema handling
- [x] Local model evaluation workflow exists and baseline vs upgraded model results have been captured
- [x] Retrieval eval loop now writes per-query debug artifacts and failure classifications
- [ ] Final answer generation is stable enough for intended product quality
- [ ] Verification is reliably schema-compliant with the configured local model

---

## Completed Work

- [x] Repository initialized and pushed to GitHub
- [x] Local development environment working in the `ai` conda env
- [x] Automated tests passing locally
- [x] Generic backend schema exists for projects, documents, sections, passages, windows, queries, drafts, and verification reports
- [x] FastAPI routes exist for projects, documents, queries, and evals
- [x] Raw and normalized text ingestion is implemented
- [x] Passage windows are built and stored
- [x] Lexical retrieval is implemented
- [x] Dense retrieval is implemented
- [x] Hybrid merge and reranking stages exist
- [x] Evidence bundle construction exists
- [x] Retrieval debug artifacts are persisted and exposed by API
- [x] Prompt and output schema layer exists
- [x] Answer generator and verifier pipeline exists
- [x] Shared structured generation runner now centralizes JSON cleanup, validation, and retry handling
- [x] Fallback extractive answer path exists when the local model fails schema validation
- [x] Fallback deterministic verification path exists when the local model fails schema validation
- [x] Configurable model evaluation script exists for local model comparison
- [x] Retrieval debug artifacts are now written for eval queries
- [x] Uploading the bundled Quran corpus now ingests into verse-level passages instead of giant chunks
- [x] Live upload -> index -> query flow works through the backend

### Completed Checklists

#### Repo and setup
- [x] Initialize repo and push to GitHub
- [x] Set up Python environment in the `ai` conda env
- [x] Get automated tests passing locally
- [x] Add `.gitignore` and keep generated state out of git

#### Core backend structure
- [x] Generic project / document / section / passage schema
- [x] Passage windows for local context
- [x] Query / retrieval / evidence / draft / verification persistence
- [x] FastAPI app and API routes for projects, documents, queries, evals

#### Ingestion
- [x] Raw + normalized text storage
- [x] Sectioning fallback
- [x] Passage building
- [x] Window building
- [x] Quran upload now splits into verse-level passages instead of giant chunks

#### Retrieval
- [x] Lexical retrieval
- [x] Dense retrieval
- [x] Hybrid merge
- [x] Reranking stage
- [x] Context expansion
- [x] Evidence bundle creation
- [x] Retrieval debug artifacts exposed through API

#### Evaluation foundations
- [x] Retrieval benchmark scaffolding exists
- [x] Eval runner exists
- [x] Grounding metrics scaffolding exists
- [x] Model comparison eval results captured for `llama3.1:8b` and `qwen2.5:7b`
- [x] Retrieval failure classification now exists for eval runs

---

## In Progress / Known Issues

- [ ] The upgraded `qwen2.5:7b` model still times out on some broad questions and still returns invalid verifier JSON on some cases
- [ ] The app currently relies on fallback answer/verification behavior more than intended
- [ ] Final answer quality is not yet at the intended product level
- [ ] UI messaging is still confusing in some states
- [ ] Older projects indexed before ingestion fixes may still contain giant chunks
- [ ] Some API paths work correctly but still need stronger end-to-end UI validation coverage
- [ ] Retrieval still misses too many paraphrase and theme questions in top-10

---

## Current Task

Use retrieval diagnostics to improve hit rates on paraphrase and thematic questions while keeping the upgraded local model in place:

retrieval + fallback extractive answers

to:

reliable grounded answers + reliable verifier output

Immediate focus:
- use eval debug artifacts to understand retrieval misses before changing retrieval weights or prompts
- keep `qwen2.5:7b` as the current default local model
- improve lexical coverage on paraphrase/theme queries
- improve user-facing UI/status messaging

---

## Next Priorities

1. make answer generation reliably return the required schema
2. make verifier generation reliably return the required schema
3. improve answer quality so the app gives concise grounded answers instead of fallback-style excerpts
4. add stronger API-level and UI-level end-to-end tests for upload, list, index, query, and result views
5. improve UI messaging around fallback behavior, verification warnings, and refresh state
6. rebuild or discard older projects created before the Quran passage-splitting fix
7. tune retrieval quality using the existing eval scaffolding and debug artifacts

### Remaining Checklists

#### Answer generation and verification
- [x] Prompt/schema infrastructure exists
- [x] Generator/verifier pipeline exists
- [x] Shared structured generation runner exists
- [x] Fallback extractive answer path exists when local model fails schema validation
- [x] Fallback deterministic verification path exists when local model fails schema validation
- [ ] Reliable schema-compliant answer generation from `qwen2.5:7b`
- [ ] Reliable schema-compliant verification from `qwen2.5:7b`
- [ ] Good user-facing answer quality without fallback behavior

#### Frontend
- [x] Basic project / document / ask-question flow exists
- [x] Query results and debug routes are wired
- [ ] UI messaging is polished and always reflects backend state clearly
- [ ] Upload / refresh UX needs one more cleanup pass

#### Retrieval tuning
- [x] Core retrieval pipeline is implemented
- [x] Retrieval tests exist
- [x] Eval dataset and runner exist
- [x] Eval debug artifacts and failure tags now exist
- [ ] Retrieval quality tuning is still needed
- [ ] Relevance quality for real user questions still needs iteration

#### Prompt / schema maturity
- [x] Schema models exist
- [x] Prompt templates exist
- [x] Validator layer exists
- [ ] `qwen2.5:7b` improves schema compliance but does not yet reliably follow the required schema
- [ ] This remains the main blocker for a strong final answer experience

---

## Admin Snapshot

- [x] Repo/setup baseline complete
- [x] Core backend and retrieval pipeline complete for MVP Step 1
- [x] Upload, ingestion, indexing, and retrieval-debug flow complete
- [x] Shared structured generation enforcement complete
- [x] Local model upgraded from `llama3.1:8b` to `qwen2.5:7b` based on measured eval results
- [x] Retrieval diagnostics loop is now in place
- [ ] Grounded answer generation quality still needs stabilization
- [ ] Verifier reliability still needs stabilization
- [ ] UI polish and end-to-end UX cleanup still pending

---

## Model Evaluation Summary

Current default local model:
- `qwen2.5:7b`

Measured on:
- dataset: `data/evals/questions.json`
- questions: 10
- project: `86da8892-b3c5-4a15-a174-1f8ff5179d6b`

Results:
- `llama3.1:8b`
  - fallback rate: `0.90`
  - full schema success rate: `0.10`
  - answer schema success rate: `0.10`
  - verifier schema success rate: `0.10`
- `qwen2.5:7b`
  - fallback rate: `0.50`
  - full schema success rate: `0.40`
  - answer schema success rate: `0.50`
  - verifier schema success rate: `0.40`

Decision:
- switch to `qwen2.5:7b` as the default local model

Remaining gap:
- even with `qwen2.5:7b`, fallback is still too common for production-quality behavior

---

## Retrieval Evaluation Summary

Measured on:
- dataset: `data/evals/questions.json`
- questions: 10
- mode: retrieval-only debug run
- results file: `data/evals/results/qwen2.5_7b_retrieval_debug_results.json`

Current retrieval metrics:
- hit@5: `0.50`
- hit@10: `0.50`
- failure count: `5`
- failure type distribution:
  - `lexical_miss`: `5`

Observed retrieval weaknesses:
- paraphrase queries about fasting/eating restrictions still miss expected passages in top-10
- broad thematic prompts like mercy and Moses still miss expected passages in top-10
- patience-themed retrieval also misses the expected anchor verses even though related verses are present elsewhere in the corpus

Known successful cases:
- fasting direct lookup
- prayer guidance
- giving to the poor
- rewards promised to the righteous
