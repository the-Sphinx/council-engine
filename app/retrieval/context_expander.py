"""
Context expansion: given anchor passages, fetch neighboring passages from the DB
and build expanded windows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.interfaces import RetrievalCandidate
from app.db.models import Passage, Section


@dataclass
class ExpandedContext:
    anchor_passage_id: str
    anchor_text: str
    section_title: Optional[str]
    section_order_index: Optional[int]
    window_passage_ids: list[str]
    window_text: str
    metadata: dict = field(default_factory=dict)


def expand_context(
    anchor: RetrievalCandidate,
    db: Session,
    radius: int = 1,
) -> ExpandedContext:
    """
    Fetch neighboring passages from the DB around the anchor passage.
    Deduplicates and respects document boundaries.
    """
    # Get the anchor passage
    anchor_passage = db.get(Passage, anchor.passage_id)
    if anchor_passage is None:
        # Fallback: return anchor-only context
        return ExpandedContext(
            anchor_passage_id=anchor.passage_id,
            anchor_text=anchor.passage_text,
            section_title=anchor.metadata.get("section_title"),
            section_order_index=None,
            window_passage_ids=[anchor.passage_id],
            window_text=anchor.passage_text,
        )

    doc_id = anchor_passage.document_id
    anchor_idx = anchor_passage.passage_index
    start_idx = max(0, anchor_idx - radius)
    end_idx = anchor_idx + radius

    neighbors = (
        db.query(Passage)
        .filter(
            and_(
                Passage.document_id == doc_id,
                Passage.passage_index >= start_idx,
                Passage.passage_index <= end_idx,
            )
        )
        .order_by(Passage.passage_index)
        .all()
    )

    window_ids = [p.id for p in neighbors]
    window_text = " ".join(p.text for p in neighbors)

    section_title = None
    section_order = None
    if anchor_passage.section_id:
        section = db.get(Section, anchor_passage.section_id)
        if section:
            section_title = section.title
            section_order = section.order_index

    return ExpandedContext(
        anchor_passage_id=anchor.passage_id,
        anchor_text=anchor_passage.text,
        section_title=section_title,
        section_order_index=section_order,
        window_passage_ids=window_ids,
        window_text=window_text,
    )
