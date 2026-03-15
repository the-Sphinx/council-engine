"""
Sectioning strategies:
- ExplicitBoundarySectioner: sections defined by a JSON manifest (char offsets)
- HeadingBasedSectioner: detects headings by regex patterns
- ParagraphFallbackSectioner: treats each paragraph block as a section
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class SectionBoundary:
    title: Optional[str]
    section_type: str
    order_index: int
    start_offset: int
    end_offset: int
    metadata: dict


class ExplicitBoundarySectioner:
    """
    Uses a pre-built list of section boundaries (e.g., from quran_sections.json).
    Each boundary: {title, start_offset, end_offset, section_type?, metadata?}
    """

    def __init__(self, boundaries: list[dict]):
        self._boundaries = boundaries

    def section(self, text: str) -> list[SectionBoundary]:
        results = []
        for i, b in enumerate(self._boundaries):
            start = b["start_offset"]
            end = b["end_offset"]
            # Clamp to text length
            end = min(end, len(text))
            if start >= len(text):
                continue
            results.append(
                SectionBoundary(
                    title=b.get("title"),
                    section_type=b.get("section_type", "chapter"),
                    order_index=i,
                    start_offset=start,
                    end_offset=end,
                    metadata=b.get("metadata", {}),
                )
            )
        return results


class HeadingBasedSectioner:
    """
    Splits on lines that look like headings (all-caps, or markdown #, or numbered).
    """

    HEADING_PATTERN = re.compile(
        r"^(#{1,4}\s+.+|[A-Z][A-Z\s\d:,.-]{3,}|^\d+[\.\)]\s+.{3,})$",
        re.MULTILINE,
    )

    def section(self, text: str) -> list[SectionBoundary]:
        matches = list(self.HEADING_PATTERN.finditer(text))
        if not matches:
            return [
                SectionBoundary(
                    title=None,
                    section_type="document",
                    order_index=0,
                    start_offset=0,
                    end_offset=len(text),
                    metadata={},
                )
            ]

        boundaries = []
        for i, m in enumerate(matches):
            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            boundaries.append(
                SectionBoundary(
                    title=m.group(0).strip(),
                    section_type="heading",
                    order_index=i,
                    start_offset=start,
                    end_offset=end,
                    metadata={},
                )
            )
        return boundaries


class ParagraphFallbackSectioner:
    """
    Each double-newline-delimited paragraph block becomes a section.
    Groups up to `max_paragraphs_per_section` paragraphs to avoid tiny sections.
    """

    def __init__(self, max_paragraphs_per_section: int = 10):
        self.max_per_section = max_paragraphs_per_section

    def section(self, text: str) -> list[SectionBoundary]:
        # Split on blank lines
        paragraph_pattern = re.compile(r"\n{2,}")
        parts = paragraph_pattern.split(text)

        boundaries = []
        order = 0
        i = 0
        pos = 0
        while i < len(parts):
            chunk_parts = parts[i : i + self.max_per_section]
            chunk = "\n\n".join(chunk_parts)
            start = text.find(chunk, pos)
            if start == -1:
                start = pos
            end = start + len(chunk)
            boundaries.append(
                SectionBoundary(
                    title=None,
                    section_type="paragraph_group",
                    order_index=order,
                    start_offset=start,
                    end_offset=end,
                    metadata={},
                )
            )
            pos = end
            order += 1
            i += self.max_per_section

        if not boundaries:
            boundaries.append(
                SectionBoundary(
                    title=None,
                    section_type="document",
                    order_index=0,
                    start_offset=0,
                    end_offset=len(text),
                    metadata={},
                )
            )
        return boundaries


def get_sectioner(
    strategy: str,
    boundaries: list[dict] | None = None,
    max_paragraphs_per_section: int = 10,
):
    if strategy == "explicit" and boundaries is not None:
        return ExplicitBoundarySectioner(boundaries)
    elif strategy == "heading":
        return HeadingBasedSectioner()
    else:
        return ParagraphFallbackSectioner(max_paragraphs_per_section)
