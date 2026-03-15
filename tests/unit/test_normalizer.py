import pytest
from app.ingestion.normalizer import normalize_text, normalize_query


def test_normalize_text_basic():
    result = normalize_text("  hello   world  ")
    assert result == "hello world"


def test_normalize_text_line_endings():
    result = normalize_text("line1\r\nline2\rline3")
    assert result == "line1\nline2\nline3"


def test_normalize_text_multiple_blank_lines():
    result = normalize_text("a\n\n\n\nb")
    assert result == "a\n\nb"


def test_normalize_text_unicode_nfc():
    # Composed vs decomposed 'é'
    decomposed = "e\u0301"
    composed = "\xe9"
    result = normalize_text(decomposed)
    assert result == composed


def test_normalize_query_strips_whitespace():
    result = normalize_query("  What is patience?  ")
    assert result == "What is patience?"


def test_normalize_query_collapses_spaces():
    result = normalize_query("What   is   this?")
    assert result == "What is this?"


def test_normalize_text_preserves_punctuation():
    text = "Hello, world! How are you?"
    result = normalize_text(text)
    assert result == "Hello, world! How are you?"
