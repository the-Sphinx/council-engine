# Retrieval + Evaluation Design Spec
## For the MVP Source-Grounded Interpretation App (V1)

**Purpose:** This document defines the **retrieval system**, **evidence bundle logic**, and **evaluation framework** for the MVP described in `mvp_core_architecture_spec.md`.

This spec is written for implementation by an AI coding agent. It is intentionally concrete and optimized for:
- **source-only grounding**
- **generic long-text retrieval**
- **debuggability**
- **low-cost iteration in development**
- **future extensibility beyond Quran**

---

# 1. Objectives

## 1.1 Primary Retrieval Objective
Given a user question, retrieve the **most relevant source passages** from the uploaded corpus such that:
- the answer generator can answer from those passages alone,
- the verifier can validate support,
- the final answer remains grounded in source text.

## 1.2 Primary Evaluation Objective
Measure whether the system:
- retrieves the right passages,
- preserves necessary context,
- avoids unsupported claims,
- exposes uncertainty when evidence is weak or ambiguous.

## 1.3 V1 Constraint
V1 is **source-only**.  
Retrieval must operate only over uploaded/indexed source text.  
No outside knowledge retrieval is allowed.

---

# 2. High-Level Retrieval Strategy

Use a **multi-stage retrieval pipeline**:

1. query preprocessing
2. lexical retrieval
3. dense retrieval
4. candidate merge
5. reranking
6. context expansion
7. evidence bundle creation
8. grounded answer generation
9. verification
10. evaluation logging

**Critical warning to coding agent:**  
Do **not** replace this with “just dense vector search.”  
Dense-only retrieval is not acceptable for V1.

---

# 3. Retrieval Design Principles

## 3.1 Retrieval Must Be Generic
The retrieval system must not assume Quran-specific structure.  
It should work for:
- religious texts,
- books,
- papers,
- notes,
- long reports.

Quran is only the first corpus.

## 3.2 Use Atomic Retrieval Units + Context Windows
The system should retrieve **small atomic passages** and then expand into windows for reasoning context.

Do not retrieve only giant chunks.

## 3.3 Preserve Explainability
Every retrieval stage must be inspectable:
- lexical hits
- dense hits
- merged candidates
- reranked list
- selected evidence bundle

## 3.4 Optimize for Recall First, Then Precision
Early retrieval stages should not be overly aggressive.  
It is better to over-retrieve slightly and use reranking than to miss the key evidence.

## 3.5 Evaluation Is Part of Retrieval Design
Do not design retrieval without a testable benchmark.

---

# 4. Retrieval Units

This section is one of the most critical in the entire project.

## 4.1 Atomic Passage
The atomic passage is the fundamental retrieval and citation unit.

Properties:
- small enough for precise citation
- stable identity
- tied to exact location in source
- semantically coherent if possible

Examples:
- Quran: one ayah
- book: one paragraph
- paper: one paragraph or sentence group
- notes: one paragraph or bullet group

## 4.2 Passage Window
A passage window is a context object built from neighboring atomic passages.

Purpose:
- preserve local context
- help answer generation
- reduce decontextualization

Recommended window variants:
- anchor only
- anchor +/- 1
- anchor +/- 2

## 4.3 Section Metadata
Every passage should carry parent metadata:
- document title
- section title
- section order
- passage order

This is useful for reranking and evidence presentation.

## 4.4 Why This Matters
**Likely coding-agent failure:** using only large chunks to reduce implementation effort.

That is wrong because:
- citations become vague,
- retrieval becomes noisy,
- verifier support becomes weak,
- local context cannot be controlled properly.

**Required design:**  
Use atomic passages for retrieval/citation, and windows for reasoning context.

---

# 5. Corpus Preparation

## 5.1 Raw and Normalized Text
Store both:
- raw text
- normalized text

The retriever may use normalized text, but citations must still map cleanly to raw/source text.

## 5.2 Normalization Rules
Recommended:
- normalize whitespace
- normalize line endings
- optional lowercase normalized copy
- preserve punctuation in raw text
- optionally strip repeated headers/footers in imported files

## 5.3 Generic Sectioning
Sectioning should be metadata-driven where possible.

Priority:
1. explicit source section boundaries
2. structural headings
3. heuristic section fallback

## 5.4 Passage Splitting Rules
Recommended V1:
- if source has natural atomic units, use them
- otherwise split by paragraph
- avoid fixed token chunking as primary method

**Critical warning:**  
Do not use arbitrary 500-token chunking as the default ingestion strategy.  
That may be acceptable for quick prototypes, but it is a bad default for this product.

---

# 6. Indexing Design

## 6.1 Required Indices
V1 should build:
1. lexical index over atomic passages
2. dense vector index over atomic passages
3. optional metadata index/filtering support

## 6.2 Lexical Index
Purpose:
- exact term matching
- named concepts
- phrase-level retrieval
- terminology-sensitive cases

Examples:
- Ramadan
- fasting
- Moses
- prayer
- mercy

## 6.3 Dense Index
Purpose:
- semantic matching
- paraphrase handling
- non-verbatim retrieval
- thematic similarity

## 6.4 Metadata Signals
These are not standalone retrievers, but useful retrieval/rerank signals:
- document title
- section title
- position in document
- source version / language
- passage length

## 6.5 Index Persistence
Indices must be persistent or reproducibly rebuildable.  
For local/dev, persistence can be filesystem-based.

**Critical warning:**  
Do not make indexing ephemeral only in memory unless explicitly configured for tests.

---

# 7. Query Processing

## 7.1 Input
A user question in natural language.

## 7.2 Minimal Query Preprocessing
Recommended:
- trim whitespace
- preserve original query text
- optionally create normalized query copy
- do not aggressively rewrite query in V1

## 7.3 Optional Query Expansion
V1 may later support internal query expansion, but should not depend on it initially.

Reason:
- expansion can improve recall,
- but it can also distort source-only retrieval if done too aggressively.

**V1 recommendation:**  
Keep original query and maybe one light normalized form only.

## 7.4 Query Logging
Persist:
- raw query
- normalized query
- retrieval configuration used

---

# 8. Multi-Stage Retrieval Pipeline

## 8.1 Stage 1: Lexical Retrieval
Retrieve top_k_lexical atomic passages using BM25 or equivalent.

Suggested initial top_k:
- 20 to 50

Why not too small:
- early recall matters
- user question wording may only partially match text

## 8.2 Stage 2: Dense Retrieval
Retrieve top_k_dense atomic passages using embeddings.

Suggested initial top_k:
- 20 to 50

## 8.3 Stage 3: Candidate Merge
Merge lexical and dense candidate sets by `passage_id`.

Store:
- lexical score
- dense score
- source retriever(s)
- merged candidate rank info

## 8.4 Stage 4: Score Normalization
Normalize scores before fusion.

Recommended:
- min-max normalization per retrieval method over current candidate set
- or rank-based normalization if score scales are unstable

## 8.5 Stage 5: Hybrid Fusion
Compute hybrid score.

Suggested initial formula:
```text
hybrid_score = alpha * lexical_norm + beta * dense_norm
```

Initial weights:
- `alpha = 0.5`
- `beta = 0.5`

These are starting defaults only and should be tunable.

**Critical warning:**  
Do not hardcode retrieval fusion weights without configuration support.

## 8.6 Stage 6: Reranking
Apply reranker to top merged candidates.

Reranker input:
- query
- candidate atomic passage text
- optionally section title

Reranker output:
- rerank score
- final rank

Suggested rerank candidate count:
- top 20 to 40 merged candidates

## 8.7 Stage 7: Anchor Selection
Select top anchor passages after reranking.

Suggested initial anchor count:
- 5 to 10

## 8.8 Stage 8: Context Expansion
For each anchor passage:
- attach local window
- attach section metadata
- record anchor-to-window mapping

## 8.9 Stage 9: Evidence Bundle Creation
Combine anchors and windows into one coherent bundle.

Bundle must:
- deduplicate overlaps
- preserve ranking and support metadata
- remain small enough for answer generation

---

# 9. Retrieval Configuration

Make retrieval configurable.  
This is required for experimentation.

Suggested configuration object:

```yaml
retrieval:
  top_k_lexical: 30
  top_k_dense: 30
  top_k_rerank: 25
  top_k_anchors: 6
  lexical_weight: 0.5
  dense_weight: 0.5
  context_window_radius: 1
  max_bundle_passages: 12
  min_anchor_score: null
  reranker_enabled: true
```

**Critical warning:**  
Coding agent should not bury retrieval configuration inside random constants scattered across files.

---

# 10. Candidate Data Structure

Define a stable internal candidate object.

Suggested fields:
- `passage_id`
- `document_id`
- `section_id`
- `passage_text`
- `normalized_text`
- `lexical_score`
- `dense_score`
- `hybrid_score`
- `rerank_score`
- `source_methods`
- `rank_lexical`
- `rank_dense`
- `rank_hybrid`
- `rank_rerank`
- `metadata`

This object should move through the retrieval pipeline.

---

# 11. Reranking Design

## 11.1 Purpose
Reranking improves precision after broad-recall retrieval.

## 11.2 Reranker Scope
V1 reranking happens over **atomic passages**, not windows.

Reason:
- more precise matching
- easier debugging
- more stable citation alignment

## 11.3 If No Strong Reranker Is Available
Architecture must still support:
- no-op reranker
- simple scoring reranker
- later upgrade to stronger model

## 11.4 Important Warning
Do not allow the reranker to directly replace retrieval with generated reasoning.  
It should rank candidates, not synthesize an answer.

---

# 12. Context Expansion Design

## 12.1 Goal
Restore enough local context for interpretation without losing citation precision.

## 12.2 Window Policy
For each selected anchor:
- fetch anchor passage
- fetch neighboring passages according to `context_window_radius`
- assemble one passage window

## 12.3 Deduplication
If neighboring windows overlap, merge or deduplicate them.

## 12.4 Context Expansion Output
For each anchor:
- anchor passage
- expanded window text
- list of included passage IDs
- section metadata

## 12.5 Important Warning
Do not let context expansion silently alter the cited anchor.  
The anchor remains the primary cited object. The window is supporting context.

---

# 13. Evidence Bundle Design

This is one of the most important modules after retrieval itself.

## 13.1 Purpose
Turn raw retrieved material into a usable, coherent packet for grounded answer generation.

## 13.2 Evidence Bundle Structure
Suggested structure:

```json
{
  "query_id": "...",
  "mode": "source_only",
  "anchors": [
    {
      "passage_id": "...",
      "text": "...",
      "rank": 1,
      "scores": {
        "lexical": 0.91,
        "dense": 0.77,
        "hybrid": 0.84,
        "rerank": 0.93
      },
      "section": {
        "title": "...",
        "order_index": 3
      },
      "window": {
        "included_passage_ids": ["...", "...", "..."],
        "text": "..."
      }
    }
  ]
}
```

## 13.3 Bundle Policies
The evidence bundle should:
- prefer top-ranked anchors
- include enough context for interpretation
- remain compact
- avoid repeated near-duplicate windows

## 13.4 Suggested V1 Limits
- 5 to 8 anchors
- up to 12 total atomic passages represented
- compact enough for cheap answer generation

## 13.5 Important Warning
Do not hand the model:
- raw full documents
- too many overlapping chunks
- unordered candidate lists

A messy bundle will degrade grounding quality.

---

# 14. Answer Generation Requirements (Retrieval-Side)

Even though answer generation is specified elsewhere, retrieval must support it properly.

## 14.1 Answer Generator Input Contract
It must receive:
- question
- mode = source_only
- structured evidence bundle
- citation-ready passage references

## 14.2 Retrieval-Side Requirements
The retrieval system must provide enough evidence for the answer generator to:
- quote or paraphrase correctly
- compare passages
- state uncertainty when evidence is incomplete

## 14.3 Important Warning
Do not force the answer generator to reconstruct structure from a flat text blob.

---

# 15. Verifier-Side Support Requirements

The verifier depends on retrieval outputs.

Required:
- stable passage IDs
- citation-to-passage mapping
- access to raw anchor passages
- access to context windows

Without that, verification becomes weak and expensive.

---

# 16. Evaluation Design Overview

Evaluation has three layers:
1. retrieval evaluation
2. grounding/citation evaluation
3. qualitative/manual review support

## 16.1 Why Build Eval Early
Without evaluation:
- retrieval tuning becomes guesswork,
- agent behavior may hide retrieval failures,
- progress becomes anecdotal.

---

# 17. Eval Dataset Design

## 17.1 Eval Item Schema
Each eval item should include:

```json
{
  "id": "q001",
  "question": "What does the text say about fasting?",
  "mode": "source_only",
  "expected_relevant_passage_ids": ["p123", "p124"],
  "acceptable_alternative_passage_ids": ["p220"],
  "minimum_expected_count": 1,
  "ambiguity_flag": false,
  "notes": "Core references should include the main fasting passage."
}
```

## 17.2 Why Alternatives Matter
Some questions may be answerable from more than one passage set.  
Do not force a single brittle gold answer if multiple valid anchors exist.

## 17.3 Eval Categories
Build at least these categories:

### A. Direct lookup questions
Example:
- Where is fasting discussed?

### B. Paraphrase questions
Example:
- What does the text say about abstaining during a sacred period?

### C. Multi-passage synthesis questions
Example:
- What themes are associated with patience and prayer?

### D. Ambiguous questions
Example:
- What is the text’s overall philosophy of hardship?

### E. Trap questions
Questions likely to tempt outside knowledge or unsupported generalization

---

# 18. Retrieval Metrics

## 18.1 Hit@K
Whether at least one expected relevant passage appears in top K.

Track at:
- Hit@5
- Hit@10
- Hit@20

## 18.2 Recall@K
Fraction of expected relevant passages retrieved in top K.

## 18.3 Precision@K
Fraction of top K retrieved passages that are relevant.

## 18.4 MRR (Optional)
Useful if gold labels are strong and ranking quality matters.

## 18.5 Section-Level Recall (Optional)
For some questions, retrieving the correct section may matter even if exact passage differs.

## 18.6 Recommended V1 Focus
Start with:
- Hit@5
- Hit@10
- Recall@10
- manual retrieval inspection

**Critical warning:**  
Do not overcomplicate the first eval dashboard.

---

# 19. Grounding / Citation Metrics

These are required because retrieval alone is not enough.

## 19.1 Citation Validity Rate
Percentage of cited passage IDs that exist and resolve correctly.

## 19.2 Claim Support Rate
Percentage of substantive claims judged supported by cited evidence.

## 19.3 Unsupported Claim Count
Count unsupported claims per answer.

## 19.4 Verifier Warning Rate
How often verifier detects weak support.

## 19.5 Ambiguity Handling Rate
For ambiguous eval items, whether the system preserves ambiguity rather than overclaiming.

---

# 20. Manual Review Protocol

Because fully automatic grading is imperfect, support manual review.

For each eval query, save:
- query text
- top lexical hits
- top dense hits
- merged candidates
- reranked anchors
- evidence bundle
- answer draft
- cited passages
- verifier report

This should be exportable or inspectable.

**Critical warning:**  
A coding agent may skip this because it is “not user-facing.”  
Do not skip it. This is central to tuning.

---

# 21. Initial Eval Set Size

Recommended:
- 30 questions minimum
- 50 better
- 100 ideal for early iteration

Balance:
- direct
- paraphrase
- synthesis
- ambiguity
- trap

Do not wait for a huge perfect dataset before starting.

---

# 22. Eval Workflow

## 22.1 Offline Eval Runner
Implement an eval runner that:
1. loads eval items
2. runs retrieval pipeline
3. computes retrieval metrics
4. runs answer generation
5. runs verifier
6. computes grounding metrics
7. writes results to JSON/CSV/DB

## 22.2 Reproducibility
Every eval run should record:
- timestamp
- git commit if available
- retrieval config
- model config
- corpus version

## 22.3 Important Warning
Do not compare eval runs if configuration metadata is missing.

---

# 23. Error Analysis Workflow

For failed queries, classify the failure:

## 23.1 Failure Types
- lexical miss
- dense miss
- fusion issue
- reranker issue
- context expansion too small
- context expansion too noisy
- evidence bundle overload
- answer generation overreach
- verifier miss

## 23.2 Why This Matters
Without failure typing, tuning will be random.

---

# 24. Recommended Initial Defaults

These are starting defaults only.

## 24.1 Passage Policy
- atomic unit: natural source unit if available, else paragraph
- context radius: 1

## 24.2 Retrieval
- top_k_lexical = 30
- top_k_dense = 30
- top_k_rerank = 25
- top_k_anchors = 6

## 24.3 Fusion
- lexical_weight = 0.5
- dense_weight = 0.5

## 24.4 Evidence Bundle
- max total anchor passages = 6
- max total included passage IDs after expansion = 12

## 24.5 Eval
- evaluate Hit@5, Hit@10, Recall@10
- save all debug artifacts

---

# 25. Thresholds and Guardrails

Do not hard-fail the product on weak metrics initially, but track them.

Suggested early targets:
- Hit@10 >= 0.80 on direct lookup questions
- lower but improving on paraphrase/synthesis questions
- unsupported claim count trending downward over iterations

These are directional goals, not strict production SLAs.

---

# 26. Recommended Implementation Order

## Phase 1: Retrieval Skeleton
1. define retrieval candidate schema
2. implement lexical retrieval
3. implement dense retrieval
4. implement candidate merge
5. implement score normalization
6. implement hybrid fusion

## Phase 2: Precision Improvements
7. implement reranker interface
8. add reranking
9. implement anchor selection
10. implement context expansion
11. implement evidence bundle builder

## Phase 3: Evaluation
12. define eval dataset schema
13. create first 30 eval questions
14. implement retrieval metrics
15. implement eval runner
16. implement saved debug artifacts

## Phase 4: Grounding Metrics
17. integrate answer generator
18. integrate verifier
19. implement citation/claim support metrics

---

# 27. Anti-Patterns to Avoid

## 27.1 Dense-Only Retrieval
Not acceptable for V1.

## 27.2 Giant Fixed Chunks
Bad for citation precision and interpretability.

## 27.3 No Saved Intermediate Retrieval Artifacts
Makes tuning much harder.

## 27.4 Flat Unstructured Evidence Dump
Bad for generation and verification.

## 27.5 Over-Reliance on Prompt Tricks
Retrieval and verification must do real work.

## 27.6 Quran-Specific Hardcoding in Core Retrieval
Avoid special-case logic in generic retrieval code.

---

# 28. Minimal Deliverables for “Retrieval + Evaluation Complete”

This module is considered complete for MVP when the system can:

1. retrieve atomic passages with lexical search  
2. retrieve atomic passages with dense search  
3. merge them into one candidate set  
4. rerank candidates  
5. expand selected anchors into windows  
6. create a structured evidence bundle  
7. run an eval set and compute retrieval metrics  
8. save debug artifacts for every query  
9. support answer generator and verifier with citation-ready evidence  

---

# 29. Suggested Next Artifact After This One

After implementing this spec, the next implementation doc should be:

**Prompt + Output Schema Spec**
covering:
- grounded answer generator prompt
- verifier prompt
- strict answer JSON schema
- claim schema
- objections schema
- citation rendering schema

That should be done before adding visible multi-agent debate.

