import pytest
from app.core.interfaces import RetrievalCandidate
from app.retrieval.hybrid import compute_hybrid_scores, merge_candidates, normalize_scores


def make_candidate(pid, lex=None, dense=None):
    c = RetrievalCandidate(
        passage_id=pid,
        document_id="doc1",
        section_id=None,
        passage_text=f"text {pid}",
        normalized_text=f"text {pid}",
        lexical_score=lex,
        dense_score=dense,
    )
    if lex is not None:
        c.source_methods.append("bm25")
    if dense is not None:
        c.source_methods.append("dense")
    return c


def test_merge_candidates_union():
    lex = [make_candidate("p1", lex=0.9), make_candidate("p2", lex=0.7)]
    dense = [make_candidate("p2", dense=0.8), make_candidate("p3", dense=0.6)]
    merged = merge_candidates(lex, dense)
    ids = {c.passage_id for c in merged}
    assert ids == {"p1", "p2", "p3"}


def test_merge_candidates_preserves_both_scores():
    lex = [make_candidate("p1", lex=0.9)]
    dense = [make_candidate("p1", dense=0.7)]
    merged = merge_candidates(lex, dense)
    assert len(merged) == 1
    assert merged[0].lexical_score == 0.9
    assert merged[0].dense_score == 0.7


def test_normalize_scores_minmax():
    candidates = [
        make_candidate("p1", lex=10.0),
        make_candidate("p2", lex=5.0),
        make_candidate("p3", lex=0.0),
    ]
    normalize_scores(candidates, "lexical")
    scores = [c.lexical_score_normalized for c in candidates]
    assert max(scores) == pytest.approx(1.0)
    assert min(scores) == pytest.approx(0.0)
    assert [c.lexical_score for c in candidates] == [10.0, 5.0, 0.0]


def test_normalize_scores_all_equal():
    candidates = [make_candidate("p1", lex=5.0), make_candidate("p2", lex=5.0)]
    normalize_scores(candidates, "lexical")
    # All equal => rng=0, all become 0.0
    assert all(c.lexical_score_normalized == 0.0 for c in candidates)


def test_compute_hybrid_scores_range():
    candidates = [
        make_candidate("p1", lex=1.0, dense=1.0),
        make_candidate("p2", lex=0.5, dense=0.5),
        make_candidate("p3", lex=0.0, dense=0.0),
    ]
    normalize_scores(candidates, "lexical")
    normalize_scores(candidates, "dense")
    result = compute_hybrid_scores(candidates, alpha=0.5, beta=0.5)
    for c in result:
        assert 0.0 <= c.hybrid_score <= 1.0


def test_compute_hybrid_scores_sorted_descending():
    candidates = [
        make_candidate("p1", lex=0.3, dense=0.3),
        make_candidate("p2", lex=0.9, dense=0.9),
    ]
    normalize_scores(candidates, "lexical")
    normalize_scores(candidates, "dense")
    result = compute_hybrid_scores(candidates)
    assert result[0].passage_id == "p2"


def test_compute_hybrid_scores_alpha_beta_weights():
    c1 = make_candidate("p1", lex=1.0, dense=0.0)
    c2 = make_candidate("p2", lex=0.0, dense=1.0)
    candidates = [c1, c2]
    normalize_scores(candidates, "lexical")
    normalize_scores(candidates, "dense")
    result = compute_hybrid_scores(candidates, alpha=0.8, beta=0.2)
    # p1 should score higher with alpha=0.8
    assert result[0].passage_id == "p1"


def test_compute_hybrid_scores_applies_overlap_boost():
    overlap = make_candidate("p1", lex=1.0, dense=1.0)
    lexical_only = make_candidate("p2", lex=1.0, dense=None)
    candidates = [overlap, lexical_only]
    normalize_scores(candidates, "lexical")
    normalize_scores(candidates, "dense")

    result = compute_hybrid_scores(
        candidates,
        alpha=0.5,
        beta=0.5,
        overlap_boost_enabled=True,
        overlap_boost_value=0.1,
    )

    assert result[0].passage_id == "p1"
    assert result[0].overlap_matched is True
    assert result[0].overlap_boost == pytest.approx(0.1)
