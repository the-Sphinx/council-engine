"""
IndexManager: builds, saves, and loads BM25 + numpy dense indices for a project.

Index files per project (under INDICES_DIR/{project_id}/):
  lexical.pkl       — pickled BM25Okapi
  dense_vectors.npy — float32 numpy array (N x D)
  dense_meta.json   — list of {passage_id, document_id, section_id, text}
"""

from __future__ import annotations

import json
import pickle
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from app.core.interfaces import PassageForIndex
from app.core.logging import get_logger
from app.retrieval.query_processing import tokenize_text_for_lexical

logger = get_logger(__name__)


class IndexManager:
    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self._bm25: BM25Okapi | None = None
        self._bm25_meta: list[dict] | None = None  # passage metadata parallel to corpus
        self._dense_vectors: np.ndarray | None = None
        self._dense_meta: list[dict] | None = None

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build_lexical(self, passages: list[PassageForIndex]) -> None:
        if not passages:
            logger.warning("build_lexical called with empty passage list")
            return
        tokenized = [tokenize_text_for_lexical(p.normalized_text) for p in passages]
        self._bm25 = BM25Okapi(tokenized)
        self._bm25_meta = [
            {
                "passage_id": p.passage_id,
                "document_id": p.document_id,
                "section_id": p.section_id,
                "text": p.text,
                "normalized_text": p.normalized_text,
                "passage_index": p.passage_index,
                "section_title": p.section_title,
                "metadata": p.metadata,
            }
            for p in passages
        ]
        logger.info("Built BM25 index with %d passages", len(passages))

    def build_dense(self, passages: list[PassageForIndex], embedder) -> None:
        if not passages:
            logger.warning("build_dense called with empty passage list")
            return
        texts = [p.normalized_text for p in passages]
        vectors = embedder.embed_texts(texts)
        arr = np.array(vectors, dtype=np.float32)
        # L2 normalize for cosine similarity via dot product
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        self._dense_vectors = arr / norms
        self._dense_meta = [
            {
                "passage_id": p.passage_id,
                "document_id": p.document_id,
                "section_id": p.section_id,
                "text": p.text,
                "normalized_text": p.normalized_text,
                "passage_index": p.passage_index,
                "section_title": p.section_title,
                "metadata": p.metadata,
            }
            for p in passages
        ]
        logger.info(
            "Built dense index: %d passages, %d dims",
            len(passages),
            arr.shape[1] if arr.ndim > 1 else 0,
        )

    # ------------------------------------------------------------------
    # Persist
    # ------------------------------------------------------------------

    def save(self) -> None:
        if self._bm25 is not None:
            with open(self.index_dir / "lexical.pkl", "wb") as f:
                pickle.dump({"bm25": self._bm25, "meta": self._bm25_meta}, f)
            logger.info("Saved lexical index to %s", self.index_dir / "lexical.pkl")

        if self._dense_vectors is not None:
            np.save(str(self.index_dir / "dense_vectors.npy"), self._dense_vectors)
            with open(self.index_dir / "dense_meta.json", "w") as f:
                json.dump(self._dense_meta, f)
            logger.info("Saved dense index to %s", self.index_dir)

    def load(self) -> bool:
        """Load existing indices. Returns True if both were loaded."""
        loaded_lexical = self._load_lexical()
        loaded_dense = self._load_dense()
        return loaded_lexical and loaded_dense

    def _load_lexical(self) -> bool:
        path = self.index_dir / "lexical.pkl"
        if not path.exists():
            return False
        with open(path, "rb") as f:
            data = pickle.load(f)
        self._bm25 = data["bm25"]
        self._bm25_meta = data["meta"]
        logger.info("Loaded lexical index from %s (%d passages)", path, len(self._bm25_meta))
        return True

    def _load_dense(self) -> bool:
        vec_path = self.index_dir / "dense_vectors.npy"
        meta_path = self.index_dir / "dense_meta.json"
        if not vec_path.exists() or not meta_path.exists():
            return False
        self._dense_vectors = np.load(str(vec_path))
        with open(meta_path) as f:
            self._dense_meta = json.load(f)
        logger.info(
            "Loaded dense index from %s (%d passages)", vec_path, len(self._dense_meta)
        )
        return True

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_lexical(self, query: str, top_k: int) -> list[dict]:
        """Returns top_k results sorted by BM25 score (descending)."""
        if self._bm25 is None or not self._bm25_meta:
            raise RuntimeError("Lexical index not loaded")
        tokens = tokenize_text_for_lexical(query)
        scores = self._bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for rank, idx in enumerate(top_indices):
            meta = self._bm25_meta[idx]
            results.append({**meta, "score": float(scores[idx]), "rank": rank})
        return results

    def search_dense(self, query_vector: list[float], top_k: int) -> list[dict]:
        """Returns top_k results sorted by cosine similarity (descending)."""
        if self._dense_vectors is None or not self._dense_meta:
            raise RuntimeError("Dense index not loaded")
        q = np.array(query_vector, dtype=np.float32)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm
        sims = self._dense_vectors @ q
        top_indices = np.argsort(sims)[::-1][:top_k]
        results = []
        for rank, idx in enumerate(top_indices):
            meta = self._dense_meta[idx]
            results.append({**meta, "score": float(sims[idx]), "rank": rank})
        return results

    @property
    def has_lexical(self) -> bool:
        return self._bm25 is not None

    @property
    def has_dense(self) -> bool:
        return self._dense_vectors is not None
