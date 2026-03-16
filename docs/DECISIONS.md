# Architecture Decisions

This file records important design decisions.

---

## Hybrid Retrieval

Decision:
Use lexical + dense retrieval.

Reason:
Dense-only retrieval misses exact textual matches.
Lexical-only retrieval misses semantic similarity.

---

## Atomic Passage Units

Decision:
Use small atomic passages.

Reason:
Enables precise citations and reliable verification.

---

## Verification Layer

Decision:
Always verify answers.

Reason:
Prompt-only grounding is unreliable.

---

## Generic Schema

Decision:
Core architecture must remain domain-agnostic.

Reason:
Future corpora may include books, papers, or medical records.

---

## Persist Retrieval Artifacts

Decision:
Store retrieval debug artifacts for every query.

Reason:
Enables debugging and evaluation.

---

## Structured Generation Enforcement

Decision:
Centralize JSON cleanup, parsing, validation, and retry behavior in a shared structured-generation layer before answer/verifier domain conversion.

Reason:
Improves schema compliance and inspectability without collapsing the answer generator and verifier into one generic pipeline.
