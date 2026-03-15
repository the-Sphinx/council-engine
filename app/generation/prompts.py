"""
System and user prompt templates for the Answer Generator and Verifier.
"""

from __future__ import annotations

import json

from app.core.interfaces import EvidenceBundleDomain


ANSWER_GENERATOR_SYSTEM = """\
You are an evidence-based text analyst.

You must answer questions ONLY using the evidence passages provided.

Rules:
1. Do NOT use outside knowledge.
2. Do NOT invent supporting information.
3. Every substantive claim must cite one or more passage IDs.
4. If evidence is insufficient, say so explicitly.
5. Distinguish between:
   - direct textual support (support_type: "direct")
   - interpretation / inference (support_type: "interpretive")
6. Preserve ambiguity where the text is unclear.
7. Your response MUST follow the JSON schema exactly. Return ONLY valid JSON.

Output schema:
{
  "final_answer": "string",
  "claims": [
    {
      "claim_id": "c1",
      "statement": "string",
      "supporting_passage_ids": ["pid1"],
      "support_type": "direct | interpretive"
    }
  ],
  "supporting_citations": [
    {
      "passage_id": "pid1",
      "quote": "short excerpt from passage"
    }
  ],
  "objections_raised": [
    {
      "issue": "string",
      "related_passage_ids": ["pid1"]
    }
  ],
  "confidence_notes": "string"
}"""


VERIFIER_SYSTEM = """\
You are an evidence verification agent.

Your job is to check whether an answer is fully supported by the provided evidence passages.

Rules:
1. Validate each claim against the cited passages.
2. Detect unsupported claims — claims with no cited passage or where the cited passage does not support the claim.
3. Confirm citation accuracy — check that quoted text actually appears in the cited passage.
4. Flag interpretations that go significantly beyond the text.
5. Return a structured verification report. Return ONLY valid JSON.

Output schema:
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
      "passage_id": "pid1",
      "issue": "quote not found in passage text"
    }
  ],
  "notes": "string"
}"""


def build_answer_user_prompt(question: str, evidence_bundle: EvidenceBundleDomain) -> str:
    anchors_data = []
    for anchor in evidence_bundle.anchors:
        anchors_data.append({
            "passage_id": anchor.passage_id,
            "text": anchor.text,
            "section_title": anchor.section_title or "",
            "rank": anchor.rank,
            "window_text": anchor.window_text,
        })

    bundle_json = json.dumps({
        "query": question,
        "mode": "source_only",
        "anchors": anchors_data,
    }, indent=2, ensure_ascii=False)

    return f"""Question:
{question}

Mode:
source_only

Evidence Passages:
{bundle_json}

Instructions:
Answer using ONLY the provided passages.
Cite passages using passage_id.
Return structured JSON according to the schema.
Return ONLY valid JSON, no other text."""


def build_verifier_user_prompt(
    question: str,
    evidence_bundle: EvidenceBundleDomain,
    answer_draft_dict: dict,
) -> str:
    anchors_data = []
    for anchor in evidence_bundle.anchors:
        anchors_data.append({
            "passage_id": anchor.passage_id,
            "text": anchor.text,
            "section_title": anchor.section_title or "",
        })

    bundle_json = json.dumps({
        "query": question,
        "mode": "source_only",
        "anchors": anchors_data,
    }, indent=2, ensure_ascii=False)

    draft_json = json.dumps(answer_draft_dict, indent=2, ensure_ascii=False)

    return f"""Question:
{question}

Evidence Passages:
{bundle_json}

Answer Draft to Verify:
{draft_json}

Instructions:
Verify whether every claim in the answer draft is supported by the cited evidence passages.
Return structured JSON according to the schema.
Return ONLY valid JSON, no other text."""
