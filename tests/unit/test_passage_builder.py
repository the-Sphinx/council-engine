import pytest
from app.ingestion.passage_builder import build_passages


SAMPLE = """Line one text.
Line two text.
Line three text.
Line four text."""


def test_natural_units_basic():
    passages = build_passages(SAMPLE, section_start_offset=0, strategy="natural_units")
    assert len(passages) == 4
    assert passages[0].text == "Line one text."
    assert passages[-1].text == "Line four text."


def test_natural_units_offsets():
    passages = build_passages(SAMPLE, section_start_offset=0, strategy="natural_units")
    for p in passages:
        assert p.start_offset < p.end_offset
        # The text at that offset should contain the passage text
        assert SAMPLE[p.start_offset:p.end_offset].strip() == p.text


def test_natural_units_with_offset():
    offset = 100
    passages = build_passages(SAMPLE, section_start_offset=offset, strategy="natural_units")
    assert passages[0].start_offset >= offset


def test_natural_units_skips_empty_lines():
    text = "Line one.\n\nLine two."
    passages = build_passages(text, section_start_offset=0, strategy="natural_units")
    texts = [p.text for p in passages]
    assert "Line one." in texts
    assert "Line two." in texts
    assert "" not in texts


def test_paragraph_strategy():
    text = "Para one.\n\nPara two."
    passages = build_passages(text, section_start_offset=0, strategy="paragraph")
    assert len(passages) >= 1


def test_sentence_group_strategy():
    text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    passages = build_passages(text, section_start_offset=0, strategy="sentence_group", group_size=2)
    assert len(passages) >= 2
