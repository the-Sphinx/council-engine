# Prompt + Output Schema Specification
## For the MVP Source-Grounded Interpretation App (V1)

**Purpose:**  
Define the **prompt structure**, **output schemas**, and **validation contracts** for the **Grounded Answer Generator** and **Verifier Agent** used in the MVP system.

This document ensures:
- answers remain **source-grounded**
- structured outputs are **machine-parseable**
- verifier logic can **systematically validate claims**
- later **multi-agent expansion** can plug into the same schema

This spec assumes the system described in:
- `mvp_core_architecture_spec.md`
- `retrieval_evaluation_design_spec.md`

The prompt and output schema must be **strictly enforced**.  
Loose natural-language responses are **not acceptable**.

---

# 1. Design Goals

## 1.1 Strict Source Grounding
The model must only use passages provided in the **Evidence Bundle**.

## 1.2 Structured Machine-Readable Output
Outputs must always follow a **JSON schema**.

## 1.3 Separation of Responsibilities
Two different agents exist:

1. **Answer Generator**
   - interprets evidence
   - produces grounded answer
   - proposes claims and citations
   - raises possible objections

2. **Verifier**
   - checks claim validity
   - validates citations
   - flags unsupported statements

## 1.4 Future Multi-Agent Compatibility
Later versions will add multiple agents.  
The schema must allow answers to be compared across agents.

---

# 2. Evidence Bundle Input Format

The Answer Generator receives evidence in structured format.

Example:

```json
{
  "query": "What does the text say about fasting?",
  "mode": "source_only",
  "anchors": [
    {
      "passage_id": "p102",
      "text": "...",
      "section_title": "Surah X",
      "rank": 1,
      "window_text": "... expanded context ..."
    }
  ]
}
```

Important rules:

- **anchors** are the primary passages
- **window_text** is context only
- citations must reference **passage_id**

---

# 3. Answer Generator Prompt

## 3.1 System Prompt

The system prompt must clearly enforce grounding.

Example:

```
You are an evidence-based text analyst.

You must answer questions ONLY using the evidence passages provided.

Rules:
1. Do NOT use outside knowledge.
2. Do NOT invent supporting information.
3. Every substantive claim must cite one or more passage IDs.
4. If evidence is insufficient, say so.
5. Distinguish between:
   - direct textual support
   - interpretation
6. Preserve ambiguity where the text is unclear.
7. Your response MUST follow the JSON schema exactly.
```

---

## 3.2 User Prompt Template

```
Question:
{question}

Mode:
source_only

Evidence Passages:
{evidence_bundle_json}

Instructions:
Answer using ONLY the provided passages.
Cite passages using passage_id.
Return structured JSON according to the schema.
```

---

# 4. Answer Generator Output Schema

The answer generator must return:

```json
{
  "final_answer": "string",
  "claims": [
    {
      "claim_id": "c1",
      "statement": "string",
      "supporting_passage_ids": ["p102", "p105"],
      "support_type": "direct | interpretive"
    }
  ],
  "supporting_citations": [
    {
      "passage_id": "p102",
      "quote": "short excerpt"
    }
  ],
  "objections_raised": [
    {
      "issue": "string",
      "related_passage_ids": ["p110"]
    }
  ],
  "confidence_notes": "string"
}
```

---

# 5. Output Field Explanation

## 5.1 final_answer
Human-readable answer summarizing supported conclusions.

Constraints:
- must not introduce new claims not in `claims`
- must remain faithful to cited passages

---

## 5.2 claims
Atomic reasoning statements.

Example:

```
"The text associates fasting with spiritual discipline."
```

Each claim must list supporting passages.

---

## 5.3 support_type

Possible values:

| Type | Meaning |
|-----|------|
| direct | Explicitly stated in passage |
| interpretive | Inferred by connecting multiple passages |

Interpretive claims must still reference passages.

---

## 5.4 supporting_citations

Small excerpts from passages used to justify claims.

Important rules:

- must correspond to `passage_id`
- must appear within stored source text
- verifier checks them

---

## 5.5 objections_raised

Possible weaknesses or ambiguities.

Examples:

- interpretation ambiguity
- conflicting passages
- weak evidence coverage

This helps the later **Skeptic Agent** extension.

---

## 5.6 confidence_notes

Free-text explanation of uncertainty.

Example:

```
"The passages discuss fasting but do not explicitly define its full ritual rules."
```

---

# 6. Verifier Prompt

## 6.1 Verifier Role

The verifier performs **independent validation**.

It must check:

1. claims supported by passages
2. citations valid
3. unsupported claims
4. interpretation overreach

---

## 6.2 Verifier System Prompt

```
You are an evidence verification agent.

Your job is to check whether an answer is fully supported by the provided evidence passages.

Rules:
1. Validate each claim against the cited passages.
2. Detect unsupported claims.
3. Confirm citation accuracy.
4. Flag interpretations that go beyond the text.
5. Return a structured verification report.
```

---

# 7. Verifier Input Format

```json
{
  "question": "...",
  "evidence_bundle": {...},
  "answer_draft": {...}
}
```

---

# 8. Verifier Output Schema

```json
{
  "status": "pass | pass_with_warnings | fail",
  "supported_claims": ["c1", "c2"],
  "unsupported_claims": [
    {
      "claim_id": "c3",
      "reason": "no supporting passage"
    }
  ],
  "citation_issues": [
    {
      "passage_id": "p201",
      "issue": "quote not found"
    }
  ],
  "notes": "string"
}
```

---

# 9. Verification Rules

Verifier must:

1. Compare each claim with referenced passages
2. Confirm passage text contains support
3. Check citations reference valid passages
4. Flag hallucinated or unsupported statements

---

# 10. Final Response Builder

After verification, the system produces the user response.

Logic:

```
if status == pass:
    return answer
elif status == pass_with_warnings:
    return answer + warnings
elif status == fail:
    regenerate once OR return failure message
```

---

# 11. Example End-to-End Output

Example user response:

```
Answer:
The text describes fasting as an act associated with discipline and devotion.

Citations:
- Surah X, Passage p102
- Surah Y, Passage p115

Objections Raised:
- The passages mention fasting but do not fully define the ritual rules.
```

---

# 12. Schema Validation

Before accepting model output:

1. Parse JSON
2. Validate required fields
3. Confirm passage_ids exist
4. Confirm citations map to stored text

If validation fails:
- retry generation once

---

# 13. Critical Implementation Warnings

## 13.1 Never Trust Freeform LLM Output
Always enforce schema parsing.

## 13.2 Do Not Let the Model Invent Passage IDs
Passage IDs must exist in DB.

## 13.3 Do Not Skip Verifier
Verifier is mandatory for grounding integrity.

## 13.4 Do Not Accept Claims Without Citations
Every claim must reference evidence.

---

# 14. Implementation Order

1. Implement answer schema validation
2. Implement answer generator prompt
3. Implement verifier prompt
4. Implement verification pipeline
5. Integrate with retrieval system

---

# 15. Definition of Done

Prompt + Output Schema module is complete when:

- Answer generator returns structured JSON
- Verifier validates claims and citations
- System rejects unsupported answers
- Final response shows answer + citations + objections

---

# 16. Next Phase

After implementing this module, the next design artifact should be:

**Multi-Agent Board Orchestration Spec**

This will introduce:

- Analyst Agent
- Skeptic Agent
- Verifier Agent
- Moderator Agent

using the same claim and citation schema.
