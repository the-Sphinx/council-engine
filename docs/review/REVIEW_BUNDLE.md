# REVIEW BUNDLE

## 1. Task Summary
- Task name: Hybrid weighting and reranker tuning
- Date: 2026-03-17
- Branch: main
- Commit hash: pending commit
- Agent: Codex
- Status: completed

## 2. Objective
Turn hybrid retrieval into a configurable experiment surface so weight choices, overlap boost, and reranker impact can be measured instead of assumed.

## 3. What Changed
- Added explicit hybrid tuning config in `app/core/config.py` and `config.yaml` for:
  - `hybrid_alpha`
  - `hybrid_beta`
  - `overlap_boost_enabled`
  - `overlap_boost_value`
  - `reranker_top_k`
- Updated `app/core/interfaces.py` and `app/retrieval/hybrid.py` to preserve raw lexical/dense scores, compute normalized score fields separately, and track overlap metadata on each candidate
- Updated `app/retrieval/pipeline.py` and `app/services/query_service.py` so debug artifacts now include normalized scores, overlap status, overlap boost, hybrid score, and rerank score
- Extended retrieval debug persistence/API with retrieval config metadata so a query can be tied back to the fusion settings that produced it
- Extended `scripts/run_model_eval.py` to support named experiment labels plus per-run overrides for weights, overlap boost, reranker on/off, and reranker top-k
- Made the eval runner read-only with synthetic query IDs so experiment runs no longer need to insert `Query` rows into the main SQLite DB
- Ran controlled retrieval-only experiments for balanced, lexical-heavy, reranker-off, and overlap-boost variants

## 4. Files Changed
- app/core/interfaces.py
- app/core/config.py
- app/retrieval/hybrid.py
- app/retrieval/pipeline.py
- app/services/query_service.py
- app/api/queries.py
- app/schemas/api.py
- app/db/models.py
- app/db/bootstrap.py
- config.yaml
- scripts/run_model_eval.py
- scripts/run_eval.py
- data/evals/results/qwen2.5_7b_balanced_with_rerank_results.json
- data/evals/results/qwen2.5_7b_lexical_heavy_with_rerank_results.json
- data/evals/results/qwen2.5_7b_balanced_no_rerank_results.json
- data/evals/results/qwen2.5_7b_overlap_boost_balanced_results.json
- tests/unit/test_hybrid.py
- tests/integration/test_query_pipeline.py
- tests/integration/test_retrieval_debug_api.py
- tests/unit/test_model_eval_script.py
- docs/DECISIONS.md
- docs/PROGRESS.md
- docs/review/REVIEW_BUNDLE.md

## 5. Architecture Impact
This change stays inside retrieval and inspectability boundaries.
It does not change answer generation, verifier behavior, UI, or the core hybrid architecture.

## 6. Key Implementation Notes
- Raw lexical and dense scores are no longer overwritten during normalization; normalized scores are stored separately on each candidate
- The optional overlap boost is explicit and small, and the candidate debug artifacts show whether it was applied
- Eval runs now record experiment metadata directly in the output summary and each per-query record
- The current reranker remains the same model, but its influence is now measurable because we can compare reranker-on vs reranker-off runs with the same benchmark
- The read-only eval runner change removes the earlier SQLite write contention we saw when experiments were launched in parallel

## 7. Risks / Known Issues
- The benchmark is still only 10 questions, so the tuning conclusions are directional rather than definitive
- None of the simple hybrid variants improved hit@10 beyond the current lexical-recall baseline
- The current reranker is now measurable, but this benchmark does not show a retrieval gain from using it
- Remaining failures still classify as `lexical_miss`, so the next bottleneck likely sits before reranking

## 8. Alignment Check Against MASTER_BRIEF
- source grounding: preserved
- hybrid retrieval: preserved
- verification layer: unchanged
- generic schema: preserved
- inspectability: improved materially for ranking analysis and experiment comparison

## 9. Testing Performed
- `conda run -n ai python -m pytest -q tests/unit/test_hybrid.py tests/integration/test_retrieval_debug_api.py tests/integration/test_query_pipeline.py tests/unit/test_model_eval_script.py`
  - `24 passed in 5.89s`
- Controlled retrieval-only experiments:
  - `balanced_with_rerank`
  - `lexical_heavy_with_rerank`
  - `balanced_no_rerank`
  - `overlap_boost_balanced`

## 10. Example Output / Logs
- `balanced_with_rerank`
  - `hit@5 = 0.50`
  - `hit@10 = 0.60`
- `lexical_heavy_with_rerank`
  - `hit@5 = 0.40`
  - `hit@10 = 0.60`
- `balanced_no_rerank`
  - `hit@5 = 0.50`
  - `hit@10 = 0.60`
- `overlap_boost_balanced`
  - `hit@5 = 0.50`
  - `hit@10 = 0.60`
- Current measurable answer to the reranker question:
  - reranking did not improve top-k hit rate on the current benchmark
  - current misses are still happening before reranking, not because of reranking

## 11. Recommended Reviewer Focus
- Whether the new weight and overlap settings are truly configurable and not hidden
- Whether the overlap boost stays transparent and corpus-agnostic
- Whether the current benchmark is large enough to justify keeping or removing the reranker in defaults
- Whether the remaining misses point toward reranker replacement, dense retriever changes, or benchmark refinement
- Whether the new debug fields are sufficient to explain rank changes and regressions

## 12. Suggested Next Step
Use the new experiment/debug surface to inspect the four remaining misses and decide whether the next retrieval task should target dense retrieval quality, reranker replacement, or benchmark expansion rather than simple fusion-weight tuning.
