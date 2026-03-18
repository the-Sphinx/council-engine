# Review Bundle Creation Spec
## For The Council Development Workflow

**Purpose:**  
This document defines the expected structure and content of a `REVIEW_BUNDLE.md` file that a coding agent should generate and commit after each meaningful development task.

The review bundle is intended for:
- architecture review
- debugging support
- retrieval/grounding analysis
- progress tracking
- fast handoff into ChatGPT for code and design review

This file should be generated in a **consistent format** every time so that it is easy to review.

---

# 1. File Name and Location

Recommended file name:

```text
REVIEW_BUNDLE.md
```

Recommended repo location:

```text
docs/review/REVIEW_BUNDLE.md
```

Optional historical snapshots:

```text
docs/review/history/
```

If keeping a rolling history, recommended naming:

```text
review_bundle_YYYY-MM-DD_HH-MM.md
```

For normal use, keep one current bundle at:

```text
docs/review/REVIEW_BUNDLE.md
```

and overwrite it after each task.

---

# 2. When to Generate It

Generate and commit a fresh review bundle after any of the following:

- a completed coding task
- a meaningful architecture change
- a retrieval logic change
- a schema change
- a verifier change
- a bugfix affecting grounding/retrieval
- an evaluation run worth reviewing

Do **not** generate it for trivial formatting-only changes unless explicitly requested.

---

# 3. Primary Goals of the Review Bundle

The review bundle must help an external reviewer quickly understand:

1. what changed
2. why it changed
3. what files were affected
4. what architectural decisions were made
5. whether core project principles were preserved
6. what still appears broken or risky
7. what should be reviewed next

The bundle should be **compact but complete**.

---

# 4. Required Structure

The file must contain the following sections in this order.

---

# 5. Required Template

Use this exact template structure.

```md
# REVIEW BUNDLE

## 1. Task Summary
- Task name:
- Date:
- Time:
- Branch:
- Commit hash:
- Agent:
- Status: completed / partial / blocked

## 2. Objective
Briefly describe the intended task outcome.

## 3. What Changed
List the key implemented changes.

## 4. Files Changed
- path/to/file1
- path/to/file2

## 5. Architecture Impact
Explain whether the change affects:
- data model
- retrieval pipeline
- evidence bundle
- prompting/schema
- verifier
- evaluation
- API/UI

## 6. Key Implementation Notes
Explain important design decisions and tradeoffs.

## 7. Risks / Known Issues
List any problems, uncertainties, shortcuts, or technical debt.

## 8. Alignment Check Against MASTER_BRIEF
State whether the implementation preserves:
- source grounding
- hybrid retrieval
- verification layer
- generic schema
- inspectability

## 9. Testing Performed
List tests run and their results.

## 10. Example Output / Logs
Provide relevant snippets:
- retrieval output
- verifier output
- schema output
- error logs
- evaluation metrics

## 11. Recommended Reviewer Focus
List what ChatGPT should inspect carefully.

## 12. Suggested Next Step
Recommend the next implementation task.
```

---

# 6. Detailed Section Guidance

## 6.1 Task Summary
Must include:
- task name
- date/time
- branch
- commit hash
- agent/tool used
- completion status

Example:

```md
## 1. Task Summary
- Task name: Implement BM25 lexical retriever
- Date: 2026-03-16 14:20 UTC
- Branch: feature/lexical-retrieval
- Commit hash: abc1234
- Agent: Codex
- Status: completed
```

---

## 6.2 Objective
A short paragraph describing the intended outcome.

Good example:

```md
## 2. Objective
Implement lexical retrieval over atomic passages using BM25 so the system can retrieve exact term matches and return passage IDs for downstream hybrid merging.
```

Bad example:
- “worked on retrieval”
- “fixed stuff”

Be precise.

---

## 6.3 What Changed
Summarize the implementation in bullets.

Good example:

```md
## 3. What Changed
- Added BM25 index builder for Passage records
- Implemented lexical search function returning passage_id and score
- Added retriever interface adapter
- Added unit tests for basic search behavior
- Added retrieval debug persistence for lexical results
```

This section should be outcome-focused, not code-dump-heavy.

---

## 6.4 Files Changed
List the important files, ideally grouped by purpose.

Example:

```md
## 4. Files Changed
- app/retrieval/lexical.py
- app/ingestion/indexer.py
- app/schemas/domain.py
- tests/unit/test_lexical_retrieval.py
```

If many files changed, list the important ones first and summarize the rest.

---

## 6.5 Architecture Impact
This is one of the most important sections.

The coding agent must explicitly say whether the change affects any of the following:

- data model
- retrieval pipeline
- evidence bundle
- answer generator
- verifier
- evaluation
- API
- UI
- configuration

Example:

```md
## 5. Architecture Impact
This change affects the retrieval pipeline and debug artifact persistence.
It does not change the data model, answer schema, or verifier behavior.
```

This helps prevent hidden architecture drift.

---

## 6.6 Key Implementation Notes
This section should explain:
- important design choices
- alternatives considered
- constraints encountered
- shortcuts taken
- why specific implementation choices were made

Example:

```md
## 6. Key Implementation Notes
- Used a simple BM25 library for the first version to reduce implementation complexity.
- Indexed normalized passage text but preserved raw passage text for citation mapping.
- Stored lexical scores in retrieval result objects to support later hybrid fusion.
```

This section is important because it captures intent, not just output.

---

## 6.7 Risks / Known Issues
Be honest and explicit.

This section should include:
- incomplete work
- possible bugs
- technical debt
- weak tests
- design uncertainty
- shortcuts that may need later revision

Example:

```md
## 7. Risks / Known Issues
- BM25 tokenizer is basic and may not handle punctuation optimally.
- Retrieval currently runs in-memory and may need persistence changes later.
- Search ranking has not yet been evaluated against benchmark questions.
```

Never hide issues.

---

## 6.8 Alignment Check Against MASTER_BRIEF
The coding agent must explicitly verify whether the implementation still respects the project’s core rules.

Required checklist:

- source grounding preserved?
- hybrid retrieval preserved?
- verifier layer preserved?
- generic schema preserved?
- inspectability preserved?

Example:

```md
## 8. Alignment Check Against MASTER_BRIEF
- Source grounding preserved: yes
- Hybrid retrieval preserved: yes
- Verifier layer preserved: yes
- Generic schema preserved: yes
- Inspectability preserved: yes
```

If any answer is “no” or “partially,” explain why.

This section is mandatory.

---

## 6.9 Testing Performed
Summarize:
- unit tests
- integration tests
- manual tests
- evaluation runs
- untested areas

Example:

```md
## 9. Testing Performed
- Ran unit tests for BM25 index creation: passed
- Ran lexical retrieval smoke test on 5 sample queries: passed
- Did not yet run benchmark evaluation set
```

Do not claim tests were done if they were not.

---

## 6.10 Example Output / Logs
This section is critical for remote review.

Include short, focused artifacts such as:
- example retrieval result
- example answer JSON
- example verifier report
- stack trace
- evaluation metric table
- relevant logs

Examples:

```md
## 10. Example Output / Logs

### Example lexical retrieval result
- query: "What does the text say about fasting?"
- top result: passage_id=p102 score=8.42

### Example saved retrieval debug JSON
{
  "top_lexical_ids": ["p102", "p110", "p204"]
}
```

Keep it concise. Do not paste giant logs unless necessary.

---

## 6.11 Recommended Reviewer Focus
This section tells ChatGPT what to examine.

Examples:
- “Check whether lexical retriever output structure is future-proof for hybrid merge.”
- “Check whether passage tokenization may break citation mapping.”
- “Review whether the in-memory index approach risks architecture drift.”

This makes reviews more effective.

---

## 6.12 Suggested Next Step
The coding agent should recommend the next smallest sensible task.

Examples:
- implement dense retrieval interface
- add hybrid candidate merging
- add reranker config support
- add retrieval evaluation runner

This improves continuity between iterations.

---

# 7. Optional Sections

The following are useful but optional.

## 7.1 Diff Summary
A short human-readable description of the main code diff.

## 7.2 Config Snapshot
Useful when retrieval parameters changed.

Example:

```md
## Config Snapshot
- top_k_lexical: 30
- top_k_dense: 30
- context_window_radius: 1
```

## 7.3 Evaluation Snapshot
Useful after retrieval or verifier changes.

Example:

```md
## Evaluation Snapshot
- Hit@5: 0.72
- Hit@10: 0.86
- Recall@10: 0.68
```

---

# 8. Quality Requirements

The review bundle must be:

- concise
- honest
- architecture-aware
- implementation-aware
- review-friendly
- consistent in format

Avoid:
- vague summaries
- giant code dumps
- hiding known issues
- marketing-style language

This is an engineering artifact, not a presentation.

---

# 9. Suggested Prompt for the Coding Agent

Use a prompt like this when asking the coding agent to generate the bundle:

```text
Create or update docs/review/REVIEW_BUNDLE.md using the Review Bundle Creation Spec.

Requirements:
- Follow the required section order exactly.
- Be honest about incomplete work and risks.
- Include architecture impact.
- Include alignment check against MASTER_BRIEF.md.
- Include short example outputs or logs when relevant.
- Keep it concise but informative.
- Then commit the updated REVIEW_BUNDLE.md with the task changes.
```

---

# 10. Recommended Git Workflow

Recommended pattern after each meaningful task:

1. implement task
2. update PROGRESS.md if needed
3. update DECISIONS.md if needed
4. create/update REVIEW_BUNDLE.md
5. commit code + review bundle together
6. push repo

This makes the review bundle a reliable snapshot of the task state.

---

# 11. Recommended Repo Structure

```text
the-council/
├── MASTER_BRIEF.md
├── DECISIONS.md
├── PROGRESS.md
├── TASK_TEMPLATE.md
├── docs/
│   ├── review/
│   │   └── REVIEW_BUNDLE.md
│   └── specs/
│       ├── mvp_core_architecture_spec.md
│       ├── retrieval_evaluation_design_spec.md
│       └── prompt_output_schema_spec.md
├── app/
└── tests/
```

---

# 12. Definition of Done

A review bundle is considered acceptable when it:

- uses the required structure
- clearly explains the task and changes
- lists changed files
- describes architecture impact
- lists risks and known issues
- includes the alignment check
- includes testing notes
- includes useful output/log snippets
- recommends reviewer focus
- suggests the next step

If these are missing, the bundle is incomplete.

---

# 13. Final Recommendation

Treat `REVIEW_BUNDLE.md` as a **communication layer** between:
- coding agent
- repository history
- ChatGPT reviewer

It should function as a compact engineering handoff after every meaningful development step.
