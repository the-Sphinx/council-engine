# THE COUNCIL — MASTER BRIEF

This document is the **primary context file** for all development agents working on The Council.

Before implementing anything, agents must read this document.

---

# 1. Project Overview

**The Council** is a source-grounded reasoning system designed to answer questions using only the evidence contained in a set of documents.

Unlike typical RAG systems, The Council emphasizes:

- strict evidence grounding
- structured reasoning
- verification of claims
- transparent citations
- inspectable intermediate steps

Initial MVP corpus:
**Quran (English translation)**

The architecture must remain **generic** so that future datasets may include:

- books
- research papers
- notes
- legal texts
- medical records

---

# 2. Core Pipeline

User Question  
→ Hybrid Retrieval  
→ Evidence Bundle  
→ Grounded Answer Generation  
→ Verification  
→ Final Answer

---

# 3. Core Principles

## Source Grounding
Answers must be derived **only from retrieved evidence**.

## Evidence Transparency
Every meaningful claim must cite passages.

## Verification Layer
Verifier checks:
- claim support
- citation validity
- unsupported claims

## Inspectability
Persist intermediate artifacts:
- lexical retrieval results
- dense retrieval results
- merged candidates
- reranked candidates
- evidence bundle
- answer draft
- verifier report

---

# 4. Retrieval Philosophy

Hybrid retrieval is mandatory:

- lexical retrieval (BM25)
- dense semantic retrieval

Steps:

1. lexical retrieval
2. dense retrieval
3. merge candidates
4. rerank
5. select anchors
6. expand context windows
7. build evidence bundle

Atomic passages are the primary retrieval unit.