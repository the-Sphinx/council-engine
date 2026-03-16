# MVP Core Architecture Spec  
## Source-Grounded Multi-Agent Interpretation App (V1)

**Purpose:** This document defines the **minimum viable architecture** for a text-only, source-grounded question answering webapp, starting with **Quran in English** as the first corpus, but designed **generically** so the same architecture can later support books, papers, notes, and other long textual sources.

**Primary V1 goal:**  
Implement a system where a user can upload or load a text corpus, ask a question, and receive an answer that is:
- grounded only in the uploaded source text,
- supported by citations,
- checked by a verifier,
- accompanied by a short “objections raised” section.

This spec is written for implementation by an AI coding agent. It is intentionally concrete and opinionated.

---

# 1. Scope

## In Scope for V1
- Single-user local/dev usage.
- Text-only corpus.
- One project containing one or more documents.
- Generic document ingestion pipeline.
- Generic document representation not tied to Quran.
- Hybrid retrieval:
  - lexical retrieval,
  - dense retrieval,
  - reranking,
  - context expansion.
- One grounded answer generator.
- One verifier.
- Output:
  - final answer,
  - citations,
  - short objections raised.
- Retrieval and grounding evaluation support.
- Simple Python backend and simple web frontend.

## Out of Scope for V1
- Audio/image/video ingestion.
- Multi-user auth.
- Fine-grained permissions.
- Production-grade deployment.
- Advanced debate UI.
- Full agent chatroom visible to users.
- External knowledge mode.
- Commentary/tafsir ingestion.
- Advanced memory graph / GraphRAG / hierarchical summarization.
- Medical workflows.

---

# 2. Product Principles

These principles are mandatory. The coding agent should optimize for them even if not explicitly repeated elsewhere.

## 2.1 Generic Core, Quran as First Dataset
The internal architecture must **not** assume:
- surah,
- ayah,
- verse structure,
- religious semantics.

Instead, the system must be built around generic concepts:
- Project
- Document
- Section
- Passage
- PassageWindow
- Citation
- RetrievalResult
- EvidenceBundle
- AnswerDraft
- VerificationReport

Quran should be represented through metadata only.

## 2.2 Source-Grounded by Default
V1 answers must use **only uploaded text**.  
No outside knowledge is allowed in final answers.

## 2.3 Retrieval Quality Is More Important Than Fancy Agent Behavior
Do not spend complexity budget on multi-agent theater until retrieval and verification are working.

## 2.4 Every Substantive Claim Must Be Traceable
The final answer must contain citations to passages that support the claim.  
If a claim cannot be supported, it must be removed or marked unsupported by verifier.

## 2.5 Simple, Inspectable, Modular
The architecture should be easy to inspect and debug:
- saved retrieval candidates,
- reranked results,
- evidence bundle,
- answer draft,
- verifier output.

---

# 3. Recommended Tech Stack

## Backend
- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL or SQLite for local dev
- Background jobs can be synchronous at first; optional lightweight task queue later

## Retrieval / Indexing
- BM25 or equivalent lexical retrieval
- Dense embeddings
- pgvector or a simple vector store for local/dev
- Optional reranker model
- Optional ColBERT-style reranker later

## Frontend
- Minimal web UI
- No major styling work required
- Core screens only:
  - projects
  - documents
  - ask question
  - answer + citations + objections

## Models
- Must be swappable behind interfaces
- Start with local/self-hosted or cheap hosted models
- Never hardcode a provider-specific implementation deep into business logic

---

# 4. High-Level Architecture

The system should be organized into the following modules:

1. **Project Module**
2. **Document Ingestion Module**
3. **Document Storage Module**
4. **Retrieval Module**
5. **Evidence Bundle Builder**
6. **Grounded Answer Generator**
7. **Verifier Module**
8. **Evaluation Module**
9. **API Layer**
10. **Frontend UI**

## 4.1 Request Flow
User asks question -> retrieval -> reranking -> context expansion -> evidence bundle -> grounded answer -> verifier -> final response

## 4.2 Design Constraint
Each stage must have its own input/output object and logs for debugging.  
Do not collapse everything into one giant function.

---

# 5. Data Model

The schema below is the most important part of the architecture.  
**Critical warning to coding agent:** do not design directly around “verse” or “surah”. Build generic entities.

## 5.1 Project
Represents a workspace.

Suggested fields:
- `id`
- `name`
- `description`
- `created_at`
- `updated_at`

## 5.2 Document
Represents one uploaded or loaded text source.

Suggested fields:
- `id`
- `project_id`
- `title`
- `source_type` (e.g. uploaded_text, uploaded_pdf, predefined_corpus)
- `language`
- `raw_text_path` or `raw_text`
- `normalized_text_path` or `normalized_text`
- `metadata_json`
- `created_at`

Notes:
- `metadata_json` should store flexible source-specific information.
- For Quran, metadata may include translator/version.

## 5.3 Section
Represents a logical document subdivision.

Examples:
- chapter
- heading
- subheading
- surah
- article section

Suggested fields:
- `id`
- `document_id`
- `parent_section_id` (nullable)
- `section_type`
- `title`
- `order_index`
- `start_offset`
- `end_offset`
- `metadata_json`

## 5.4 Passage
This is the atomic retrieval unit.

**Critical warning:** This is one of the easiest places for the coding agent to get the architecture wrong.

A Passage should:
- be small enough for precise citation,
- be stable across re-indexing,
- preserve location information.

Suggested fields:
- `id`
- `document_id`
- `section_id`
- `passage_index`
- `text`
- `normalized_text`
- `start_offset`
- `end_offset`
- `token_count`
- `metadata_json`

Quran example:
- one ayah may become one passage
- but architecture must not depend on that

Book example:
- one paragraph may become one passage

## 5.5 PassageWindow
A context-expanded retrieval object derived from one or more adjacent passages.

Suggested fields:
- `id`
- `document_id`
- `anchor_passage_id`
- `start_passage_index`
- `end_passage_index`
- `text`
- `normalized_text`
- `metadata_json`

Purpose:
- retrieval may hit a passage,
- answering usually needs local context,
- citations still point to atomic passages.

## 5.6 Citation
Represents a reference used in an answer.

Suggested fields:
- `id`
- `document_id`
- `section_id`
- `passage_id`
- `quote_text`
- `citation_label`
- `start_offset`
- `end_offset`
- `metadata_json`

**Critical warning:**  
Do not make citations freeform strings only.  
They must reference actual stored objects.

## 5.7 Query
Represents a user question.

Suggested fields:
- `id`
- `project_id`
- `question_text`
- `mode` (for V1 always `source_only`)
- `created_at`

## 5.8 RetrievalResult
Represents one candidate match produced during retrieval.

Suggested fields:
- `id`
- `query_id`
- `passage_id`
- `retrieval_method` (bm25, dense, hybrid, rerank)
- `raw_score`
- `rank`
- `metadata_json`

## 5.9 EvidenceBundle
Represents the final packet of evidence sent to the answer generator.

Suggested fields:
- `id`
- `query_id`
- `bundle_json`
- `created_at`

`bundle_json` should include:
- chosen passages,
- chosen windows,
- ranking metadata,
- rationale if available.

## 5.10 AnswerDraft
Represents the grounded draft answer before verification.

Suggested fields:
- `id`
- `query_id`
- `answer_text`
- `claims_json`
- `citations_json`
- `objections_json`
- `created_at`

## 5.11 VerificationReport
Represents verifier output.

Suggested fields:
- `id`
- `query_id`
- `status` (`pass`, `pass_with_warnings`, `fail`)
- `supported_claims_json`
- `unsupported_claims_json`
- `citation_issues_json`
- `notes_json`
- `created_at`

---

# 6. Ingestion Pipeline

## Goal
Turn raw source text into:
- sections,
- passages,
- lexical indexable units,
- vector indexable units,
- retrievable metadata.

## 6.1 Ingestion Steps
1. Create Project
2. Create Document
3. Normalize text
4. Detect or define sections
5. Split into Passages
6. Create PassageWindows
7. Create lexical index
8. Create dense embeddings
9. Persist all artifacts

## 6.2 Text Normalization Rules
Normalization should be deterministic and stored separately from raw text.

Suggested normalization:
- normalize whitespace
- standardize line breaks
- preserve punctuation unless retrieval experiments show otherwise
- optional lowercase normalized copy
- do not destroy original formatting needed for citations

**Critical warning:**  
Do not overwrite raw text with normalized text.  
Both must be preserved.

## 6.3 Sectioning
The ingestion pipeline must support:
- explicit section boundaries if available,
- fallback segmentation if not.

For Quran predefined corpus:
- section = surah
- passage = ayah

For generic future sources:
- section can be chapter/heading-based or heuristic.

## 6.4 Passage Creation
Passages should be:
- fine-grained enough for precise citations,
- but not so small that retrieval becomes meaningless.

V1 recommendation:
- if source has natural verse/paragraph units, use them
- otherwise use paragraph-level units

## 6.5 PassageWindow Creation
For every passage, create local windows for context.

Recommended:
- anchor passage alone
- anchor +/- 1 passage
- anchor +/- 2 passages

This can be implemented dynamically or precomputed.

**Critical warning:**  
Do not cite the whole window unless necessary.  
The window is for reasoning context. Citation should prefer atomic passage references.

---

# 7. Retrieval Architecture

This is the most important functional module in V1.

## 7.1 Retrieval Strategy
Use a multi-stage pipeline:

1. lexical retrieval
2. dense retrieval
3. merge candidates
4. rerank candidates
5. context expansion
6. evidence bundle construction

## 7.2 Lexical Retrieval
Implement BM25 or equivalent sparse lexical retrieval over passages.

Purpose:
- exact term matching
- important for text with repeated keywords or named concepts

## 7.3 Dense Retrieval
Implement embedding-based retrieval over passages.

Purpose:
- paraphrase matching
- semantic similarity
- non-verbatim retrieval

## 7.4 Hybrid Merge
Merge lexical and dense candidate lists.

Recommended initial strategy:
- retrieve top_k from lexical
- retrieve top_k from dense
- union by passage_id
- keep both scores
- compute hybrid score using weighted normalization

Store source scores for debugging.

**Critical warning:**  
Do not discard method-specific scores too early.  
You will need them for debugging retrieval failures.

## 7.5 Reranking
Apply a reranker over merged candidates.

Reranker input:
- user question
- candidate passage text

Reranker output:
- refined ranking score

If a strong reranker is not immediately available, implement architecture so reranking can be plugged in later.

## 7.6 Context Expansion
Once top anchor passages are selected, expand context using neighboring passages.

Recommended output object:
- anchor passage
- local context window
- parent section metadata

## 7.7 Evidence Bundle Construction
The retrieval system must output a coherent evidence bundle, not just a loose list of chunks.

Evidence bundle should include:
- top anchor passages
- their context windows
- section titles / source labels
- retrieval scores
- deduplicated overlaps

**Critical warning:**  
Do not pass raw top-k chunks directly into answer generation.  
First deduplicate and organize them.

---

# 8. Answer Generation

V1 uses one grounded answer generator.

## 8.1 Input
- user question
- source_only mode
- evidence bundle only

## 8.2 Output Requirements
The answer generator must output a structured object with:
- `final_answer`
- `supporting_citations`
- `objections_raised`
- `claims`

## 8.3 Grounding Rules
The answer generator must:
- answer only from evidence bundle
- avoid outside knowledge
- avoid unsupported generalization
- prefer “the text supports / suggests / states” language
- preserve ambiguity when evidence is ambiguous

## 8.4 Prompting Constraint
Prompt must clearly state:
- use only provided evidence
- if evidence is insufficient, say so
- do not invent support
- cite supporting passages for every substantive claim

**Critical warning:**  
Do not trust prompt alone for grounding.  
Prompting is necessary but insufficient. Verifier is mandatory.

---

# 9. Verifier Module

The verifier is required in V1.

## 9.1 Purpose
Check whether the answer draft is actually supported by cited passages and evidence bundle.

## 9.2 Verifier Input
- user question
- evidence bundle
- answer draft
- cited passages

## 9.3 Verifier Checks
1. Are cited passage IDs valid?
2. Does each substantive claim have support?
3. Does the cited passage actually support the claim?
4. Are there claims that go beyond the text?
5. Are objections needed because of ambiguity or weak support?

## 9.4 Verifier Output
- supported claims
- unsupported claims
- citation issues
- final status

## 9.5 Final Response Policy
If verifier status is:
- `pass`: return answer
- `pass_with_warnings`: return answer + warnings
- `fail`: either regenerate once or return constrained failure message

**Critical warning:**  
Do not silently pass unverifiable answers to the UI.

---

# 10. Evaluation Module

Evaluation must be built early, not later.

## 10.1 Purpose
Measure:
- retrieval quality
- citation correctness
- grounding quality
- unsupported claim rate

## 10.2 Eval Dataset Format
Each eval item should contain:
- `id`
- `question`
- `expected_relevant_passage_ids`
- `acceptable_alternative_passage_ids`
- `notes`
- `ambiguity_flag`

## 10.3 Retrieval Metrics
At minimum:
- recall@k
- precision@k
- hit@k for expected relevant passages

## 10.4 Grounding Metrics
At minimum:
- percent of claims supported
- citation validity rate
- unsupported claim count
- verifier fail rate

## 10.5 Manual Review Support
The system should expose a debug view or saved artifact showing:
- query
- top lexical hits
- top dense hits
- merged candidates
- reranked top hits
- final evidence bundle
- final answer
- verifier result

**Critical warning:**  
Without inspection artifacts, debugging retrieval will be slow and confusing.

---

# 11. API Design

Keep API simple and explicit.

## 11.1 Suggested Endpoints
- `POST /projects`
- `GET /projects`
- `POST /projects/{project_id}/documents`
- `GET /projects/{project_id}/documents`
- `POST /projects/{project_id}/index`
- `POST /projects/{project_id}/queries`
- `GET /queries/{query_id}`
- `GET /queries/{query_id}/retrieval-debug`
- `GET /queries/{query_id}/verification`

## 11.2 Query Execution Contract
When a query is created:
1. store query
2. run retrieval pipeline
3. build evidence bundle
4. generate answer draft
5. verify answer
6. persist outputs
7. return final response

---

# 12. Frontend Requirements

Keep frontend minimal.

## 12.1 Required Screens
1. Project list / create project
2. Document upload / corpus load
3. Ask question screen
4. Answer screen with:
   - final answer
   - citations
   - objections raised
   - optional debug link

## 12.2 Citation UX
Each citation should be clickable and map to:
- document
- section
- passage text

**Critical warning:**  
Do not present citations as plain labels without underlying navigable source text.

---

# 13. Directory / Module Structure (Suggested)

```text
app/
  api/
    projects.py
    documents.py
    queries.py
    evals.py
  core/
    config.py
    logging.py
    interfaces.py
  db/
    models.py
    session.py
    migrations/
  ingestion/
    loaders.py
    normalizer.py
    sectioner.py
    passage_builder.py
    window_builder.py
    indexer.py
  retrieval/
    lexical.py
    dense.py
    hybrid.py
    reranker.py
    context_expander.py
    evidence_bundle.py
  generation/
    answer_generator.py
    verifier.py
    prompts.py
  evaluation/
    dataset.py
    metrics.py
    runner.py
  schemas/
    api.py
    domain.py
  services/
    project_service.py
    document_service.py
    query_service.py
  ui/
    ...
tests/
  unit/
  integration/
  eval/
data/
  corpora/
  evals/
```

The coding agent may adapt this structure, but must preserve modular separation.

---

# 14. Interfaces to Keep Stable

These interfaces are important because model/retrieval providers may change later.

## 14.1 Embedder Interface
Methods:
- `embed_texts(texts: list[str]) -> list[list[float]]`
- `embed_query(text: str) -> list[float]`

## 14.2 LexicalRetriever Interface
Methods:
- `search(query: str, top_k: int) -> list[RetrievalCandidate]`

## 14.3 DenseRetriever Interface
Methods:
- `search(query: str, top_k: int) -> list[RetrievalCandidate]`

## 14.4 Reranker Interface
Methods:
- `rerank(query: str, candidates: list[RetrievalCandidate]) -> list[RetrievalCandidate]`

## 14.5 AnswerGenerator Interface
Methods:
- `generate(question: str, evidence_bundle: EvidenceBundle) -> AnswerDraft`

## 14.6 Verifier Interface
Methods:
- `verify(question: str, evidence_bundle: EvidenceBundle, answer_draft: AnswerDraft) -> VerificationReport`

**Critical warning:**  
Do not mix provider-specific model code directly into service code.  
Always keep model calls behind interfaces.

---

# 15. Error Handling Rules

## 15.1 If Retrieval Finds Weak Evidence
Return answer that explicitly says evidence is insufficient or ambiguous.

## 15.2 If Answer Generation Fails
Return structured error and keep retrieval artifacts persisted for inspection.

## 15.3 If Verification Fails
Do one constrained regeneration attempt max.  
Do not loop endlessly.

## 15.4 If Index Is Missing
Return clear actionable error.

---

# 16. Logging and Debugging Requirements

Every query execution should persist:
- question text
- lexical candidates
- dense candidates
- merged candidates
- reranked candidates
- selected evidence bundle
- answer draft
- verifier output

This can be DB-backed or file-backed in dev.

**Critical warning:**  
A coding agent may try to skip persistence for speed. Do not skip it. This project depends on inspectability.

---

# 17. Testing Strategy

## 17.1 Unit Tests
Must cover:
- text normalization
- passage splitting
- context window creation
- score merging
- citation object creation

## 17.2 Integration Tests
Must cover:
- ingest document -> index -> query -> answer -> verify flow

## 17.3 Eval Tests
Must cover:
- benchmark questions against known passages

## 17.4 Golden Cases
Create a small set of known questions for Quran corpus:
- direct lookup questions
- paraphrase questions
- multi-passage questions
- ambiguous questions

---

# 18. Implementation Order

This order is strongly recommended.

## Phase A: Core Data + Ingestion
1. Define DB schema
2. Implement project/document/section/passage models
3. Implement text loader and normalizer
4. Implement sectioning and passage creation
5. Implement passage window generation

## Phase B: Retrieval
6. Implement lexical retrieval
7. Implement dense retrieval
8. Implement hybrid merge
9. Implement reranking hook
10. Implement context expansion
11. Implement evidence bundle builder

## Phase C: Grounded Answering
12. Implement grounded answer generator
13. Implement verifier
14. Implement final response builder

## Phase D: API + UI
15. Add query API
16. Add retrieval-debug API
17. Build minimal ask/answer frontend

## Phase E: Evaluation
18. Implement eval dataset format
19. Implement retrieval metrics
20. Implement grounding metrics
21. Add benchmark runner

---

# 19. Non-Negotiable Anti-Patterns to Avoid

The coding agent must avoid these mistakes:

## 19.1 Do Not Make Quran-Specific Core Types
Wrong:
- `Surah`, `Ayah` as required universal schema

Right:
- generic `Section`, `Passage`
- Quran-specific metadata layered on top

## 19.2 Do Not Store Only Freeform Citation Strings
Citations must map to real source objects.

## 19.3 Do Not Skip the Verifier
Prompt-only grounding is not enough.

## 19.4 Do Not Pass Raw Top-k Chunks Directly to Generation
Build organized evidence bundles.

## 19.5 Do Not Couple Everything to One Model Provider
Use interfaces.

## 19.6 Do Not Optimize Frontend Early
Functionality first.

## 19.7 Do Not Hide Debug Information
Persist intermediate retrieval artifacts.

---

# 20. Definition of Done for MVP Core Architecture

The MVP core architecture is considered complete when the system can:

1. load a text corpus into a project  
2. parse it into generic sections and passages  
3. build lexical and dense retrieval artifacts  
4. accept a user question  
5. retrieve relevant passages using hybrid retrieval  
6. rerank and expand context  
7. create an evidence bundle  
8. generate a source-grounded answer draft  
9. verify support for the answer  
10. return:
    - final answer
    - citations
    - objections raised  
11. persist intermediate artifacts for debugging  
12. run a small evaluation set

---

# 21. Suggested Immediate Next Step After This Spec

After implementing this architecture skeleton, the next design artifact should be:

**Retrieval + Evaluation Design Spec**
covering:
- chunking rules
- scoring fusion
- reranking choices
- evidence bundle policy
- eval dataset format
- retrieval metrics and thresholds

This should be implemented before adding visible multi-agent debate.

