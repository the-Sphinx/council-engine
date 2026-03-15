from __future__ import annotations

from app.core.interfaces import (
    LexicalRetrieverInterface,
    PassageForIndex,
    RetrievalCandidate,
)
from app.ingestion.indexer import IndexManager


class BM25Retriever(LexicalRetrieverInterface):
    def __init__(self, index_manager: IndexManager):
        self._im = index_manager

    def build_index(self, passages: list[PassageForIndex]) -> None:
        self._im.build_lexical(passages)

    def save_index(self, path: str) -> None:
        self._im.save()

    def load_index(self, path: str) -> None:
        self._im._load_lexical()

    def search(self, query: str, top_k: int) -> list[RetrievalCandidate]:
        hits = self._im.search_lexical(query, top_k)
        candidates = []
        for h in hits:
            c = RetrievalCandidate(
                passage_id=h["passage_id"],
                document_id=h["document_id"],
                section_id=h.get("section_id"),
                passage_text=h["text"],
                normalized_text=h.get("normalized_text", ""),
                lexical_score=h["score"],
                source_methods=["bm25"],
                rank_lexical=h["rank"],
                metadata=h.get("metadata", {}),
            )
            c.metadata["section_title"] = h.get("section_title")
            c.metadata["passage_index"] = h.get("passage_index")
            candidates.append(c)
        return candidates
