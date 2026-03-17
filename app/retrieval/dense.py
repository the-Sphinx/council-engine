from __future__ import annotations

import hashlib

import numpy as np

from app.core.interfaces import (
    DenseRetrieverInterface,
    EmbedderInterface,
    PassageForIndex,
    RetrievalCandidate,
)
from app.ingestion.indexer import IndexManager
from app.core.logging import get_logger

logger = get_logger(__name__)


class HashingEmbedder(EmbedderInterface):
    """
    Lightweight deterministic fallback embedder for offline/dev use.

    It preserves the dense retrieval interface without requiring a model download.
    """

    def __init__(self, dims: int = 384):
        self._dims = dims

    def _embed(self, text: str) -> list[float]:
        vector = np.zeros(self._dims, dtype=np.float32)
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dims
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class SentenceTransformerEmbedder(EmbedderInterface):
    """Wraps sentence-transformers for embedding."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self._model_name = model_name
        self._model = None
        self._fallback_embedder: EmbedderInterface | None = None

    def _get_model(self):
        if self._fallback_embedder is not None:
            return None
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                try:
                    self._model = SentenceTransformer(self._model_name, local_files_only=True)
                except Exception:
                    self._model = SentenceTransformer(self._model_name)
            except Exception as exc:
                logger.warning(
                    "Falling back to hashing embedder because %s could not be loaded: %s",
                    self._model_name,
                    exc,
                )
                self._fallback_embedder = HashingEmbedder()
                return None
        return self._model

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        model = self._get_model()
        if self._fallback_embedder is not None:
            return self._fallback_embedder.embed_texts(texts)
        vecs = model.encode(texts, show_progress_bar=False, normalize_embeddings=False)
        return [v.tolist() for v in vecs]

    def embed_query(self, text: str) -> list[float]:
        model = self._get_model()
        if self._fallback_embedder is not None:
            return self._fallback_embedder.embed_query(text)
        vec = model.encode([text], show_progress_bar=False, normalize_embeddings=False)[0]
        return vec.tolist()


class NumpyDenseRetriever(DenseRetrieverInterface):
    def __init__(self, index_manager: IndexManager, embedder: EmbedderInterface):
        self._im = index_manager
        self._embedder = embedder

    def build_index(self, passages: list[PassageForIndex]) -> None:
        self._im.build_dense(passages, self._embedder)

    def save_index(self, path: str) -> None:
        self._im.save()

    def load_index(self, path: str) -> None:
        self._im._load_dense()

    def search(self, query: str, top_k: int) -> list[RetrievalCandidate]:
        query_vec = self._embedder.embed_query(query)
        hits = self._im.search_dense(query_vec, top_k)
        candidates = []
        for h in hits:
            c = RetrievalCandidate(
                passage_id=h["passage_id"],
                document_id=h["document_id"],
                section_id=h.get("section_id"),
                passage_text=h["text"],
                normalized_text=h.get("normalized_text", ""),
                dense_score=h["score"],
                source_methods=["dense"],
                rank_dense=h["rank"],
                metadata=h.get("metadata", {}),
            )
            c.metadata["section_title"] = h.get("section_title")
            c.metadata["passage_index"] = h.get("passage_index")
            candidates.append(c)
        return candidates
