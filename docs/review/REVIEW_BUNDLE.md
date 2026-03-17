# REVIEW BUNDLE

## 1. Task Summary
- Task name: Structured generation enforcement layer
- Date: 2026-03-17
- Branch: main
- Commit hash: pending commit
- Agent: Codex
- Status: completed

## 2. Objective
Implement a shared structured-generation layer so answer generation and verification both use the same JSON cleanup, parsing, validation, retry, and failure-reporting flow before falling back.

## 3. What Changed
- Added a shared structured-generation runner with retry, safe JSON cleanup, and structured failure metadata
- Refactored the answer generator to use the shared runner and keep only answer-specific post-validation/fallback logic
- Refactored the verifier to use the shared runner and keep only verifier-specific post-validation/fallback logic
- Added a verifier guard that skips the LLM and uses deterministic verification when the answer draft is already a fallback extractive answer
- Added unit tests for structured generation success, repair, retry, and failure behavior
- Added retry-oriented generator integration coverage
- Updated progress and architecture decision docs

## 4. Files Changed
- app/generation/structured_generation.py
- app/generation/answer_generator.py
- app/generation/verifier.py
- tests/unit/test_structured_generation.py
- tests/unit/test_llm_client.py
- tests/integration/test_query_pipeline.py
- docs/DECISIONS.md
- docs/PROGRESS.md
- docs/review/REVIEW_BUNDLE.md

## 5. Architecture Impact
This change affects the prompting/schema handling layer, answer generator, verifier, and test coverage.
It does not change the data model, retrieval pipeline, evidence bundle contract, or public API schemas.

## 6. Key Implementation Notes
- The shared runner performs only safe cleanup: code-fence stripping, trimming surrounding text, and extracting the first balanced JSON block
- Schema validation still uses the existing Pydantic models
- Answer-specific and verifier-specific fallback paths were preserved
- Domain-specific filtering remains local to the answer/verifier modules, so the new shared layer handles structure, not semantics
- Live API validation showed an important edge case: if answer generation falls back after an LLM timeout, sending that fallback answer back into the LLM verifier can incorrectly turn a usable response into `verification_status="fail"`. The verifier now short-circuits to deterministic verification for fallback answer drafts.

## 7. Risks / Known Issues
- Better schema enforcement should reduce fallback frequency, but it cannot compensate for a weak or timing-out local model
- The runner currently logs failure metadata but does not persist it to the database
- Repair is intentionally conservative and may still reject malformed near-JSON outputs that need human-visible model tuning
- Verifier outputs from the local model can still be schema-valid but low quality or contradictory, which means the user can still see verification failures until the model or verifier policy is improved
- The fail-state frontend message is still misleading in some cases, especially when `verification_status="fail"` is produced without a useful verifier note

## 8. Alignment Check Against MASTER_BRIEF
- source grounding: preserved
- hybrid retrieval: unchanged
- verification layer: preserved
- generic schema: preserved
- inspectability: improved through structured failure metadata and centralized handling

## 9. Testing Performed
- Unit tests for structured-generation runner success, cleanup, retry, and failure cases
- Unit tests for answer generator and verifier retry/fallback behavior
- Integration test for answer generation succeeding after an initial malformed response
- Full automated suite passed: `85 passed in 20.25s`
- Live API validation against a real local server on `127.0.0.1:8002` using:
  `POST /api/projects/86da8892-b3c5-4a15-a174-1f8ff5179d6b/queries`
  with question: `Is there anything that a muslim should not eat?`
- Live API result after the verifier guard fix:
  non-empty `final_answer`, `verification_status="pass_with_warnings"`, and `error=null`

## 10. Example Output / Logs
- Example failure reason: `schema_validation: ...`
- Example failure reason: `llm_error: boom`
- Example repair path: code-fenced JSON parsed successfully after cleanup
- Observed live limitation before the verifier guard fix:
  verifier sometimes returned schema-invalid `supported_claims` items like `{"claim_id":"c1"}` instead of plain strings
- Observed live behavior after the verifier guard fix:
  timed-out answer generation can still produce a deterministic extractive answer, but it now remains visible to the user instead of being converted into a hard verification failure

## 11. Recommended Reviewer Focus
- Whether the shared runner is generic enough without over-generalizing answer/verifier logic
- Whether the cleanup and retry behavior is safe and conservative
- Whether failure metadata is sufficient for debugging future model comparisons
- Whether answer and verifier domain boundaries remain clean
- Whether verifier-fail responses should degrade more gracefully when the local verifier model remains unreliable

## 12. Suggested Next Step
Improve verifier fail-policy and frontend fail messaging, then measure fallback frequency again with the current local model before deciding whether to switch to a stronger schema-following model.
