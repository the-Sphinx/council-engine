"""
Evidence bundle builder: assembles anchor passages + context windows into
an EvidenceBundleDomain ready for answer generation.
"""

from __future__ import annotations

from app.core.interfaces import (
    AnchorPassage,
    EvidenceBundleDomain,
    RetrievalCandidate,
)
from app.retrieval.context_expander import ExpandedContext


def build_evidence_bundle(
    query_id: str,
    anchors: list[RetrievalCandidate],
    contexts: list[ExpandedContext],
    top_k_anchors: int = 6,
    max_bundle_passages: int = 12,
) -> EvidenceBundleDomain:
    """
    Combine reranked anchors and their expanded contexts into an EvidenceBundleDomain.

    - Caps at top_k_anchors
    - Deduplicates overlapping window passages
    - Enforces max_bundle_passages across all windows
    """
    assert len(anchors) == len(contexts), "anchors and contexts must be parallel"

    # Cap anchors
    anchors = anchors[:top_k_anchors]
    contexts = contexts[:top_k_anchors]

    seen_passage_ids: set[str] = set()
    total_window_passages = 0
    bundle_anchors: list[AnchorPassage] = []

    for rank, (candidate, ctx) in enumerate(zip(anchors, contexts)):
        if total_window_passages >= max_bundle_passages:
            break

        # Deduplicate window passage IDs
        unique_window_ids = [
            pid for pid in ctx.window_passage_ids if pid not in seen_passage_ids
        ]
        # Respect overall cap
        remaining_budget = max_bundle_passages - total_window_passages
        unique_window_ids = unique_window_ids[:remaining_budget]

        seen_passage_ids.update(unique_window_ids)
        total_window_passages += len(unique_window_ids)

        scores: dict[str, float] = {}
        if candidate.lexical_score is not None:
            scores["lexical"] = round(candidate.lexical_score, 4)
        if candidate.dense_score is not None:
            scores["dense"] = round(candidate.dense_score, 4)
        if candidate.hybrid_score is not None:
            scores["hybrid"] = round(candidate.hybrid_score, 4)
        if candidate.rerank_score is not None:
            scores["rerank"] = round(candidate.rerank_score, 4)

        bundle_anchors.append(
            AnchorPassage(
                passage_id=candidate.passage_id,
                text=ctx.anchor_text,
                rank=rank + 1,
                scores=scores,
                section_title=ctx.section_title,
                section_order_index=ctx.section_order_index,
                window_passage_ids=unique_window_ids,
                window_text=ctx.window_text,
            )
        )

    return EvidenceBundleDomain(
        query_id=query_id,
        mode="source_only",
        anchors=bundle_anchors,
    )
