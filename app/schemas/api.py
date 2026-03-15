"""FastAPI request/response Pydantic models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class DocumentResponse(BaseModel):
    id: str
    project_id: str
    title: str
    source_type: str
    language: str
    created_at: datetime


class IndexResponse(BaseModel):
    project_id: str
    status: str
    message: str


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

class QueryCreate(BaseModel):
    question: str
    mode: str = "source_only"


class CitationResponse(BaseModel):
    passage_id: str
    quote: str
    section_title: Optional[str]
    passage_text: str


class QueryResponse(BaseModel):
    query_id: str
    question: str
    final_answer: str
    citations: list[CitationResponse]
    objections: list[str]
    confidence_notes: str
    verification_status: str
    verification_warnings: list[str]
    debug_url: str
    error: Optional[str] = None


class RetrievalDebugResponse(BaseModel):
    query_id: str
    question: str
    normalized_query: str
    lexical_hits: list[dict]
    dense_hits: list[dict]
    merged_candidates: list[dict]
    reranked_candidates: list[dict]
    evidence_bundle: dict
    answer_draft: Optional[dict]
    verification_report: Optional[dict]


class VerificationResponse(BaseModel):
    query_id: str
    status: str
    supported_claims: list[str]
    unsupported_claims: list[dict]
    citation_issues: list[dict]
    notes: str


# ---------------------------------------------------------------------------
# Evals
# ---------------------------------------------------------------------------

class EvalRunRequest(BaseModel):
    project_id: str
    eval_dataset_path: str
    label: Optional[str] = None


class EvalRunResponse(BaseModel):
    run_id: str
    label: Optional[str]
    status: str
    output_path: str


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: Optional[Any] = None
