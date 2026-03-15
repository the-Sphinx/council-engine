"""Grounding/citation evaluation metrics."""

from __future__ import annotations

from app.core.interfaces import AnswerDraftDomain, VerificationReportDomain


def citation_validity_rate(
    answer_draft: AnswerDraftDomain,
    valid_passage_ids: set[str],
) -> float:
    """Fraction of cited passage IDs that exist in the passage store."""
    cited = [c.passage_id for c in answer_draft.supporting_citations]
    if not cited:
        return 1.0
    valid = [pid for pid in cited if pid in valid_passage_ids]
    return len(valid) / len(cited)


def claim_support_rate(report: VerificationReportDomain) -> float:
    """Fraction of claims judged supported by the verifier."""
    total = len(report.supported_claims) + len(report.unsupported_claims)
    if total == 0:
        return 1.0
    return len(report.supported_claims) / total


def unsupported_claim_count(report: VerificationReportDomain) -> int:
    return len(report.unsupported_claims)


def verifier_status(report: VerificationReportDomain) -> str:
    return report.status


def compute_grounding_metrics(
    answer_draft: AnswerDraftDomain,
    report: VerificationReportDomain,
    valid_passage_ids: set[str],
) -> dict:
    return {
        "citation_validity_rate": citation_validity_rate(answer_draft, valid_passage_ids),
        "claim_support_rate": claim_support_rate(report),
        "unsupported_claim_count": unsupported_claim_count(report),
        "verifier_status": verifier_status(report),
    }
