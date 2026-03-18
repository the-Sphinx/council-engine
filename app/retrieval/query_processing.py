from __future__ import annotations

import re
from dataclasses import dataclass


_STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "according",
    "anything",
    "associated",
    "be",
    "by",
    "can",
    "concept",
    "describe",
    "does",
    "given",
    "how",
    "is",
    "say",
    "should",
    "text",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "to",
    "together",
    "what",
    "which",
    "with",
}


@dataclass
class LexicalQueryDebug:
    original_query: str
    normalized_query: str
    normalized_tokens: list[str]
    expanded_terms: list[str]
    lexical_query: str


def tokenize_text_for_lexical(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    raw_tokens = [token for token in cleaned.split() if token]
    tokens: list[str] = []
    for token in raw_tokens:
        stemmed = _light_stem(token)
        if stemmed and stemmed not in _STOPWORDS:
            tokens.append(stemmed)
    return tokens


def build_lexical_query(
    question: str,
    normalized_query: str,
    expansions: dict[str, list[str]] | None = None,
    expansion_enabled: bool = True,
) -> LexicalQueryDebug:
    base_tokens = tokenize_text_for_lexical(normalized_query)
    expanded_terms: list[str] = []
    if expansion_enabled:
        expansions = expansions or {}
        for token in list(base_tokens):
            for extra in expansions.get(token, []):
                expanded = _light_stem(extra.lower())
                if expanded and expanded not in base_tokens and expanded not in expanded_terms:
                    expanded_terms.append(expanded)

    all_tokens = list(dict.fromkeys(base_tokens + expanded_terms))
    return LexicalQueryDebug(
        original_query=question,
        normalized_query=normalized_query,
        normalized_tokens=base_tokens,
        expanded_terms=expanded_terms,
        lexical_query=" ".join(all_tokens),
    )


def _light_stem(token: str) -> str:
    if len(token) <= 3:
        return token
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "y"
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if (
        len(token) > 4
        and token.endswith("es")
        and (
            token.endswith("ches")
            or token.endswith("shes")
            or token.endswith("xes")
            or token.endswith("zes")
            or token.endswith("sses")
        )
    ):
        return token[:-2]
    if token.endswith("s") and len(token) > 4 and not token.endswith("ss") and not token.endswith("ses"):
        return token[:-1]
    return token
