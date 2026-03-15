"""Eval dataset schema and loader."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class EvalItem:
    id: str
    question: str
    mode: str
    expected_relevant_passage_ids: list[str]
    acceptable_alternative_passage_ids: list[str]
    minimum_expected_count: int
    ambiguity_flag: bool
    notes: str
    category: str = "direct_lookup"


def load_eval_dataset(path: Path) -> list[EvalItem]:
    with open(path) as f:
        data = json.load(f)
    items = []
    for d in data:
        items.append(
            EvalItem(
                id=d["id"],
                question=d["question"],
                mode=d.get("mode", "source_only"),
                expected_relevant_passage_ids=d.get("expected_relevant_passage_ids", []),
                acceptable_alternative_passage_ids=d.get("acceptable_alternative_passage_ids", []),
                minimum_expected_count=d.get("minimum_expected_count", 1),
                ambiguity_flag=d.get("ambiguity_flag", False),
                notes=d.get("notes", ""),
                category=d.get("category", "direct_lookup"),
            )
        )
    return items
