"""
Passage builder strategies.

Each strategy turns a section's text into a list of atomic passage dicts:
    {text, start_offset, end_offset}

All offsets are absolute (relative to the full document text).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class RawPassage:
    text: str
    start_offset: int
    end_offset: int


def _natural_units(section_text: str, section_start: int) -> list[RawPassage]:
    """
    One passage per non-empty line.
    Ideal for line-per-unit corpora like the Quran (one ayah per line).
    """
    passages = []
    pos = 0
    for line in section_text.split("\n"):
        line_start = section_start + pos
        line_end = line_start + len(line)
        if line.strip():
            passages.append(RawPassage(text=line.strip(), start_offset=line_start, end_offset=line_end))
        pos += len(line) + 1  # +1 for \n
    return passages


def _paragraph_units(section_text: str, section_start: int) -> list[RawPassage]:
    """One passage per double-newline paragraph."""
    passages = []
    # find all paragraph blocks
    for m in re.finditer(r"(?:(?!\n\n).)+", section_text, re.DOTALL):
        chunk = m.group(0).strip()
        if not chunk:
            continue
        abs_start = section_start + m.start()
        abs_end = section_start + m.end()
        passages.append(RawPassage(text=chunk, start_offset=abs_start, end_offset=abs_end))
    return passages


def _sentence_group_units(
    section_text: str, section_start: int, group_size: int = 3
) -> list[RawPassage]:
    """
    Groups sentences into passage-sized units of `group_size` sentences each.
    """
    sentence_re = re.compile(r"(?<=[.!?])\s+")
    sentences = sentence_re.split(section_text.strip())
    passages = []
    pos = 0
    i = 0
    while i < len(sentences):
        group = sentences[i : i + group_size]
        chunk = " ".join(group)
        abs_start = section_start + section_text.find(chunk, pos)
        if abs_start < section_start:
            abs_start = section_start + pos
        abs_end = abs_start + len(chunk)
        passages.append(
            RawPassage(text=chunk, start_offset=abs_start, end_offset=abs_end)
        )
        pos = abs_end - section_start
        i += group_size
    return passages


def build_passages(
    section_text: str,
    section_start_offset: int,
    strategy: str = "natural_units",
    group_size: int = 3,
) -> list[RawPassage]:
    """
    Build passages from a section's text using the given strategy.

    Args:
        section_text: The text of the section.
        section_start_offset: Absolute char offset of section start in parent document.
        strategy: One of "natural_units", "paragraph", "sentence_group".
        group_size: For sentence_group, how many sentences per passage.
    """
    if strategy == "natural_units":
        return _natural_units(section_text, section_start_offset)
    elif strategy == "paragraph":
        return _paragraph_units(section_text, section_start_offset)
    elif strategy == "sentence_group":
        return _sentence_group_units(section_text, section_start_offset, group_size)
    else:
        raise ValueError(f"Unknown passage strategy: {strategy!r}")
