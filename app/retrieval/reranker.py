from __future__ import annotations

from app.core.interfaces import RerankerInterface, RetrievalCandidate
from app.core.logging import get_logger

logger = get_logger(__name__)


class NoOpReranker(RerankerInterface):
    """Pass-through reranker: returns candidates unchanged (uses hybrid_score as rerank_score)."""

    def rerank(
        self, query: str, candidates: list[RetrievalCandidate]
    ) -> list[RetrievalCandidate]:
        for c in candidates:
            c.rerank_score = c.hybrid_score
        for rank, c in enumerate(candidates):
            c.rank_rerank = rank
        return candidates


class CrossEncoderReranker(RerankerInterface):
    """
    Cross-encoder reranker using sentence-transformers CrossEncoder.
    Model: cross-encoder/ms-marco-MiniLM-L-6-v2 (or configured model).
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self._model_name = model_name
        self._model = None

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self._model_name)
        return self._model

    def rerank(
        self, query: str, candidates: list[RetrievalCandidate]
    ) -> list[RetrievalCandidate]:
        if not candidates:
            return candidates

        try:
            model = self._get_model()
            pairs = [(query, c.passage_text) for c in candidates]
            scores = model.predict(pairs)

            for c, score in zip(candidates, scores):
                c.rerank_score = float(score)

            candidates.sort(key=lambda c: c.rerank_score or 0.0, reverse=True)
            for rank, c in enumerate(candidates):
                c.rank_rerank = rank

        except Exception as e:
            logger.warning("CrossEncoder reranking failed (%s), falling back to NoOp", e)
            noop = NoOpReranker()
            candidates = noop.rerank(query, candidates)

        return candidates


def get_reranker(enabled: bool, model_name: str) -> RerankerInterface:
    if enabled:
        return CrossEncoderReranker(model_name)
    return NoOpReranker()
