"""
PassageWindow builder.

Creates context windows around anchor passages using their neighbors.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WindowSpec:
    anchor_passage_id: str
    anchor_passage_index: int
    start_passage_index: int
    end_passage_index: int
    included_passage_ids: list[str]
    text: str
    normalized_text: str


def build_windows(
    passages: list[dict],
    radius: int = 1,
) -> list[WindowSpec]:
    """
    Build context windows for every passage in `passages`.

    Each passage dict must have:
        id, passage_index, text, normalized_text

    For radius=1 we create a window spanning [index-1, index+1].
    Only one window per anchor (the largest window that fits within radius).
    Boundaries are clamped to available passages.
    """
    if not passages:
        return []

    # Build lookup by passage_index
    by_index: dict[int, dict] = {p["passage_index"]: p for p in passages}
    indices = sorted(by_index.keys())

    windows = []
    for p in passages:
        anchor_idx = p["passage_index"]
        start_idx = max(anchor_idx - radius, indices[0])
        end_idx = min(anchor_idx + radius, indices[-1])

        # Gather all passages in [start_idx, end_idx] that exist
        included = [
            by_index[i]
            for i in range(start_idx, end_idx + 1)
            if i in by_index
        ]

        window_text = " ".join(inc["text"] for inc in included)
        window_normalized = " ".join(inc["normalized_text"] for inc in included)
        included_ids = [inc["id"] for inc in included]

        windows.append(
            WindowSpec(
                anchor_passage_id=p["id"],
                anchor_passage_index=anchor_idx,
                start_passage_index=start_idx,
                end_passage_index=end_idx,
                included_passage_ids=included_ids,
                text=window_text,
                normalized_text=window_normalized,
            )
        )
    return windows
