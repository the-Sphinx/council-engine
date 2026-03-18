# TASK — Lexical Recall Improvement

## Context

Before implementing anything read:

- MASTER_BRIEF.md
- DECISIONS.md
- PROGRESS.md

Do not violate rules in MASTER_BRIEF.md.

Current state:

- Retrieval debug + evaluation loop is implemented
- Current eval shows weak retrieval performance
- Failures are currently dominated by lexical misses
- Goal is to improve lexical recall for paraphrase and thematic questions

This task should focus only on retrieval-side improvements that increase recall without changing the overall system architecture.

---

## Task

Implement **lexical recall improvements** for paraphrase-heavy and theme-based queries, then re-run evaluation to measure the effect.

---

## Requirements

### 1. Improve query-side lexical normalization

Add or improve query preprocessing for lexical retrieval.

Possible techniques:

- lowercase normalization
- light stemming or lemmatization
- punctuation cleanup
- singular/plural normalization
- token cleanup for common stopword-heavy phrasing

Do **not** over-aggressively normalize source passages in a way that harms citation traceability.

Prefer query-side improvements first.

---

### 2. Add optional lightweight query expansion

Implement a controlled, lightweight query expansion mechanism for lexical retrieval.

Examples:

- mercy → compassion, forgiveness
- fasting → abstain, abstinence, Ramadan
- charity → alms, giving

This should be:

- configurable
- easy to inspect
- limited in scope
- easy to disable

Do **not** build a huge opaque synonym system.

Do **not** hardcode Quran-only concepts into the generic retrieval core. If domain-specific expansions are needed, keep them configurable and isolated.

---

### 3. Preserve retrieval transparency

The debug output must still clearly show:

- original query
- normalized query
- expanded query terms (if any)
- lexical top IDs
- dense top IDs
- merged/reranked IDs

We must be able to tell whether lexical improvements actually helped.

---

### 4. Do not touch these areas

This task should **not** modify:

- answer generator
- verifier
- schema definitions
- multi-agent logic
- UI
- multimodal support

This is a retrieval improvement task only.

---

### 5. Re-run evaluation

After implementing lexical recall improvements, re-run the retrieval evaluation.

Compare against the previous baseline:

- Hit@5
- Hit@10
- failure count
- failure type distribution

Also note whether previously failed paraphrase/thematic queries now succeed.

---

### 6. Update REVIEW_BUNDLE.md

Include:

- what lexical recall changes were implemented
- why those changes were chosen
- before/after retrieval metrics
- examples of recovered queries
- remaining failure patterns

---

### 7. Update PROGRESS.md

Add:

- latest retrieval metrics
- what improved
- what still fails
- recommended next retrieval step

---

## Constraints

- Do not replace hybrid retrieval
- Do not weaken inspectability
- Do not make query expansion opaque
- Do not hardcode domain logic in generic retrieval modules
- Keep changes modular and configurable

---

## Deliverables

- updated lexical retrieval/query preprocessing logic
- optional lightweight query expansion
- updated retrieval debug artifacts
- updated evaluation results
- updated PROGRESS.md
- updated REVIEW_BUNDLE.md

If a meaningful design choice is made, also update:

- DECISIONS.md

---

## Testing Requirements

At minimum:

### Functional tests
- lexical retrieval still works on direct lookup queries
- normalized queries do not break exact-match behavior
- query expansion can be enabled/disabled

### Evaluation checks
- compare before vs after retrieval metrics
- confirm whether known lexical misses improved

Be honest in REVIEW_BUNDLE.md about any uncertain gains.

---

## Reviewer Focus

In the review bundle, ask ChatGPT to inspect:

1. whether normalization is helpful without becoming destructive
2. whether query expansion remains explainable and configurable
3. whether the system still preserves generic architecture
4. whether improvements are real or just benchmark overfitting

---

## Definition of Done

This task is complete when:

1. lexical recall logic is improved
2. query expansion is available in a controlled way
3. retrieval debug output shows normalized/expanded query behavior
4. evaluation is re-run
5. before/after retrieval metrics are documented
6. PROGRESS.md and REVIEW_BUNDLE.md are updated

---

## Suggested Next Step

Depending on results, the next likely step will be one of:

- refine hybrid weighting
- improve reranking behavior
- expand/clean the benchmark dataset
