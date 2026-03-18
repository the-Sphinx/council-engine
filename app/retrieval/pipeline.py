"""
RetrievalPipeline: orchestrates all 9 retrieval stages.

Stages:
1. Query normalization
2. Lexical retrieval
3. Dense retrieval
4. Candidate merge
5. Score normalization
6. Hybrid fusion
7. Reranking
8. Context expansion
9. Evidence bundle creation
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import RetrievalConfig
from app.core.interfaces import (
    DenseRetrieverInterface,
    EvidenceBundleDomain,
    LexicalRetrieverInterface,
    RerankerInterface,
    RetrievalCandidate,
)
from app.core.logging import get_logger
from app.db.models import RetrievalResult
from app.ingestion.normalizer import normalize_query
from app.retrieval.context_expander import expand_context
from app.retrieval.evidence_bundle import build_evidence_bundle
from app.retrieval.hybrid import compute_hybrid_scores, merge_candidates, normalize_scores
from app.retrieval.query_processing import build_lexical_query

logger = get_logger(__name__)


@dataclass
class PipelineDebugInfo:
    original_query: str
    normalized_query: str
    lexical_query: str
    expanded_terms: list[str]
    hybrid_alpha: float
    hybrid_beta: float
    overlap_boost_enabled: bool
    overlap_boost_value: float
    reranker_enabled: bool
    reranker_top_k: int
    lexical_candidates: list[RetrievalCandidate]
    dense_candidates: list[RetrievalCandidate]
    merged_candidates: list[RetrievalCandidate]
    reranked_candidates: list[RetrievalCandidate]


class RetrievalPipeline:
    def __init__(
        self,
        lexical_retriever: LexicalRetrieverInterface,
        dense_retriever: DenseRetrieverInterface,
        reranker: RerankerInterface,
        config: RetrievalConfig,
    ):
        self._lex = lexical_retriever
        self._dense = dense_retriever
        self._reranker = reranker
        self._config = config

    def run(
        self,
        query_id: str,
        question: str,
        db: Session,
    ) -> tuple[EvidenceBundleDomain, PipelineDebugInfo]:
        cfg = self._config

        # Stage 1: Query normalization
        normalized_q = normalize_query(question)
        lexical_query_debug = build_lexical_query(
            question=question,
            normalized_query=normalized_q,
            expansions=cfg.lexical_query_expansions,
            expansion_enabled=cfg.lexical_query_expansion_enabled,
        )
        logger.info("Pipeline query_id=%s | normalized_q=%r", query_id, normalized_q[:80])

        # Stage 2: Lexical retrieval
        lexical_candidates = self._lex.search(lexical_query_debug.lexical_query, cfg.top_k_lexical)
        logger.debug("Lexical hits: %d", len(lexical_candidates))

        # Stage 3: Dense retrieval
        dense_candidates = self._dense.search(normalized_q, cfg.top_k_dense)
        logger.debug("Dense hits: %d", len(dense_candidates))

        # Stage 4: Merge
        merged = merge_candidates(lexical_candidates, dense_candidates)
        logger.debug("Merged candidates: %d", len(merged))

        # Stage 5: Score normalization
        normalize_scores(merged, "lexical")
        normalize_scores(merged, "dense")

        # Stage 6: Hybrid fusion
        merged = compute_hybrid_scores(
            merged,
            alpha=cfg.hybrid_alpha,
            beta=cfg.hybrid_beta,
            overlap_boost_enabled=cfg.overlap_boost_enabled,
            overlap_boost_value=cfg.overlap_boost_value,
        )

        # Stage 7: Reranking
        top_for_rerank = merged[: cfg.reranker_top_k]
        reranked = self._reranker.rerank(normalized_q, top_for_rerank)
        logger.debug("Reranked candidates: %d", len(reranked))

        # Persist all RetrievalResult rows
        self._persist_results(query_id, reranked, db)

        # Stage 8: Context expansion
        top_anchors = reranked[: cfg.top_k_anchors]
        contexts = [
            expand_context(anchor, db, cfg.context_window_radius)
            for anchor in top_anchors
        ]

        # Stage 9: Evidence bundle
        bundle = build_evidence_bundle(
            query_id=query_id,
            anchors=top_anchors,
            contexts=contexts,
            top_k_anchors=cfg.top_k_anchors,
            max_bundle_passages=cfg.max_bundle_passages,
        )

        debug = PipelineDebugInfo(
            original_query=question,
            normalized_query=normalized_q,
            lexical_query=lexical_query_debug.lexical_query,
            expanded_terms=lexical_query_debug.expanded_terms,
            hybrid_alpha=cfg.hybrid_alpha,
            hybrid_beta=cfg.hybrid_beta,
            overlap_boost_enabled=cfg.overlap_boost_enabled,
            overlap_boost_value=cfg.overlap_boost_value,
            reranker_enabled=cfg.reranker_enabled,
            reranker_top_k=cfg.reranker_top_k,
            lexical_candidates=lexical_candidates,
            dense_candidates=dense_candidates,
            merged_candidates=merged,
            reranked_candidates=reranked,
        )

        return bundle, debug

    def _persist_results(
        self,
        query_id: str,
        candidates: list[RetrievalCandidate],
        db: Session,
    ) -> None:
        rows = []
        for c in candidates:
            meta = {
                "lexical_score": c.lexical_score,
                "dense_score": c.dense_score,
                "lexical_score_normalized": c.lexical_score_normalized,
                "dense_score_normalized": c.dense_score_normalized,
                "overlap_matched": c.overlap_matched,
                "overlap_boost": c.overlap_boost,
                "hybrid_score": c.hybrid_score,
                "rerank_score": c.rerank_score,
                "source_methods": c.source_methods,
            }
            rows.append(
                RetrievalResult(
                    query_id=query_id,
                    passage_id=c.passage_id,
                    retrieval_method="hybrid_reranked",
                    raw_score=c.rerank_score or c.hybrid_score,
                    rank=c.rank_rerank,
                    metadata_json=json.dumps(meta),
                )
            )
        db.add_all(rows)
        # Caller is responsible for commit
