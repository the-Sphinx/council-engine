import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.session import get_db
from app.ingestion.loaders import CorpusManifest
from app.schemas.api import DocumentResponse, IndexResponse
from app.services.document_service import build_index, ingest_document, list_documents
from app.services.project_service import get_project

logger = get_logger(__name__)
router = APIRouter(prefix="/projects", tags=["documents"])


def _infer_passage_strategy(text: str) -> str:
    """
    Favor line-based passages for corpora that are mostly one unit per line,
    while keeping paragraph-based splitting for normal prose uploads.
    """
    lines = [line.strip() for line in text.splitlines()]
    non_empty_lines = [line for line in lines if line]
    if len(non_empty_lines) < 3:
        return "paragraph"

    blank_lines = sum(1 for line in lines if not line)
    line_based_ratio = len(non_empty_lines) / max(len(lines), 1)
    blank_line_ratio = blank_lines / max(len(lines), 1)
    average_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines)
    allowed_blank_lines = max(3, int(len(lines) * 0.02))

    if (
        blank_lines <= allowed_blank_lines
        and blank_line_ratio <= 0.2
        and line_based_ratio >= 0.85
        and average_line_length < 220
    ):
        return "natural_units"
    return "paragraph"


@router.post("/{project_id}/documents", response_model=DocumentResponse, status_code=201)
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Project {project_id} not found"},
        )

    # Save uploaded file to a temp location
    suffix = Path(file.filename or "corpus.txt").suffix or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    decoded_content = content.decode("utf-8")

    title = file.filename or "Uploaded Document"
    manifest = CorpusManifest(
        title=title,
        source_type="uploaded_text",
        language="en",
        raw_text_path=tmp_path,
        sectioning_strategy="paragraph",
        passage_strategy=_infer_passage_strategy(decoded_content),
    )

    try:
        doc = ingest_document(db, project_id=project_id, manifest=manifest)
    finally:
        tmp_path.unlink(missing_ok=True)

    return doc


@router.get("/{project_id}/documents", response_model=list[DocumentResponse])
def list_documents_endpoint(project_id: str, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Project {project_id} not found"},
        )
    return list_documents(db, project_id)


@router.post("/{project_id}/index", response_model=IndexResponse)
def build_index_endpoint(project_id: str, db: Session = Depends(get_db)):
    """Build/rebuild lexical and dense indices for a project."""
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"error": "not_found", "message": f"Project {project_id} not found"},
        )

    # Load embedder
    from app.retrieval.dense import SentenceTransformerEmbedder
    from app.core.config import settings
    embedder = SentenceTransformerEmbedder(settings.EMBEDDER_MODEL)

    try:
        im = build_index(db, project_id=project_id, embedder=embedder)
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"error": "validation_error", "message": str(e)},
        )

    # Reload into app state
    from app.main import reload_project_index
    reload_project_index(project_id, im)

    return IndexResponse(
        project_id=project_id,
        status="ok",
        message=f"Index built successfully for project {project_id}",
    )
