"""
Quran-specific corpus manifest builder.

This is the ONLY Quran-specific file in the codebase.
It reads sahih_international.txt (line-per-ayah) and quran_sections.json
(114 surah boundaries with char offsets) and returns a generic CorpusManifest.

Expected format of sahih_international.txt:
    1|1|In the name of Allah, the Entirely Merciful, the Especially Merciful.
    1|2|Praise be to Allah, Lord of the worlds —
    ...
    where each line is: surah_number|ayah_number|text

quran_sections.json is a list of:
    {"surah": 1, "title": "Al-Fatihah", "start_offset": 0, "end_offset": 123}
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.ingestion.loaders import CorpusManifest


QURAN_DATA_DIR = Path("data/corpora/quran_en")
RAW_TEXT_FILE = QURAN_DATA_DIR / "sahih_international.txt"
SECTIONS_FILE = QURAN_DATA_DIR / "quran_sections.json"


def build_quran_manifest() -> CorpusManifest:
    """
    Build a CorpusManifest for the Quran Sahih International translation.
    Returns a generic manifest using generic concepts (section/passage).
    """
    if not RAW_TEXT_FILE.exists():
        raise FileNotFoundError(
            f"Quran corpus not found at {RAW_TEXT_FILE}. "
            "Run scripts/download_quran.py to download it."
        )

    section_boundaries: list[dict] | None = None
    if SECTIONS_FILE.exists():
        with open(SECTIONS_FILE) as f:
            section_boundaries = json.load(f)

    return CorpusManifest(
        title="Quran (Sahih International)",
        source_type="predefined_corpus",
        language="en",
        raw_text_path=RAW_TEXT_FILE,
        sectioning_strategy="explicit" if section_boundaries else "paragraph",
        passage_strategy="natural_units",
        section_boundaries=section_boundaries,
        metadata={
            "translator": "Sahih International",
            "source": "tanzil.net",
            "corpus": "quran",
        },
    )


def build_quran_sections_json(raw_text_path: Path, output_path: Path) -> None:
    """
    Parse sahih_international.txt and build quran_sections.json with char offsets.

    The text format is: surah|ayah|text\\n
    We compute byte-accurate char offsets for each surah.
    """
    raw = raw_text_path.read_text(encoding="utf-8")
    lines = raw.split("\n")

    # Surah metadata (name, English meaning, number of ayahs)
    surah_names = _get_surah_names()

    surah_offsets: dict[int, dict] = {}
    pos = 0
    for line in lines:
        if "|" in line:
            parts = line.split("|", 2)
            if len(parts) >= 3:
                try:
                    surah_num = int(parts[0])
                except ValueError:
                    pos += len(line) + 1
                    continue
                if surah_num not in surah_offsets:
                    surah_offsets[surah_num] = {"start": pos, "end": pos + len(line) + 1}
                else:
                    surah_offsets[surah_num]["end"] = pos + len(line) + 1
        pos += len(line) + 1

    sections = []
    for surah_num in sorted(surah_offsets.keys()):
        offsets = surah_offsets[surah_num]
        sections.append(
            {
                "surah": surah_num,
                "title": surah_names.get(surah_num, f"Surah {surah_num}"),
                "section_type": "chapter",
                "order_index": surah_num - 1,
                "start_offset": offsets["start"],
                "end_offset": offsets["end"],
                "metadata": {"surah_number": surah_num},
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)

    print(f"Built {len(sections)} surah sections → {output_path}")


def _get_surah_names() -> dict[int, str]:
    return {
        1: "Al-Fatihah", 2: "Al-Baqarah", 3: "Ali 'Imran", 4: "An-Nisa'",
        5: "Al-Ma'idah", 6: "Al-An'am", 7: "Al-A'raf", 8: "Al-Anfal",
        9: "At-Tawbah", 10: "Yunus", 11: "Hud", 12: "Yusuf",
        13: "Ar-Ra'd", 14: "Ibrahim", 15: "Al-Hijr", 16: "An-Nahl",
        17: "Al-Isra'", 18: "Al-Kahf", 19: "Maryam", 20: "Ta-Ha",
        21: "Al-Anbya'", 22: "Al-Hajj", 23: "Al-Mu'minun", 24: "An-Nur",
        25: "Al-Furqan", 26: "Ash-Shu'ara'", 27: "An-Naml", 28: "Al-Qasas",
        29: "Al-'Ankabut", 30: "Ar-Rum", 31: "Luqman", 32: "As-Sajdah",
        33: "Al-Ahzab", 34: "Saba'", 35: "Fatir", 36: "Ya-Sin",
        37: "As-Saffat", 38: "Sad", 39: "Az-Zumar", 40: "Ghafir",
        41: "Fussilat", 42: "Ash-Shura", 43: "Az-Zukhruf", 44: "Ad-Dukhan",
        45: "Al-Jathiyah", 46: "Al-Ahqaf", 47: "Muhammad", 48: "Al-Fath",
        49: "Al-Hujurat", 50: "Qaf", 51: "Adh-Dhariyat", 52: "At-Tur",
        53: "An-Najm", 54: "Al-Qamar", 55: "Ar-Rahman", 56: "Al-Waqi'ah",
        57: "Al-Hadid", 58: "Al-Mujadila", 59: "Al-Hashr", 60: "Al-Mumtahanah",
        61: "As-Saf", 62: "Al-Jumu'ah", 63: "Al-Munafiqun", 64: "At-Taghabun",
        65: "At-Talaq", 66: "At-Tahrim", 67: "Al-Mulk", 68: "Al-Qalam",
        69: "Al-Haqqah", 70: "Al-Ma'arij", 71: "Nuh", 72: "Al-Jinn",
        73: "Al-Muzzammil", 74: "Al-Muddaththir", 75: "Al-Qiyamah", 76: "Al-Insan",
        77: "Al-Mursalat", 78: "An-Naba'", 79: "An-Nazi'at", 80: "'Abasa",
        81: "At-Takwir", 82: "Al-Infitar", 83: "Al-Mutaffifin", 84: "Al-Inshiqaq",
        85: "Al-Buruj", 86: "At-Tariq", 87: "Al-A'la", 88: "Al-Ghashiyah",
        89: "Al-Fajr", 90: "Al-Balad", 91: "Ash-Shams", 92: "Al-Layl",
        93: "Ad-Duha", 94: "Ash-Sharh", 95: "At-Tin", 96: "Al-'Alaq",
        97: "Al-Qadr", 98: "Al-Bayyinah", 99: "Az-Zalzalah", 100: "Al-'Adiyat",
        101: "Al-Qari'ah", 102: "At-Takathur", 103: "Al-'Asr", 104: "Al-Humazah",
        105: "Al-Fil", 106: "Quraysh", 107: "Al-Ma'un", 108: "Al-Kawthar",
        109: "Al-Kafirun", 110: "An-Nasr", 111: "Al-Masad", 112: "Al-Ikhlas",
        113: "Al-Falaq", 114: "An-Nas",
    }
