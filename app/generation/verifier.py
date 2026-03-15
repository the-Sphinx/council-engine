"""
LLMVerifier: validates that answer draft claims are supported by evidence bundle.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

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


@dataclass
class ParseAttempt:
    output: VerifierOutput | None
    should_retry: bool


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
        try:
            raw = self._llm.chat(VERIFIER_SYSTEM, user_prompt)
        except Exception as exc:
            logger.warning("Verifier request failed, using fallback: %s", exc)
            return self._build_fallback_report(evidence_bundle, answer_draft)
        attempt = self._parse(raw)
        output = attempt.output

        if output is None and attempt.should_retry:
            # Retry once
            retry_prompt = (
                user_prompt
                + "\n\nReturn ONLY valid JSON according to the schema, nothing else."
            )
            try:
                raw2 = self._llm.chat(VERIFIER_SYSTEM, retry_prompt)
            except Exception as exc:
                logger.warning("Verifier retry failed, using fallback: %s", exc)
                return self._build_fallback_report(evidence_bundle, answer_draft)
            output = self._parse(raw2).output

        if output is None:
            logger.warning(
                "Falling back to deterministic verification for query %r",
                question[:120],
            )
            return self._build_fallback_report(evidence_bundle, answer_draft)

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

    def _parse(self, raw: str) -> ParseAttempt:
        try:
            data = json.loads(raw)
            return ParseAttempt(output=VerifierOutput.model_validate(data), should_retry=False)
        except json.JSONDecodeError as e:
            logger.warning("Verifier parse error: %s", e)
            return ParseAttempt(output=None, should_retry=True)
        except Exception as e:
            logger.warning("Verifier parse error: %s", e)
            return ParseAttempt(output=None, should_retry=False)

    def _build_fallback_report(
        self,
        evidence_bundle: EvidenceBundleDomain,
        answer_draft: AnswerDraftDomain,
    ) -> VerificationReportDomain:
        anchor_map = {anchor.passage_id: anchor.text for anchor in evidence_bundle.anchors}
        supported_claims = []
        unsupported_claims = []

        for claim in answer_draft.claims:
            if claim.supporting_passage_ids and all(pid in anchor_map for pid in claim.supporting_passage_ids):
                supported_claims.append(claim.claim_id)
            else:
                unsupported_claims.append(
                    UnsupportedClaimDomain(
                        claim_id=claim.claim_id,
                        reason="Fallback verification could not match all supporting passage IDs.",
                    )
                )

        citation_issues = []
        for citation in answer_draft.supporting_citations:
            passage_text = anchor_map.get(citation.passage_id)
            if not passage_text:
                citation_issues.append(
                    CitationIssueDomain(
                        passage_id=citation.passage_id,
                        issue="Citation passage was not present in the evidence bundle.",
                    )
                )
            elif citation.quote and citation.quote not in passage_text:
                citation_issues.append(
                    CitationIssueDomain(
                        passage_id=citation.passage_id,
                        issue="Citation quote was not found verbatim in the anchor passage.",
                    )
                )

        status = "pass_with_warnings"
        if unsupported_claims:
            status = "fail"

        return VerificationReportDomain(
            status=status,
            supported_claims=supported_claims,
            unsupported_claims=unsupported_claims,
            citation_issues=citation_issues,
            notes=(
                "Fallback verification used deterministic passage/citation checks because the "
                "local model did not return the required schema."
            ),
        )
