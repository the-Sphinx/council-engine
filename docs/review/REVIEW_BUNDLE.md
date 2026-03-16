# REVIEW BUNDLE

## 1. Task Summary
- Task name: Structured generation enforcement layer
- Date: 2026-03-16
- Branch: main
- Commit hash: uncommitted
- Agent: Codex
- Status: completed

## 2. Objective
Implement a shared structured-generation layer so answer generation and verification both use the same JSON cleanup, parsing, validation, retry, and failure-reporting flow before falling back.

## 3. What Changed
- Added a shared structured-generation runner with retry, safe JSON cleanup, and structured failure metadata
- Refactored the answer generator to use the shared runner and keep only answer-specific post-validation/fallback logic
- Refactored the verifier to use the shared runner and keep only verifier-specific post-validation/fallback logic
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

## 5. Architecture Impact
This change affects the prompting/schema handling layer, answer generator, verifier, and test coverage.
It does not change the data model, retrieval pipeline, evidence bundle contract, or public API schemas.

## 6. Key Implementation Notes
- The shared runner performs only safe cleanup: code-fence stripping, trimming surrounding text, and extracting the first balanced JSON block
- Schema validation still uses the existing Pydantic models
- Answer-specific and verifier-specific fallback paths were preserved
- Domain-specific filtering remains local to the answer/verifier modules, so the new shared layer handles structure, not semantics

## 7. Risks / Known Issues
- Better schema enforcement should reduce fallback frequency, but it cannot compensate for a weak or timing-out local model
- The runner currently logs failure metadata but does not persist it to the database
- Repair is intentionally conservative and may still reject malformed near-JSON outputs that need human-visible model tuning

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
- Full automated suite to be run after implementation

## 10. Example Output / Logs
- Example failure reason: `schema_validation: ...`
- Example failure reason: `llm_error: boom`
- Example repair path: code-fenced JSON parsed successfully after cleanup

## 11. Recommended Reviewer Focus
- Whether the shared runner is generic enough without over-generalizing answer/verifier logic
- Whether the cleanup and retry behavior is safe and conservative
- Whether failure metadata is sufficient for debugging future model comparisons
- Whether answer and verifier domain boundaries remain clean

## 12. Suggested Next Step
Measure fallback frequency with the current local model after this refactor, then either tune prompts further or switch to a stronger schema-following local model.
