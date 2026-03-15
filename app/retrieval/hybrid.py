"""
Hybrid score fusion: merge lexical + dense candidates, normalize, compute hybrid score.
"""

from __future__ import annotations

from app.core.interfaces import RetrievalCandidate


def merge_candidates(
    lexical: list[RetrievalCandidate],
    dense: list[RetrievalCandidate],
) -> list[RetrievalCandidate]:
    """
    Union by passage_id. Preserve both scores.
    If a passage appears in both, merge into a single candidate.
    """
    by_id: dict[str, RetrievalCandidate] = {}

    for c in lexical:
        by_id[c.passage_id] = c

    for c in dense:
        if c.passage_id in by_id:
            existing = by_id[c.passage_id]
            existing.dense_score = c.dense_score
            existing.rank_dense = c.rank_dense
            if "dense" not in existing.source_methods:
                existing.source_methods.append("dense")
        else:
            by_id[c.passage_id] = c

    return list(by_id.values())


def normalize_scores(
    candidates: list[RetrievalCandidate],
    method: str,
) -> list[RetrievalCandidate]:
    """
    Min-max normalize scores for a given method ("lexical" or "dense").
    Operates in-place on the candidates.
    """
    score_attr = f"{method}_score"
    norm_attr = f"{method}_score"  # we overwrite in the candidate

    scores = [getattr(c, score_attr) for c in candidates if getattr(c, score_attr) is not None]
    if not scores:
        return candidates

    min_s = min(scores)
    max_s = max(scores)
    rng = max_s - min_s

    for c in candidates:
        raw = getattr(c, score_attr)
        if raw is not None:
            normalized = (raw - min_s) / rng if rng > 0 else 0.0
            setattr(c, score_attr, normalized)

    return candidates


def compute_hybrid_scores(
    candidates: list[RetrievalCandidate],
    alpha: float = 0.5,
    beta: float = 0.5,
) -> list[RetrievalCandidate]:
    """
    hybrid_score = alpha * lexical_score + beta * dense_score
    Missing scores count as 0.
    Sorts descending by hybrid_score and sets rank_hybrid.
    """
    for c in candidates:
        lex = c.lexical_score or 0.0
        den = c.dense_score or 0.0
        c.hybrid_score = alpha * lex + beta * den

    candidates.sort(key=lambda c: c.hybrid_score or 0.0, reverse=True)
    for rank, c in enumerate(candidates):
        c.rank_hybrid = rank
    return candidates
