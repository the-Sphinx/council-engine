"""
LLMVerifier: validates that answer draft claims are supported by evidence bundle.
"""

from __future__ import annotations

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
from app.generation.structured_generation import StructuredGenerationRunner

logger = get_logger(__name__)


class VerificationError(Exception):
    pass


class LLMVerifier(VerifierInterface):
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client
        self._runner = StructuredGenerationRunner(llm_client)
        self.last_run_info: dict | None = None

    def verify(
        self,
        question: str,
        evidence_bundle: EvidenceBundleDomain,
        answer_draft: AnswerDraftDomain,
    ) -> VerificationReportDomain:
        if self._should_use_deterministic_verification(answer_draft):
            self.last_run_info = {
                "mode": "deterministic_skip",
                "attempts": 0,
                "structured_success": False,
                "repair_attempted": False,
                "repair_succeeded": False,
                "failure_reason": "skipped_for_fallback_answer",
                "fallback_used": True,
            }
            logger.warning(
                "Using deterministic verification for fallback answer draft on query %r",
                question[:120],
            )
            return self._build_fallback_report(evidence_bundle, answer_draft)

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
        result = self._runner.run(
            system_prompt=VERIFIER_SYSTEM,
            user_prompt=user_prompt,
            output_model=VerifierOutput,
            schema_label="verifier output",
        )

        if result.parsed is None:
            self.last_run_info = {
                "mode": "deterministic_fallback",
                "attempts": result.attempts,
                "structured_success": False,
                "repair_attempted": result.repair_attempted,
                "repair_succeeded": result.repair_succeeded,
                "failure_reason": result.failure_reason,
                "fallback_used": True,
            }
            logger.warning(
                "Falling back to deterministic verification for query %r after %s attempts: %s",
                question[:120],
                result.attempts,
                result.failure_reason,
            )
            return self._build_fallback_report(evidence_bundle, answer_draft)
        output = result.parsed
        self.last_run_info = {
            "mode": "structured",
            "attempts": result.attempts,
            "structured_success": True,
            "repair_attempted": result.repair_attempted,
            "repair_succeeded": result.repair_succeeded,
            "failure_reason": None,
            "fallback_used": False,
        }

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

    def _should_use_deterministic_verification(
        self,
        answer_draft: AnswerDraftDomain,
    ) -> bool:
        if "Fallback extractive answer built from top evidence" in answer_draft.confidence_notes:
            return True
        return any(
            "local model did not return the required schema" in objection.issue
            for objection in answer_draft.objections_raised
        )
