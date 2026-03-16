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
- local LLM answer generation and verification are still not reliably schema-compliant

Overall status:
- [x] Step 1 foundation is substantially implemented
- [x] Retrieval and indexing are operational
- [x] Inspectability/debug artifact persistence is operational
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
- [x] Fallback extractive answer path exists when the local model fails schema validation
- [x] Fallback deterministic verification path exists when the local model fails schema validation
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

---

## In Progress / Known Issues

- [ ] The configured Ollama model often times out or returns the wrong JSON shape
- [ ] The app currently relies on fallback answer/verification behavior more than intended
- [ ] Final answer quality is not yet at the intended product level
- [ ] UI messaging is still confusing in some states
- [ ] Older projects indexed before ingestion fixes may still contain giant chunks
- [ ] Some API paths work correctly but still need stronger end-to-end UI validation coverage

---

## Current Task

Stabilize the answer-generation layer so the product moves from:

retrieval + fallback extractive answers

to:

reliable grounded answers + reliable verifier output

Immediate focus:
- improve the local model behavior or replace the local model
- reduce schema failures and fallback frequency
- improve user-facing UI/status messaging

---

## Next Priorities

1. make answer generation reliably return the required schema
2. make verifier generation reliably return the required schema
3. improve answer quality so the app gives concise grounded answers instead of fallback-style excerpts
4. add stronger API-level and UI-level end-to-end tests for upload, list, index, query, and result views
5. improve UI messaging around fallback behavior, verification warnings, and refresh state
6. rebuild or discard older projects created before the Quran passage-splitting fix
7. tune retrieval quality using the existing eval scaffolding

### Remaining Checklists

#### Answer generation and verification
- [x] Prompt/schema infrastructure exists
- [x] Generator/verifier pipeline exists
- [x] Fallback extractive answer path exists when local model fails schema validation
- [x] Fallback deterministic verification path exists when local model fails schema validation
- [ ] Reliable schema-compliant answer generation from the configured local model
- [ ] Reliable schema-compliant verification from the configured local model
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
- [ ] Retrieval quality tuning is still needed
- [ ] Relevance quality for real user questions still needs iteration

#### Prompt / schema maturity
- [x] Schema models exist
- [x] Prompt templates exist
- [x] Validator layer exists
- [ ] Local model does not yet reliably follow the required schema
- [ ] This remains the main blocker for a strong final answer experience

---

## Admin Snapshot

- [x] Repo/setup baseline complete
- [x] Core backend and retrieval pipeline complete for MVP Step 1
- [x] Upload, ingestion, indexing, and retrieval-debug flow complete
- [ ] Grounded answer generation quality still needs stabilization
- [ ] Verifier reliability still needs stabilization
- [ ] UI polish and end-to-end UX cleanup still pending
