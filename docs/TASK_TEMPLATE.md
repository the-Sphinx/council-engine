# Task Template for Coding Agents

Use this template when assigning tasks to coding agents like Codex.

---

## Context

Before implementing anything read the following documents that are stored under the `docs/` directory:

MASTER_BRIEF.md  
DECISIONS.md  
PROGRESS.md  

Do not violate rules in MASTER_BRIEF.md.

---

## Task

Describe the specific implementation task.

Example:
Implement BM25 lexical retrieval over Passage table.

---

## Constraints

- Must support passage_id references
- Must remain compatible with hybrid retrieval pipeline
- Must not break schema assumptions

---

## Deliverables

The coding agent should produce:

- code changes
- modified files
- explanation of implementation decisions

---

## Self‑Check

The agent must confirm:

- hybrid retrieval remains intact
- grounding rules are preserved
- schema compatibility is maintained