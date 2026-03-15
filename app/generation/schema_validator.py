"""
Pydantic schemas for Answer Generator and Verifier outputs.
Includes validation of passage IDs and quote texts.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, model_validator


class Claim(BaseModel):
    claim_id: str
    statement: str
    supporting_passage_ids: list[str]
    support_type: Literal["direct", "interpretive"]


class SupportingCitation(BaseModel):
    passage_id: str
    quote: str


class Objection(BaseModel):
    issue: str
    related_passage_ids: list[str]


class AnswerGeneratorOutput(BaseModel):
    final_answer: str
    claims: list[Claim]
    supporting_citations: list[SupportingCitation]
    objections_raised: list[Objection]
    confidence_notes: str

    def validate_passage_ids(self, valid_ids: set[str]) -> list[str]:
        """Return list of passage IDs referenced but not in valid_ids."""
        hallucinated = []
        for claim in self.claims:
            for pid in claim.supporting_passage_ids:
                if pid not in valid_ids:
                    hallucinated.append(pid)
        for citation in self.supporting_citations:
            if citation.passage_id not in valid_ids:
                hallucinated.append(citation.passage_id)
        return list(set(hallucinated))

    def validate_citation_quotes(self, passage_texts: dict[str, str]) -> list[str]:
        """Return list of passage IDs where the quote text is not found in passage text."""
        mismatches = []
        for citation in self.supporting_citations:
            pid = citation.passage_id
            if pid in passage_texts:
                # Allow partial match (quote may be a substring of passage)
                if citation.quote and citation.quote not in passage_texts[pid]:
                    mismatches.append(pid)
        return mismatches


class UnsupportedClaim(BaseModel):
    claim_id: str
    reason: str


class CitationIssue(BaseModel):
    passage_id: str
    issue: str


class VerifierOutput(BaseModel):
    status: Literal["pass", "pass_with_warnings", "fail"]
    supported_claims: list[str]
    unsupported_claims: list[UnsupportedClaim]
    citation_issues: list[CitationIssue]
    notes: str
