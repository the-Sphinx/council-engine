"""
Text corpus loaders.

TextLoader: reads a plain text file.
CorpusManifest: describes a corpus ready for ingestion.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class CorpusManifest:
    """Describes a corpus ready for ingestion."""
    title: str
    source_type: str  # "uploaded_text" | "predefined_corpus"
    language: str
    raw_text_path: Path
    sectioning_strategy: str  # "explicit" | "heading" | "paragraph"
    passage_strategy: str     # "natural_units" | "paragraph" | "sentence_group"
    section_boundaries: Optional[list[dict]] = None  # for explicit strategy
    metadata: dict = field(default_factory=dict)


class TextLoader:
    """Loads a plain text corpus from disk."""

    def load(self, path: Path) -> str:
        if not path.exists():
            raise FileNotFoundError(f"Corpus file not found: {path}")
        return path.read_text(encoding="utf-8")
