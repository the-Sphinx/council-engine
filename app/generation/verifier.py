"""
LLMVerifier: validates that answer draft claims are supported by evidence bundle.
"""

from __future__ import annotations

import json

from app.core.interfaces import (
    AnswerDraftDomain,
    CitationIssueDomain,
    EvidenceBundleDomain,
    UnsupportedClaimDomain,
    VerificationReportDomain,
    VerifierInterface,
)
from app.core.logging import get_logger
from app.generation.llm_client import LLMClient
from app.generation.prompts import VERIFIER_SYSTEM, build_verifier_user_prompt
from app.generation.schema_validator import VerifierOutput

logger = get_logger(__name__)


class VerificationError(Exception):
    pass


class LLMVerifier(VerifierInterface):
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def verify(
        self,
        question: str,
        evidence_bundle: EvidenceBundleDomain,
        answer_draft: AnswerDraftDomain,
    ) -> VerificationReportDomain:
        draft_dict = {
            "final_answer": answer_draft.final_answer,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "statement": c.statement,
                    "supporting_passage_ids": c.supporting_passage_ids,
                    "support_type": c.support_type,
                }
                for c in answer_draft.claims
            ],
            "supporting_citations": [
                {"passage_id": c.passage_id, "quote": c.quote}
                for c in answer_draft.supporting_citations
            ],
        }

        user_prompt = build_verifier_user_prompt(question, evidence_bundle, draft_dict)
        raw = self._llm.chat(VERIFIER_SYSTEM, user_prompt)
        output = self._parse(raw)

        if output is None:
            # Retry once
            retry_prompt = (
                user_prompt
                + "\n\nReturn ONLY valid JSON according to the schema, nothing else."
            )
            raw2 = self._llm.chat(VERIFIER_SYSTEM, retry_prompt)
            output = self._parse(raw2)

        if output is None:
            raise VerificationError("Verifier failed to produce valid JSON after retry")

        # Cross-check: unsupported claim_ids must exist in draft
        draft_claim_ids = {c.claim_id for c in answer_draft.claims}
        filtered_unsupported = [
            u for u in output.unsupported_claims if u.claim_id in draft_claim_ids
        ]

        # Cross-check: citation passage_ids must be in bundle
        valid_bundle_ids = {a.passage_id for a in evidence_bundle.anchors}
        filtered_citation_issues = [
            ci for ci in output.citation_issues if ci.passage_id in valid_bundle_ids
        ]

        return VerificationReportDomain(
            status=output.status,
            supported_claims=output.supported_claims,
            unsupported_claims=[
                UnsupportedClaimDomain(claim_id=u.claim_id, reason=u.reason)
                for u in filtered_unsupported
            ],
            citation_issues=[
                CitationIssueDomain(passage_id=ci.passage_id, issue=ci.issue)
                for ci in filtered_citation_issues
            ],
            notes=output.notes,
        )

    def _parse(self, raw: str) -> VerifierOutput | None:
        try:
            data = json.loads(raw)
            return VerifierOutput.model_validate(data)
        except (json.JSONDecodeError, ValueError, Exception) as e:
            logger.warning("Verifier parse error: %s", e)
            return None
