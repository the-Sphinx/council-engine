import pytest
from app.ingestion.window_builder import build_windows


def make_passages(n: int) -> list[dict]:
    return [
        {"id": f"p{i}", "passage_index": i, "text": f"Text {i}", "normalized_text": f"text {i}"}
        for i in range(n)
    ]


def test_build_windows_basic():
    passages = make_passages(5)
    windows = build_windows(passages, radius=1)
    assert len(windows) == 5


def test_build_windows_middle_anchor():
    passages = make_passages(5)
    windows = build_windows(passages, radius=1)
    # Passage index 2 should have window [1,2,3]
    w = next(w for w in windows if w.anchor_passage_index == 2)
    assert w.start_passage_index == 1
    assert w.end_passage_index == 3
    assert "p1" in w.included_passage_ids
    assert "p2" in w.included_passage_ids
    assert "p3" in w.included_passage_ids


def test_build_windows_boundary_start():
    passages = make_passages(5)
    windows = build_windows(passages, radius=1)
    w = next(w for w in windows if w.anchor_passage_index == 0)
    # Can't go before index 0
    assert w.start_passage_index == 0
    assert w.end_passage_index == 1


def test_build_windows_boundary_end():
    passages = make_passages(5)
    windows = build_windows(passages, radius=1)
    w = next(w for w in windows if w.anchor_passage_index == 4)
    assert w.start_passage_index == 3
    assert w.end_passage_index == 4


def test_build_windows_empty():
    windows = build_windows([], radius=1)
    assert windows == []


def test_build_windows_single():
    passages = make_passages(1)
    windows = build_windows(passages, radius=1)
    assert len(windows) == 1
    assert windows[0].text == "Text 0"


def test_build_windows_radius_2():
    passages = make_passages(10)
    windows = build_windows(passages, radius=2)
    w = next(w for w in windows if w.anchor_passage_index == 5)
    assert w.start_passage_index == 3
    assert w.end_passage_index == 7
    assert len(w.included_passage_ids) == 5
