# TASK — Retrieval Debug + Evaluation Loop

## Context

Before implementing anything read:

- MASTER_BRIEF.md
- DECISIONS.md
- PROGRESS.md

Current state:

- Retrieval pipeline exists (lexical + dense + rerank)
- Evaluation script exists
- Model is upgraded (qwen2.5)
- System is stable enough for evaluation-driven improvement

---

## Goal

Turn evaluation into a **diagnostic tool** to systematically improve retrieval quality.

---

## Task

Implement a **retrieval debug + evaluation loop system**.

---

## Requirements

### 1. Extend evaluation output

Modify evaluation script to store:

For each query:

- query
- expected_passage_ids
- retrieved_passage_ids (top K)
- hit@K result (true/false)
- model used

---

### 2. Add retrieval debug artifact

For each query store:

{
  "query": "...",
  "top_lexical_ids": [...],
  "top_dense_ids": [...],
  "merged_ids": [...],
  "reranked_ids": [...]
}

Save under:

data/evals/debug/<query_id>.json

---

### 3. Failure detection

Mark a query as failure if:

expected passage not in top K

---

### 4. Failure classification (simple version)

Add tags:

- lexical_miss
- dense_miss
- rerank_miss
- unknown

Heuristic:

- not in lexical → lexical_miss
- not in dense → dense_miss
- present but removed later → rerank_miss

---

### 5. Summary metrics

Extend evaluation summary:

- Hit@5
- Hit@10
- failure_count
- failure_types distribution

---

### 6. Update REVIEW_BUNDLE.md

Include:

- retrieval performance summary
- top failure examples
- suspected causes

---

### 7. Update PROGRESS.md

Add:

- current Hit@K metrics
- known retrieval weaknesses

---

## Constraints

- Do not modify answer generation
- Do not modify schema
- Do not modify verifier

---

## Deliverables

- updated evaluation script
- debug artifacts per query
- failure classification
- updated PROGRESS.md
- updated REVIEW_BUNDLE.md

---

## Definition of Done

- retrieval failures are clearly visible
- failure causes are identifiable
- metrics are tracked
