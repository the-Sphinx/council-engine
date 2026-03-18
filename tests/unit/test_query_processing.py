from __future__ import annotations

from app.retrieval.query_processing import build_lexical_query, tokenize_text_for_lexical


def test_tokenize_text_for_lexical_normalizes_lightly_without_erasing_keywords():
    tokens = tokenize_text_for_lexical("What do prayers, fasting, and charities say?")

    assert "prayer" in tokens
    assert "fast" in tokens
    assert "charity" in tokens
    assert "what" not in tokens


def test_build_lexical_query_adds_configured_expansions():
    debug = build_lexical_query(
        question="What does the text say about mercy?",
        normalized_query="What does the text say about mercy?",
        expansions={"mercy": ["compassion", "forgiveness"]},
        expansion_enabled=True,
    )

    assert debug.original_query == "What does the text say about mercy?"
    assert debug.normalized_tokens == ["mercy"]
    assert debug.expanded_terms == ["compassion", "forgiveness"]
    assert debug.lexical_query == "mercy compassion forgiveness"


def test_build_lexical_query_can_disable_expansion():
    debug = build_lexical_query(
        question="What does the text say about mercy?",
        normalized_query="What does the text say about mercy?",
        expansions={"mercy": ["compassion", "forgiveness"]},
        expansion_enabled=False,
    )

    assert debug.expanded_terms == []
    assert debug.lexical_query == "mercy"


def test_tokenize_text_for_lexical_keeps_names_like_moses_intact():
    assert tokenize_text_for_lexical("What does the text say about Moses?") == ["moses"]
