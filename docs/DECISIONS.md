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

---

## Default Local Model

Decision:
Use `qwen2.5:7b` as the default local Ollama model instead of `llama3.1:8b`.

Reason:
Local evaluation over 10 Quran questions showed materially better behavior: fallback rate dropped from 90% to 50%, and full structured answer+verifier schema success improved from 10% to 40%.

---

## Retrieval Eval Diagnostics

Decision:
Store per-query retrieval debug artifacts during eval runs, including lexical, dense, merged, and reranked passage IDs plus simple failure classification.

Reason:
Makes retrieval misses inspectable and turns evaluation into a practical tuning loop instead of a single aggregate score.

---

## Lexical Query Processing

Decision:
Use lightweight lexical query normalization plus a small configurable query-expansion map for BM25, and expose the expanded query state in retrieval debug output.

Reason:
Improves recall on paraphrase-heavy questions while keeping retrieval behavior explainable, inspectable, and easy to disable if an expansion set becomes too broad.

---

## Hybrid Retrieval Defaults

Decision:
Keep balanced hybrid defaults (`alpha=0.5`, `beta=0.5`) and treat reranking and overlap boost as experiment knobs rather than assumed improvements.

Reason:
On the current 10-question Quran benchmark, lexical-heavy weighting reduced `hit@5`, while balanced-with-rerank, balanced-no-rerank, and balanced-with-overlap-boost all produced the same `hit@10`. The system now measures these knobs explicitly, but the benchmark does not yet justify changing the default retrieval mix.
