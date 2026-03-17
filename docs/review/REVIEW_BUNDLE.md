# REVIEW BUNDLE

## 1. Task Summary
- Task name: Retrieval debug and evaluation loop
- Date: 2026-03-17
- Branch: main
- Commit hash: pending commit
- Agent: Codex
- Status: completed

## 2. Objective
Turn retrieval evaluation into a practical diagnostic loop by storing expected passage IDs, per-stage retrieval IDs, and simple failure classifications for each eval query.

## 3. What Changed
- Extended the eval question set with verse-ref-backed ground truth for the current Sahih International Quran project
- Updated `scripts/run_model_eval.py` to resolve expected passage IDs, compute hit@5/hit@10, classify failures, and write per-query retrieval debug artifacts
- Added a retrieval-only mode so retrieval tuning can run without paying LLM latency
- Made the dense embedder prefer local cached sentence-transformer weights before falling back to hashing, so retrieval diagnostics reflect the intended dense retriever
- Ran a retrieval-only debug eval with `qwen2.5:7b` and saved the results plus per-query debug files

## 4. Files Changed
- scripts/run_model_eval.py
- data/evals/questions.json
- data/evals/results/qwen2.5_7b_retrieval_debug_results.json
- data/evals/debug/*.json
- app/retrieval/dense.py
- tests/unit/test_model_eval_script.py
- docs/DECISIONS.md
- docs/PROGRESS.md
- docs/review/REVIEW_BUNDLE.md

## 5. Architecture Impact
This change affects the evaluation workflow and retrieval observability.
It does not change answer generation, verification, schema definitions, or public API contracts.

## 6. Key Implementation Notes
- Ground truth is expressed as verse references in `data/evals/questions.json` and resolved to passage IDs at runtime for the current indexed Quran project
- Each eval query now writes a debug artifact containing lexical, dense, merged, and reranked IDs
- Failure classification is intentionally simple:
  - missing from lexical top-10 → `lexical_miss`
  - missing from dense top-10 → `dense_miss`
  - present before rerank but removed later → `rerank_miss`
  - otherwise → `unknown`
- The dense embedder now tries `local_files_only=True` first, which avoided the earlier misleading hashing fallback during retrieval-only eval runs

## 7. Risks / Known Issues
- Ground truth is still a small seed set of 10 questions, not a comprehensive benchmark
- Verse-ref expectations were validated from the Sahih International text and spot-checked online, but the set should still be reviewed and expanded
- All current failures classify as `lexical_miss`, which is useful but still coarse; there may be more nuanced query-understanding issues underneath

## 8. Alignment Check Against MASTER_BRIEF
- source grounding: preserved
- hybrid retrieval: preserved and now easier to inspect
- verification layer: unchanged
- generic schema: preserved
- inspectability: improved materially for retrieval evaluation

## 9. Testing Performed
- `conda run -n ai python -m pytest -q tests/unit/test_model_eval_script.py tests/unit/test_llm_client.py tests/integration/test_query_pipeline.py`
  - `25 passed in 19.82s`
- `conda run -n ai python -m pytest -q tests/unit/test_dense_embedder.py tests/unit/test_model_eval_script.py`
  - `6 passed in 0.08s`
- Retrieval-only eval run:
  - `conda run -n ai python scripts/run_model_eval.py --project-id 86da8892-b3c5-4a15-a174-1f8ff5179d6b --dataset data/evals/questions.json --model qwen2.5:7b --label retrieval_debug --no-generation`

## 10. Example Output / Logs
- Retrieval summary:
  - `hit@5 = 0.50`
  - `hit@10 = 0.50`
  - `failure_count = 5`
  - `failure_types = {"lexical_miss": 5}`
- Top failure examples:
  - `q002` patience
  - `q006` abstaining from food during a sacred period
  - `q007` mercy
  - `q008` Moses
  - `q010` eating restrictions
- Example success:
  - `q001` fasting now hits expected passages in top-5 once the cached dense model is used

## 11. Recommended Reviewer Focus
- Whether the current failure classifier is just detailed enough without overcomplicating the loop
- Whether the ground-truth verse mapping for the 10-question seed set looks sound
- Whether lexical retrieval is underperforming because of normalization/query wording, or whether the expected passages themselves need expansion for broad thematic questions

## 12. Suggested Next Step
Tune lexical retrieval for paraphrase and theme questions using these debug artifacts, then rerun the same retrieval-only eval to raise `hit@10` materially above `0.50`.
