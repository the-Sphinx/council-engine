"""
Document service: ingestion and indexing.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.interfaces import EmbedderInterface, PassageForIndex
from app.core.logging import get_logger
from app.db.models import Document, Passage, PassageWindow, Section
from app.ingestion.indexer import IndexManager
from app.ingestion.loaders import CorpusManifest, TextLoader
from app.ingestion.normalizer import normalize_text
from app.ingestion.passage_builder import build_passages
from app.ingestion.sectioner import get_sectioner
from app.ingestion.window_builder import build_windows

logger = get_logger(__name__)


def ingest_document(
    db: Session,
    project_id: str,
    manifest: CorpusManifest,
) -> Document:
    """
    Full ingestion pipeline (synchronous):
    normalize → section → passages → windows → persist.
    Returns the created Document.
    """
    loader = TextLoader()
    raw_text = loader.load(manifest.raw_text_path)
    normalized = normalize_text(raw_text)

    # Persist raw and normalized texts to data dir
    doc_id = str(uuid.uuid4())
    raw_dir = settings.DATA_DIR / "documents" / doc_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "raw.txt"
    norm_path = raw_dir / "normalized.txt"
    raw_path.write_text(raw_text, encoding="utf-8")
    norm_path.write_text(normalized, encoding="utf-8")

    document = Document(
        id=doc_id,
        project_id=project_id,
        title=manifest.title,
        source_type=manifest.source_type,
        language=manifest.language,
        raw_text_path=str(raw_path),
        normalized_text_path=str(norm_path),
        metadata_json=json.dumps(manifest.metadata),
    )
    db.add(document)
    db.flush()

    # Section
    sectioner = get_sectioner(
        manifest.sectioning_strategy,
        boundaries=manifest.section_boundaries,
    )
    section_boundaries = sectioner.section(normalized)
    logger.info("Document %s: %d sections", doc_id, len(section_boundaries))

    db_sections: list[Section] = []
    for sb in section_boundaries:
        section = Section(
            document_id=doc_id,
            section_type=sb.section_type,
            title=sb.title,
            order_index=sb.order_index,
            start_offset=sb.start_offset,
            end_offset=sb.end_offset,
            metadata_json=json.dumps(sb.metadata),
        )
        db.add(section)
        db.flush()
        db_sections.append(section)

    # Passages
    global_passage_index = 0
    all_passage_dicts: list[dict] = []

    for section, sb in zip(db_sections, section_boundaries):
        section_text = normalized[sb.start_offset : sb.end_offset]
        raw_passages = build_passages(
            section_text,
            section_start_offset=sb.start_offset,
            strategy=manifest.passage_strategy,
        )

        for rp in raw_passages:
            if not rp.text.strip():
                continue
            norm_passage_text = normalize_text(rp.text)
            passage = Passage(
                document_id=doc_id,
                section_id=section.id,
                passage_index=global_passage_index,
                text=rp.text,
                normalized_text=norm_passage_text,
                start_offset=rp.start_offset,
                end_offset=rp.end_offset,
                token_count=len(norm_passage_text.split()),
                metadata_json=json.dumps({"section_title": section.title}),
            )
            db.add(passage)
            db.flush()

            all_passage_dicts.append({
                "id": passage.id,
                "passage_index": passage.passage_index,
                "text": passage.text,
                "normalized_text": passage.normalized_text,
                "document_id": doc_id,
                "section_id": section.id,
                "section_title": section.title,
            })
            global_passage_index += 1

    logger.info("Document %s: %d passages created", doc_id, global_passage_index)

    # Windows
    radius = settings.get_retrieval_config().context_window_radius
    window_specs = build_windows(all_passage_dicts, radius=radius)
    for ws in window_specs:
        pw = PassageWindow(
            document_id=doc_id,
            anchor_passage_id=ws.anchor_passage_id,
            start_passage_index=ws.start_passage_index,
            end_passage_index=ws.end_passage_index,
            text=ws.text,
            normalized_text=ws.normalized_text,
        )
        db.add(pw)

    db.commit()
    db.refresh(document)
    logger.info(
        "Ingested document %s: %d sections, %d passages, %d windows",
        doc_id,
        len(db_sections),
        global_passage_index,
        len(window_specs),
    )
    return document


def build_index(
    db: Session,
    project_id: str,
    embedder: EmbedderInterface,
) -> IndexManager:
    """
    Build BM25 + dense indices for all passages in the project.
    Saves indices to disk.
    """
    index_dir = settings.INDICES_DIR / project_id
    im = IndexManager(index_dir)

    # Fetch all passages for this project
    passages_db = (
        db.query(Passage)
        .join(Document, Passage.document_id == Document.id)
        .filter(Document.project_id == project_id)
        .order_by(Passage.document_id, Passage.passage_index)
        .all()
    )

    if not passages_db:
        raise ValueError(f"No passages found for project {project_id}")

    # Load section titles
    section_map: dict[str, str | None] = {}
    for p in passages_db:
        if p.section_id and p.section_id not in section_map:
            section = db.get(Section, p.section_id)
            section_map[p.section_id] = section.title if section else None

    passage_for_index = [
        PassageForIndex(
            passage_id=p.id,
            document_id=p.document_id,
            section_id=p.section_id,
            text=p.text,
            normalized_text=p.normalized_text,
            passage_index=p.passage_index,
            section_title=section_map.get(p.section_id or ""),
        )
        for p in passages_db
    ]

    logger.info("Building indices for project %s: %d passages", project_id, len(passage_for_index))
    im.build_lexical(passage_for_index)
    im.build_dense(passage_for_index, embedder)
    im.save()
    logger.info("Indices saved to %s", index_dir)
    return im


def get_document(db: Session, document_id: str) -> Document | None:
    return db.get(Document, document_id)


def list_documents(db: Session, project_id: str) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.created_at.desc())
        .all()
    )
