import re
import unicodedata


def normalize_text(text: str) -> str:
    """
    Deterministic text normalization:
    - NFC unicode normalization
    - Collapse internal whitespace (multiple spaces/tabs -> single space)
    - Normalize line endings (\\r\\n and \\r -> \\n)
    - Strip leading/trailing whitespace per line
    - Collapse 3+ consecutive blank lines to 2
    - Strip overall leading/trailing whitespace
    """
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_query(text: str) -> str:
    """
    Light normalization for a user query — preserves question punctuation.
    """
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
