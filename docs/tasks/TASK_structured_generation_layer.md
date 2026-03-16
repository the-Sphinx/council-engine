# TASK — Structured Generation Enforcement Layer

## Context

Before implementing anything read the following documents that are stored under the `docs/` directory:

- `MASTER_BRIEF.md`
- `DECISIONS.md`
- `PROGRESS.md`

Do not violate the rules in `MASTER_BRIEF.md`.

This task is based on the current repo state where:

- retrieval/indexing are operational,
- answer generation and verification exist,
- but the local LLM often fails to return the required JSON schema,
- causing frequent fallback behavior.

Relevant existing files likely include:

- `app/generation/answer_generator.py`
- `app/generation/verifier.py`
- `app/generation/schema_validator.py`
- `app/generation/llm_client.py`
- `app/core/interfaces.py`

---

## Task

Implement a **robust structured generation enforcement layer** that sits between the LLM client and the answer/verifier pipeline.

The goal is to make answer generation and verifier generation more reliably schema-compliant before we decide whether to swap the model.

This layer should:

1. centralize JSON parsing and validation logic
2. centralize retry behavior
3. support optional JSON repair for near-valid outputs
4. support validator-driven structured output handling
5. reduce duplicated schema-handling code in:
   - `answer_generator.py`
   - `verifier.py`

---

## Why This Task Matters

The current `PROGRESS.md` says the main blocker is that local LLM answer generation and verification are not reliably schema-compliant.

Right now:

- the answer generator retries once, then falls back
- the verifier retries once, then falls back
- parsing/validation logic is duplicated across both paths

We want a reusable enforcement module so that:

- schema compliance improves
- fallback frequency drops
- answer quality becomes more stable
- future model comparisons become easier
- answer/verifier logic becomes cleaner

---

## Requirements

### 1. Create a reusable module

Create a reusable module, for example:

```text
app/generation/structured_generation.py
```

or another clearly named equivalent.

It should expose a reusable function or class, something like:

```python
generate_structured_output(...)
```

or

```python
StructuredGenerationRunner(...)
```

---

### 2. The structured generation layer must support:

#### A. LLM call
- call the configured LLM client

#### B. JSON parse
- attempt `json.loads`

#### C. Pydantic validation
- validate parsed output against a provided Pydantic model

#### D. Retry behavior
- if parse fails or validation fails, retry with a correction prompt
- support configurable max retries
- recommended default: 2 or 3 total attempts

#### E. Optional repair attempt
If output is almost valid:
- try a lightweight repair step before giving up

Examples of acceptable repair behavior:
- trim surrounding markdown/code fences
- extract first valid JSON object if surrounded by extra text
- strip leading/trailing non-JSON noise

Do **not** implement unsafe guess-heavy repair that silently changes semantic content.

#### F. Return structured result
The module should return:
- parsed validated object on success
- structured failure information on failure

Do not return ambiguous mixed outputs.

---

### 3. Refactor answer generator to use it

Refactor:

```text
app/generation/answer_generator.py
```

so that it no longer owns all parsing/retry logic internally.

The answer generator should:
- build prompt
- call the structured generation layer
- apply answer-specific post-validation checks
- fall back only if structured generation ultimately fails

Keep answer-specific domain conversion logic in the answer generator.

---

### 4. Refactor verifier to use it

Refactor:

```text
app/generation/verifier.py
```

in the same way.

The verifier should:
- build prompt
- call structured generation layer
- apply verifier-specific post-checks
- fall back only if structured generation ultimately fails

Keep verifier-specific domain conversion logic in the verifier.

---

### 5. Preserve current architecture

Do **not** replace the current architecture with one giant generic pipeline.

Keep:

- Pydantic schemas for LLM output validation
- dataclass domain objects in the core
- answer-specific fallback path
- verifier-specific fallback path

The new module should reduce duplication, not erase role boundaries.

---

### 6. Add explicit failure metadata

The structured generation layer should expose enough failure detail for debugging, such as:

- parse failure
- validation failure
- retry count
- repair attempted or not
- final failure reason

This can be logged and optionally persisted later.

Do not hide why generation failed.

---

## Constraints

- Must remain compatible with current Pydantic schema models
- Must not remove fallback behavior
- Must not weaken source grounding rules
- Must not couple implementation to one provider
- Must not hardcode Quran-specific logic
- Must preserve inspectability
- Must not silently coerce semantically invalid outputs into “valid” ones

---

## Deliverables

The coding agent should produce:

1. the new structured generation module
2. refactored `answer_generator.py`
3. refactored `verifier.py`
4. tests for the structured generation layer
5. updated `PROGRESS.md`
6. updated `REVIEW_BUNDLE.md`

If a meaningful architectural decision is made, also update:

- `DECISIONS.md`

---

## Testing Requirements

Add tests covering at minimum:

### Success cases
- valid JSON returned immediately
- valid JSON returned after retry
- valid JSON returned after harmless cleanup

### Failure cases
- invalid JSON
- wrong schema shape
- hallucinated fields or missing required fields
- retry exhausted
- fallback path still works correctly

### Integration-oriented behavior
- answer generator still returns fallback answer if schema compliance fails
- verifier still returns fallback verification if schema compliance fails

Be honest in `REVIEW_BUNDLE.md` about anything not fully tested.

---

## Suggested Design Direction

A good implementation may look like:

### Structured generation result type
A small result object such as:

```python
StructuredGenerationResult(
    success: bool,
    parsed: Optional[BaseModel],
    raw_outputs: list[str],
    attempts: int,
    failure_reason: Optional[str],
)
```

### Reusable function/class
Something like:

```python
run_structured_generation(
    llm_client,
    system_prompt,
    user_prompt,
    output_model,
    max_attempts=3,
)
```

### Correction strategy
If initial output fails:
- retry with explicit message:
  - return only valid JSON
  - follow the exact schema
  - no markdown
  - no explanation
- optionally include schema summary again

---

## Anti-Patterns To Avoid

Do not do these:

### 1. Do not bury retry logic separately in both generators again
The whole point is to centralize it.

### 2. Do not implement brittle regex-only “JSON parsing”
Use real JSON parsing, with only minimal cleanup around the edges.

### 3. Do not silently discard semantically important fields
Schema correctness matters.

### 4. Do not over-engineer for future agents yet
This task is for answer generator + verifier reliability only.

### 5. Do not remove current deterministic fallback paths
They are still necessary.

---

## Reviewer Focus

In the review bundle, ask ChatGPT to inspect:

1. whether the structured generation layer is generic enough but not over-generalized
2. whether retry/repair logic is safe
3. whether answer/verifier boundaries remain clean
4. whether schema failures are now easier to debug
5. whether the architecture still aligns with `MASTER_BRIEF.md`

---

## Suggested Next Step After This Task

After this task is complete and reviewed, the likely next step will be:

- switch the local model to a stronger schema-following model (for example Qwen 2.5 family)
- then measure fallback frequency and answer quality again

Do **not** change the model inside this task unless absolutely required for testing.

---

## Definition of Done

This task is complete when:

1. answer generation and verifier generation use a shared structured-generation layer
2. parsing/validation/retry logic is no longer duplicated
3. schema failures are logged with clear reasons
4. fallback paths still work
5. tests cover success + failure behavior
6. `PROGRESS.md` and `REVIEW_BUNDLE.md` are updated
