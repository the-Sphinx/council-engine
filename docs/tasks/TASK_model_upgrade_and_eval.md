# TASK — Model Upgrade + Evaluation (Local LLM)

## Context

Before implementing anything read:

- MASTER_BRIEF.md
- DECISIONS.md
- PROGRESS.md

Do not violate rules in MASTER_BRIEF.md.

Current state:

- Structured generation layer has been implemented
- Retrieval pipeline is operational
- Current model: llama3.1:8b (Ollama)
- Known issue: schema compliance and fallback frequency still need improvement

Goal of this task:

Evaluate whether switching to a stronger local model improves:
- schema compliance
- fallback rate
- answer quality

---

## Task

Implement configurable model selection + evaluation workflow.

---

## Requirements

### 1. Make model configurable

Refactor LLM client to support model selection via:

- environment variable OR
- config file

Example:

MODEL_NAME=qwen2.5:7b

Do NOT hardcode model names inside logic.

---

### 2. Add support for multiple models

Ensure the system can run with:

- llama3.1:8b (baseline)
- qwen2.5:7b (primary test)
- qwen2.5:3b (optional fallback for speed)

Switching models should NOT require code changes.

---

### 3. Add evaluation script

Create script:

scripts/run_model_eval.py

This script should:

1. load evaluation dataset (data/evals/questions.json)
2. run full pipeline for each question
3. collect metrics

---

### 4. Metrics to collect

For each run:

- total queries
- fallback count
- fallback rate (%)
- schema success rate
- average retries used
- errors (if any)

Store results in:

data/evals/results/<model_name>_results.json

---

### 5. Track structured generation stats

Capture:

- attempts per query
- success/failure
- repair used or not

---

### 6. Compare models

Run evaluation for:

1. llama3.1:8b
2. qwen2.5:7b

Optional:
3. qwen2.5:3b

Produce comparison summary.

---

### 7. Update PROGRESS.md

Add:

- current model used
- evaluation results
- observed fallback rate
- decision: keep or switch model

---

### 8. Update REVIEW_BUNDLE.md

Include:

- evaluation summary
- comparison between models
- recommendation

---

## Constraints

- Do not modify retrieval pipeline
- Do not modify schema definitions
- Do not remove fallback logic
- Keep architecture unchanged

This task is ONLY about model + evaluation.

---

## Deliverables

- configurable model support
- evaluation script
- evaluation results JSON
- updated PROGRESS.md
- updated REVIEW_BUNDLE.md

---

## Testing

Run at least 10–20 evaluation queries.

Ensure:

- pipeline runs end-to-end
- metrics are correctly calculated
- no crashes on failure cases

---

## Definition of Done

Task is complete when:

1. model can be switched without code changes
2. evaluation script runs successfully
3. fallback rate is measured
4. schema success rate is measured
5. comparison between models is available
6. recommendation is documented

---

## Suggested Next Step

Based on results:

IF qwen2.5 significantly improves schema compliance:
→ adopt it as default model

ELSE:
→ consider cloud-based model for evaluation stage
