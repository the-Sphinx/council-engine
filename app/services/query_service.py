"""
Query service: orchestrates the full pipeline for a user question.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.interfaces import AnswerGeneratorInterface, VerifierInterface
from app.core.logging import get_logger
from app.db.models import (
    AnswerDraft,
    EvidenceBundle,
    Query,
    QueryDebugArtifact,
    VerificationReport,
)
from app.generation.response_builder import FinalResponse, build_final_response
from app.retrieval.pipeline import RetrievalPipeline

logger = get_logger(__name__)


class IndexNotFoundError(Exception):
    pass


def execute_query(
    db: Session,
    project_id: str,
    question: str,
    pipeline: RetrievalPipeline,
    generator: AnswerGeneratorInterface,
    verifier: VerifierInterface,
) -> FinalResponse:
    """
    Full pipeline:
    1. Store query
    2. Retrieval pipeline → EvidenceBundle
    3. Answer generation
    4. Verification
    5. Persist all artifacts
    6. Build final response
    """
    # Store query
    query = Query(project_id=project_id, question_text=question, mode="source_only")
    db.add(query)
    db.flush()
    query_id = query.id

    # Retrieval
    try:
        bundle, debug_info = pipeline.run(query_id=query_id, question=question, db=db)
    except RuntimeError as e:
        if "index not loaded" in str(e).lower() or "not loaded" in str(e).lower():
            db.rollback()
            raise IndexNotFoundError(
                f"Index not found for project {project_id}. "
                "Please run POST /projects/{project_id}/index first."
            ) from e
        raise

    # Persist evidence bundle
    bundle_db = EvidenceBundle(
        query_id=query_id,
        bundle_json=json.dumps(_bundle_to_dict(bundle)),
    )
    db.add(bundle_db)
    db.flush()
    bundle.bundle_id = bundle_db.id

    debug_db = QueryDebugArtifact(
        query_id=query_id,
        original_query=debug_info.original_query,
        normalized_query=debug_info.normalized_query,
        lexical_query=debug_info.lexical_query,
        expanded_terms_json=json.dumps(debug_info.expanded_terms),
        retrieval_config_json=json.dumps(
            {
                "hybrid_alpha": debug_info.hybrid_alpha,
                "hybrid_beta": debug_info.hybrid_beta,
                "overlap_boost_enabled": debug_info.overlap_boost_enabled,
                "overlap_boost_value": debug_info.overlap_boost_value,
                "reranker_enabled": debug_info.reranker_enabled,
                "reranker_top_k": debug_info.reranker_top_k,
            }
        ),
        lexical_hits_json=json.dumps([_candidate_to_dict(c) for c in debug_info.lexical_candidates]),
        dense_hits_json=json.dumps([_candidate_to_dict(c) for c in debug_info.dense_candidates]),
        merged_candidates_json=json.dumps([_candidate_to_dict(c) for c in debug_info.merged_candidates]),
        reranked_candidates_json=json.dumps([_candidate_to_dict(c) for c in debug_info.reranked_candidates]),
    )
    db.add(debug_db)
    db.flush()

    # Answer generation
    from app.generation.answer_generator import GenerationError
    try:
        answer_draft = generator.generate(question, bundle)
    except GenerationError as e:
        db.commit()  # persist what we have
        raise

    # Persist answer draft
    draft_db = AnswerDraft(
        query_id=query_id,
        answer_text=answer_draft.final_answer,
        claims_json=json.dumps([_claim_to_dict(c) for c in answer_draft.claims]),
        citations_json=json.dumps([_cit_to_dict(c) for c in answer_draft.supporting_citations]),
        objections_json=json.dumps([_obj_to_dict(o) for o in answer_draft.objections_raised]),
    )
    db.add(draft_db)
    db.flush()
    answer_draft.draft_id = draft_db.id

    # Verification
    from app.generation.verifier import VerificationError
    try:
        report = verifier.verify(question, bundle, answer_draft)
    except VerificationError as e:
        db.commit()
        raise

    # If fail, try regeneration once
    if report.status == "fail":
        logger.warning("First verification failed for query %s, retrying generation", query_id)
        try:
            answer_draft = generator.generate(question, bundle)
            report = verifier.verify(question, bundle, answer_draft)

            draft_db2 = AnswerDraft(
                query_id=query_id,
                answer_text=answer_draft.final_answer,
                claims_json=json.dumps([_claim_to_dict(c) for c in answer_draft.claims]),
                citations_json=json.dumps([_cit_to_dict(c) for c in answer_draft.supporting_citations]),
                objections_json=json.dumps([_obj_to_dict(o) for o in answer_draft.objections_raised]),
            )
            db.add(draft_db2)
            db.flush()
            answer_draft.draft_id = draft_db2.id
        except Exception as e:
            logger.error("Regeneration also failed: %s", e)

    # Persist verification report
    report_db = VerificationReport(
        query_id=query_id,
        status=report.status,
        supported_claims_json=json.dumps(report.supported_claims),
        unsupported_claims_json=json.dumps(
            [{"claim_id": u.claim_id, "reason": u.reason} for u in report.unsupported_claims]
        ),
        citation_issues_json=json.dumps(
            [{"passage_id": ci.passage_id, "issue": ci.issue} for ci in report.citation_issues]
        ),
        notes_json=json.dumps({"notes": report.notes}),
    )
    db.add(report_db)
    db.commit()
    report.report_id = report_db.id

    return build_final_response(
        query_id=query_id,
        question=question,
        evidence_bundle=bundle,
        answer_draft=answer_draft,
        verification_report=report,
    )


def _bundle_to_dict(bundle) -> dict:
    return {
        "query_id": bundle.query_id,
        "mode": bundle.mode,
        "anchors": [
            {
                "passage_id": a.passage_id,
                "text": a.text,
                "rank": a.rank,
                "scores": a.scores,
                "section_title": a.section_title,
                "section_order_index": a.section_order_index,
                "window_passage_ids": a.window_passage_ids,
                "window_text": a.window_text,
            }
            for a in bundle.anchors
        ],
    }


def _claim_to_dict(c) -> dict:
    return {
        "claim_id": c.claim_id,
        "statement": c.statement,
        "supporting_passage_ids": c.supporting_passage_ids,
        "support_type": c.support_type,
    }


def _cit_to_dict(c) -> dict:
    return {"passage_id": c.passage_id, "quote": c.quote}


def _obj_to_dict(o) -> dict:
    return {"issue": o.issue, "related_passage_ids": o.related_passage_ids}


def _candidate_to_dict(candidate) -> dict:
    return {
        "passage_id": candidate.passage_id,
        "document_id": candidate.document_id,
        "section_id": candidate.section_id,
        "passage_text": candidate.passage_text,
        "normalized_text": candidate.normalized_text,
        "lexical_score": candidate.lexical_score,
        "dense_score": candidate.dense_score,
        "lexical_score_normalized": candidate.lexical_score_normalized,
        "dense_score_normalized": candidate.dense_score_normalized,
        "overlap_matched": candidate.overlap_matched,
        "overlap_boost": candidate.overlap_boost,
        "hybrid_score": candidate.hybrid_score,
        "rerank_score": candidate.rerank_score,
        "source_methods": candidate.source_methods,
        "rank_lexical": candidate.rank_lexical,
        "rank_dense": candidate.rank_dense,
        "rank_hybrid": candidate.rank_hybrid,
        "rank_rerank": candidate.rank_rerank,
        "metadata": candidate.metadata,
    }
