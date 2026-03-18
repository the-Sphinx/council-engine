# TASK — Hybrid Weighting and Reranker Tuning

## Context

Before implementing anything read:

- `MASTER_BRIEF.md`
- `DECISIONS.md`
- `PROGRESS.md`

Do not violate rules in `MASTER_BRIEF.md`.

This task is based on the current retrieval architecture, where:

- lexical and dense retrieval both exist,
- candidates are merged by `passage_id`,
- lexical and dense scores are min-max normalized,
- a numeric hybrid score is computed,
- then candidates are reranked.

The current code already combines scores numerically before reranking. This is not a merge-only pipeline.

Current logic is approximately:

- merge lexical + dense candidate sets
- normalize lexical scores
- normalize dense scores
- compute `hybrid_score = alpha * lexical_score + beta * dense_score`
- sort by hybrid score
- rerank candidates

The current retrieval evaluation suggests:
- lexical recall improvements helped somewhat,
- gains are modest,
- at least one benchmark item regressed,
- the next likely lever is tuning hybrid weighting and reranker behavior rather than expanding lexical heuristics further.

---

## Goal

Turn hybrid retrieval from a fixed heuristic into a **measurable, configurable experiment surface**.

We want to answer questions like:

- Is the current `alpha=0.5, beta=0.5` mix actually good?
- Does stronger lexical weighting help the Quran benchmark?
- Does the reranker help or hurt on this corpus?
- Are overlap candidates (found by both lexical and dense retrieval) especially valuable?

---

## Task

Implement **configurable hybrid weighting and reranker tuning support**, then run evaluation experiments and document the results.

---

## Requirements

### 1. Make hybrid weights configurable

Expose configuration for at least:

- `hybrid_alpha`
- `hybrid_beta`

These should be settable through config and/or environment, not hardcoded.

The system should be able to run with examples like:

- lexical-heavy: `alpha=0.7, beta=0.3`
- balanced: `alpha=0.5, beta=0.5`
- dense-heavy: `alpha=0.3, beta=0.7`

Do not bury these values inside `hybrid.py`.

---

### 2. Add optional overlap boost

Add an optional configurable boost when a candidate appears in **both** lexical and dense retrieval results.

Suggested config ideas:

- `overlap_boost_enabled`
- `overlap_boost_value`

This should be small and controlled.

Purpose:
Candidates retrieved by both methods may deserve a ranking advantage.

Important:
- make this transparent
- include it in debug output
- do not hardcode Quran-specific logic

---

### 3. Make reranker behavior easier to compare

Add configuration for:

- reranker enabled / disabled
- reranker model name (already may exist; preserve or improve)
- top-k passed into reranking if configurable

We need to compare:

- hybrid without reranker
- hybrid with reranker

---

### 4. Extend evaluation to support experiment labels

Update the evaluation flow so we can run named experiments such as:

- `balanced_with_rerank`
- `lexical_heavy_with_rerank`
- `balanced_no_rerank`
- `overlap_boost_balanced`

Store experiment metadata in results.

Each evaluation result should clearly record:
- model name
- alpha
- beta
- overlap boost on/off + value
- reranker enabled/disabled
- label

---

### 5. Extend retrieval debug artifacts

Per-query debug output should now expose enough information to understand ranking behavior.

For each candidate, when practical, include:

- lexical score
- dense score
- normalized lexical score
- normalized dense score
- overlap status
- hybrid score
- rerank score
- final rank

We do not need giant dumps, but we do need enough visibility to explain regressions.

---

### 6. Run controlled experiments

Run at least these experiment variants:

1. balanced weights + reranker enabled  
2. lexical-heavy weights + reranker enabled  
3. balanced weights + reranker disabled  

Optional:
4. lexical-heavy + overlap boost  
5. dense-heavy + reranker enabled  

Use the current benchmark and compare:

- Hit@5
- Hit@10
- failure count
- failure type distribution
- regressions vs prior baseline

---

### 7. Identify whether reranker helps or hurts

This is a key deliverable.

The review bundle should explicitly answer:

- Does reranking improve top-k hit rate on the current benchmark?
- Does reranking rescue relevant candidates or suppress them?
- Are regressions caused before reranking or after reranking?

We need a real answer, not assumptions.

---

### 8. Update project memory files

Update:

- `PROGRESS.md`
- `REVIEW_BUNDLE.md`

If a meaningful retrieval design decision is made, also update:

- `DECISIONS.md`

---

## Constraints

- Do not change answer generation
- Do not change verifier schema
- Do not add new lexical expansion heuristics in this task
- Do not hardcode domain-specific weights
- Do not weaken inspectability
- Keep changes modular and configurable

---

## Deliverables

1. configurable hybrid weighting  
2. optional overlap boost  
3. reranker comparison support  
4. evaluation results for multiple experiment labels  
5. improved retrieval debug artifacts  
6. updated `PROGRESS.md`  
7. updated `REVIEW_BUNDLE.md`  

If needed:
8. updated `DECISIONS.md`

---

## Testing Requirements

At minimum:

### Functional
- hybrid pipeline still runs with default settings
- weight changes actually affect scoring
- overlap boost can be enabled/disabled
- reranker can be enabled/disabled cleanly

### Evaluation
- run required experiment variants
- compare before/after metrics
- document regressions honestly

### Debug visibility
- confirm per-query artifacts show enough score information to explain rank changes

---

## Reviewer Focus

In the review bundle, ask ChatGPT to inspect:

1. whether weights are truly configurable and not hidden
2. whether overlap boost is transparent and safe
3. whether reranker influence is now measurable
4. whether improvements are global or just benchmark overfitting
5. whether regressions can now be explained using debug artifacts

---

## Definition of Done

This task is complete when:

1. hybrid alpha/beta are configurable
2. overlap boost is available and configurable
3. reranker on/off comparison is easy to run
4. eval results clearly record experiment metadata
5. at least three retrieval experiments are run
6. retrieval debug artifacts explain score flow
7. `PROGRESS.md` and `REVIEW_BUNDLE.md` are updated

---

## Suggested Next Step

Based on results, the next likely step will be one of:

- keep current reranker and adopt better weights
- reduce reranker influence or disable it for this corpus
- improve benchmark quality / expand manual gold set
- investigate section-aware or context-aware reranking
