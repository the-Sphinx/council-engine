import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import (
    AnswerDraft,
    EvidenceBundle,
    Query,
    QueryDebugArtifact,
    VerificationReport,
)
from app.db.session import get_db
from app.schemas.api import (
    QueryCreate,
    QueryResponse,
    RetrievalDebugResponse,
    VerificationResponse,
)
from app.services.project_service import get_project

logger = get_logger(__name__)
router = APIRouter(tags=["queries"])


@router.post("/projects/{project_id}/queries", response_model=QueryResponse, status_code=201)
def create_query(
    project_id: str,
    body: QueryCreate,
    db: Session = Depends(get_db),
):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Project {project_id} not found"},
        )

    from app.main import get_pipeline_for_project, get_generator, get_verifier
    from app.services.query_service import execute_query, IndexNotFoundError
    from app.generation.answer_generator import GenerationError
    from app.generation.verifier import VerificationError

    try:
        pipeline = get_pipeline_for_project(project_id)
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "index_not_found",
                "message": f"No index loaded for project {project_id}. Run POST /projects/{project_id}/index first.",
            },
        )

    generator = get_generator()
    verifier = get_verifier()

    try:
        response = execute_query(
            db=db,
            project_id=project_id,
            question=body.question,
            pipeline=pipeline,
            generator=generator,
            verifier=verifier,
        )
    except IndexNotFoundError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "index_not_found", "message": str(e)},
        )
    except GenerationError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "generation_failed", "message": str(e)},
        )
    except VerificationError as e:
        raise HTTPException(
            status_code=500,
            detail={"error": "verification_failed", "message": str(e)},
        )

    return QueryResponse(
        query_id=response.query_id,
        question=body.question,
        final_answer=response.final_answer,
        citations=[
            {
                "passage_id": c.passage_id,
                "quote": c.quote,
                "section_title": c.section_title,
                "passage_text": c.passage_text,
            }
            for c in response.citations
        ],
        objections=response.objections,
        confidence_notes=response.confidence_notes,
        verification_status=response.verification_status,
        verification_warnings=response.verification_warnings,
        debug_url=response.debug_url,
        error=response.error,
    )


@router.get("/queries/{query_id}", response_model=QueryResponse)
def get_query(query_id: str, db: Session = Depends(get_db)):
    query = db.get(Query, query_id)
    if not query:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Query {query_id} not found"},
        )

    bundle_db = (
        db.query(EvidenceBundle)
        .filter(EvidenceBundle.query_id == query_id)
        .order_by(EvidenceBundle.created_at.desc())
        .first()
    )
    draft_db = (
        db.query(AnswerDraft)
        .filter(AnswerDraft.query_id == query_id)
        .order_by(AnswerDraft.created_at.desc())
        .first()
    )
    report_db = (
        db.query(VerificationReport)
        .filter(VerificationReport.query_id == query_id)
        .order_by(VerificationReport.created_at.desc())
        .first()
    )

    bundle = json.loads(bundle_db.bundle_json) if bundle_db else {}
    citations = []
    if bundle and draft_db:
        anchor_map = {a["passage_id"]: a for a in bundle.get("anchors", [])}
        cit_list = json.loads(draft_db.citations_json or "[]")
        for c in cit_list:
            anchor = anchor_map.get(c["passage_id"], {})
            citations.append({
                "passage_id": c["passage_id"],
                "quote": c.get("quote", ""),
                "section_title": anchor.get("section_title"),
                "passage_text": anchor.get("text", ""),
            })
    objections = []
    if draft_db:
        raw_objections = json.loads(draft_db.objections_json or "[]")
        objections = [
            obj["issue"] if isinstance(obj, dict) else obj
            for obj in raw_objections
        ]

    return QueryResponse(
        query_id=query_id,
        question=query.question_text,
        final_answer=draft_db.answer_text if draft_db else "",
        citations=citations,
        objections=objections,
        confidence_notes="",
        verification_status=report_db.status if report_db else "unknown",
        verification_warnings=[],
        debug_url=f"/queries/{query_id}/retrieval-debug",
    )


@router.get("/queries/{query_id}/retrieval-debug", response_model=RetrievalDebugResponse)
def get_retrieval_debug(query_id: str, db: Session = Depends(get_db)):
    query = db.get(Query, query_id)
    if not query:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Query {query_id} not found"},
        )

    from app.db.models import RetrievalResult
    results = (
        db.query(RetrievalResult)
        .filter(RetrievalResult.query_id == query_id)
        .order_by(RetrievalResult.rank)
        .all()
    )

    bundle_db = (
        db.query(EvidenceBundle)
        .filter(EvidenceBundle.query_id == query_id)
        .first()
    )
    debug_db = (
        db.query(QueryDebugArtifact)
        .filter(QueryDebugArtifact.query_id == query_id)
        .order_by(QueryDebugArtifact.created_at.desc())
        .first()
    )
    draft_db = (
        db.query(AnswerDraft)
        .filter(AnswerDraft.query_id == query_id)
        .order_by(AnswerDraft.created_at.desc())
        .first()
    )
    report_db = (
        db.query(VerificationReport)
        .filter(VerificationReport.query_id == query_id)
        .order_by(VerificationReport.created_at.desc())
        .first()
    )

    draft_dict = None
    if draft_db:
        draft_dict = {
            "answer_text": draft_db.answer_text,
            "claims": json.loads(draft_db.claims_json or "[]"),
            "citations": json.loads(draft_db.citations_json or "[]"),
            "objections": json.loads(draft_db.objections_json or "[]"),
        }

    report_dict = None
    if report_db:
        report_dict = {
            "status": report_db.status,
            "supported_claims": json.loads(report_db.supported_claims_json or "[]"),
            "unsupported_claims": json.loads(report_db.unsupported_claims_json or "[]"),
            "citation_issues": json.loads(report_db.citation_issues_json or "[]"),
            "notes": json.loads(report_db.notes_json or "{}"),
        }

    return RetrievalDebugResponse(
        query_id=query_id,
        question=query.question_text,
        normalized_query=debug_db.normalized_query if debug_db else query.question_text,
        lexical_hits=json.loads(debug_db.lexical_hits_json or "[]") if debug_db else [],
        dense_hits=json.loads(debug_db.dense_hits_json or "[]") if debug_db else [],
        merged_candidates=json.loads(debug_db.merged_candidates_json or "[]") if debug_db else [],
        reranked_candidates=json.loads(debug_db.reranked_candidates_json or "[]") if debug_db else [],
        evidence_bundle=json.loads(bundle_db.bundle_json) if bundle_db else {},
        answer_draft=draft_dict,
        verification_report=report_dict,
    )


@router.get("/queries/{query_id}/verification", response_model=VerificationResponse)
def get_verification(query_id: str, db: Session = Depends(get_db)):
    query = db.get(Query, query_id)
    if not query:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Query {query_id} not found"},
        )

    report_db = (
        db.query(VerificationReport)
        .filter(VerificationReport.query_id == query_id)
        .order_by(VerificationReport.created_at.desc())
        .first()
    )
    if not report_db:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": "No verification report found"},
        )

    return VerificationResponse(
        query_id=query_id,
        status=report_db.status,
        supported_claims=json.loads(report_db.supported_claims_json or "[]"),
        unsupported_claims=json.loads(report_db.unsupported_claims_json or "[]"),
        citation_issues=json.loads(report_db.citation_issues_json or "[]"),
        notes=json.loads(report_db.notes_json or '{"notes": ""}').get("notes", ""),
    )
