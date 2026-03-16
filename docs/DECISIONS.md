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