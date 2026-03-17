# REVIEW BUNDLE

## 1. Task Summary
- Task name: Model upgrade and local evaluation
- Date: 2026-03-17
- Branch: main
- Commit hash: pending commit
- Agent: Codex
- Status: completed

## 2. Objective
Evaluate whether switching the local Ollama model improves schema compliance, fallback rate, and answer quality enough to justify changing the project default.

## 3. What Changed
- Added `scripts/run_model_eval.py` to run model-specific evals against `data/evals/questions.json`
- Added per-query answer/verifier structured-generation stats so eval runs can measure fallback, retries, and schema success directly
- Ran baseline eval with `llama3.1:8b`, then removed it to free disk space
- Downloaded `qwen2.5:7b`, ran the same eval, and saved both result files plus a comparison summary
- Switched the recommended default local model from `llama3.1:8b` to `qwen2.5:7b`
- Updated progress and decisions docs with the measured outcome

## 4. Files Changed
- app/core/config.py
- app/generation/llm_client.py
- app/generation/answer_generator.py
- app/generation/verifier.py
- scripts/run_model_eval.py
- data/evals/questions.json
- data/evals/results/llama3.1_8b_results.json
- data/evals/results/qwen2.5_7b_results.json
- data/evals/results/model_comparison.json
- tests/unit/test_llm_client.py
- docs/DECISIONS.md
- docs/PROGRESS.md
- docs/review/REVIEW_BUNDLE.md

## 5. Architecture Impact
This change affects local-model configuration, answer/verifier eval observability, and project defaults.
It does not change the retrieval pipeline, schema definitions, evidence bundle contract, or public API schemas.

## 6. Key Implementation Notes
- Model switching was already possible through `LLM_MODEL`; the eval script now adds a clean model override path so comparisons do not require code edits
- The eval script records answer and verifier run metadata separately, including attempts, structured success, repair usage, fallback usage, and failure reason
- The disk-sensitive workflow was followed explicitly: baseline run first, old model deleted, new model pulled second
- The local `.env` was updated to `qwen2.5:7b` to match the installed model on this machine

## 7. Risks / Known Issues
- `qwen2.5:7b` is clearly better than `llama3.1:8b`, but fallback is still too high at 50%
- Broad or synthesis-heavy questions still time out on answer generation
- Verifier schema issues still occur on some prompts, including null `unsupported_claims[].claim_id`
- The eval script currently uses one fixed indexed Quran project rather than creating a fresh project per run

## 8. Alignment Check Against MASTER_BRIEF
- source grounding: preserved
- hybrid retrieval: unchanged
- verification layer: preserved
- generic schema: preserved
- inspectability: improved through per-query structured-generation stats in eval results

## 9. Testing Performed
- Targeted tests passed: `29 passed in 20.30s`
- Baseline model eval on `llama3.1:8b` over 10 questions
- Upgraded model eval on `qwen2.5:7b` over the same 10 questions
- Disk check before and after model swap confirmed enough space remained for the replacement pull

## 10. Example Output / Logs
- `llama3.1:8b` summary:
  fallback rate `0.90`, schema success rate `0.10`
- `qwen2.5:7b` summary:
  fallback rate `0.50`, schema success rate `0.40`
- Example remaining verifier failure on `qwen2.5:7b`:
  `unsupported_claims.0.claim_id` came back as `null`, forcing deterministic verifier fallback after 3 attempts

## 11. Recommended Reviewer Focus
- Whether `qwen2.5:7b` is the right default or whether a smaller/faster local model should also be benchmarked
- Whether verifier prompts should be tightened further before adding another model comparison round
- Whether eval metrics should be persisted in a more formal experiment-tracking shape later

## 12. Suggested Next Step
Tune verifier prompting and failure policy around `qwen2.5:7b`, then rerun the same 10-question eval to see whether fallback can be pushed materially below 50%.
