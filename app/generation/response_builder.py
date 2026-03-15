"""
Response builder: decides final response based on verification status.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from app.core.interfaces import (
    AnswerDraftDomain,
    EvidenceBundleDomain,
    VerificationReportDomain,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class CitationInfo:
    passage_id: str
    quote: str
    section_title: Optional[str]
    passage_text: str


@dataclass
class FinalResponse:
    query_id: str
    final_answer: str
    citations: list[CitationInfo]
    objections: list[str]
    confidence_notes: str
    verification_status: str
    verification_warnings: list[str]
    debug_url: str
    error: Optional[str] = None


def build_final_response(
    query_id: str,
    question: str,
    evidence_bundle: EvidenceBundleDomain,
    answer_draft: AnswerDraftDomain,
    verification_report: VerificationReportDomain,
) -> FinalResponse:
    """
    Build the user-facing response based on verification status.
    - pass: return full answer + citations
    - pass_with_warnings: prepend warnings section
    - fail: return structured error with debug link
    """
    debug_url = f"/queries/{query_id}/retrieval-debug"
    anchor_map = {a.passage_id: a for a in evidence_bundle.anchors}

    citations = []
    for cit in answer_draft.supporting_citations:
        anchor = anchor_map.get(cit.passage_id)
        citations.append(
            CitationInfo(
                passage_id=cit.passage_id,
                quote=cit.quote,
                section_title=anchor.section_title if anchor else None,
                passage_text=anchor.text if anchor else "",
            )
        )

    objections = [o.issue for o in answer_draft.objections_raised]
    warnings = []

    if verification_report.status == "pass":
        return FinalResponse(
            query_id=query_id,
            final_answer=answer_draft.final_answer,
            citations=citations,
            objections=objections,
            confidence_notes=answer_draft.confidence_notes,
            verification_status="pass",
            verification_warnings=[],
            debug_url=debug_url,
        )

    elif verification_report.status == "pass_with_warnings":
        if verification_report.unsupported_claims:
            warnings.append(
                f"{len(verification_report.unsupported_claims)} claim(s) could not be fully verified."
            )
        if verification_report.citation_issues:
            warnings.append(
                f"{len(verification_report.citation_issues)} citation issue(s) detected."
            )
        if verification_report.notes:
            warnings.append(verification_report.notes)

        return FinalResponse(
            query_id=query_id,
            final_answer=answer_draft.final_answer,
            citations=citations,
            objections=objections,
            confidence_notes=answer_draft.confidence_notes,
            verification_status="pass_with_warnings",
            verification_warnings=warnings,
            debug_url=debug_url,
        )

    else:  # fail
        logger.warning(
            "Verification FAILED for query %s. Notes: %s",
            query_id,
            verification_report.notes,
        )
        return FinalResponse(
            query_id=query_id,
            final_answer="",
            citations=[],
            objections=[],
            confidence_notes="",
            verification_status="fail",
            verification_warnings=[
                "The answer could not be verified against the source text.",
                f"Unsupported claims: {len(verification_report.unsupported_claims)}",
                verification_report.notes or "",
            ],
            debug_url=debug_url,
            error=(
                f"Verification failed. The answer contained {len(verification_report.unsupported_claims)} "
                f"unsupported claim(s). See {debug_url} for details."
            ),
        )
