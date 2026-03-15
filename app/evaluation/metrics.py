"""Retrieval evaluation metrics."""

from __future__ import annotations


def hit_at_k(
    retrieved_ids: list[str],
    expected_ids: set[str],
    k: int,
) -> float:
    """1 if any expected passage appears in top-k, else 0."""
    return float(bool(set(retrieved_ids[:k]) & expected_ids))


def recall_at_k(
    retrieved_ids: list[str],
    expected_ids: set[str],
    k: int,
) -> float:
    """Fraction of expected passages found in top-k."""
    if not expected_ids:
        return 1.0
    hits = set(retrieved_ids[:k]) & expected_ids
    return len(hits) / len(expected_ids)


def precision_at_k(
    retrieved_ids: list[str],
    expected_ids: set[str],
    k: int,
) -> float:
    """Fraction of top-k retrieved passages that are relevant."""
    if k == 0:
        return 0.0
    top_k = retrieved_ids[:k]
    hits = [pid for pid in top_k if pid in expected_ids]
    return len(hits) / k


def mrr(
    retrieved_ids: list[str],
    expected_ids: set[str],
) -> float:
    """Mean Reciprocal Rank — reciprocal of rank of first relevant result."""
    for rank, pid in enumerate(retrieved_ids, start=1):
        if pid in expected_ids:
            return 1.0 / rank
    return 0.0


def compute_retrieval_metrics(
    retrieved_ids: list[str],
    expected_ids: set[str],
    alternative_ids: set[str] | None = None,
    ks: list[int] = (5, 10, 20),
) -> dict:
    all_relevant = expected_ids | (alternative_ids or set())
    metrics: dict = {}
    for k in ks:
        metrics[f"hit@{k}"] = hit_at_k(retrieved_ids, all_relevant, k)
        metrics[f"recall@{k}"] = recall_at_k(retrieved_ids, all_relevant, k)
        metrics[f"precision@{k}"] = precision_at_k(retrieved_ids, all_relevant, k)
    metrics["mrr"] = mrr(retrieved_ids, all_relevant)
    return metrics
