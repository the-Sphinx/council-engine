from __future__ import annotations

from scripts.run_model_eval import _classify_failure, _verse_prefix


def test_verse_prefix_extracts_quran_reference():
    assert _verse_prefix("2|183|O you who have believed...") == "2|183"
    assert _verse_prefix("not a verse") is None


def test_classify_failure_lexical_miss():
    failure = _classify_failure(
        expected_ids={"p1"},
        lexical_ids=["p2", "p3"],
        dense_ids=["p1", "p4"],
        merged_ids=["p1", "p4"],
        reranked_ids=["p4", "p5"],
    )
    assert failure == "lexical_miss"


def test_classify_failure_dense_miss():
    failure = _classify_failure(
        expected_ids={"p1"},
        lexical_ids=["p1", "p2"],
        dense_ids=["p3", "p4"],
        merged_ids=["p1", "p3"],
        reranked_ids=["p3", "p4"],
    )
    assert failure == "dense_miss"


def test_classify_failure_rerank_miss():
    failure = _classify_failure(
        expected_ids={"p1"},
        lexical_ids=["p1", "p2"],
        dense_ids=["p1", "p3"],
        merged_ids=["p1", "p2", "p3"],
        reranked_ids=["p2", "p3"],
    )
    assert failure == "rerank_miss"
