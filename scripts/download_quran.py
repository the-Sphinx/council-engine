#!/usr/bin/env python3
"""
Download Sahih International Quran translation from tanzil.net and build section offsets.

Usage:
    python scripts/download_quran.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

TANZIL_URL = "https://tanzil.net/trans/en.sahih"
DATA_DIR = Path("data/corpora/quran_en")
OUTPUT_FILE = DATA_DIR / "sahih_international.txt"
SECTIONS_FILE = DATA_DIR / "quran_sections.json"


def download():
    import httpx

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading Quran (Sahih International) from {TANZIL_URL}...")
    try:
        resp = httpx.get(TANZIL_URL, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
        text = resp.text
    except Exception as e:
        print(f"Download failed: {e}")
        print("Trying alternative source...")
        text = _try_alternative()

    if not text:
        print("ERROR: Could not download Quran corpus")
        sys.exit(1)

    OUTPUT_FILE.write_text(text, encoding="utf-8")
    print(f"Saved to {OUTPUT_FILE} ({len(text)} chars, {len(text.splitlines())} lines)")


def _try_alternative() -> str:
    """Try to get from a known reliable source."""
    import httpx
    # tanzil.net direct download URL
    url = "https://tanzil.net/trans/?transID=en.sahih&type=txt"
    try:
        resp = httpx.get(url, timeout=60.0, follow_redirects=True)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"Alternative also failed: {e}")
        return ""


def build_sections():
    if not OUTPUT_FILE.exists():
        print(f"ERROR: {OUTPUT_FILE} not found. Run download first.")
        sys.exit(1)

    from app.ingestion.corpus.quran_loader import build_quran_sections_json
    build_quran_sections_json(OUTPUT_FILE, SECTIONS_FILE)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--sections-only", action="store_true")
    args = parser.parse_args()

    if not args.sections_only:
        download()
    build_sections()
    print("Done.")
