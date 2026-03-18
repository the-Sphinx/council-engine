"""
Abstract base classes and shared DTOs.

No imports from other app modules (prevents circular deps).
All interfaces operate on plain Python data objects defined here.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Shared DTOs
# ---------------------------------------------------------------------------


@dataclass
class PassageForIndex:
    passage_id: str
    document_id: str
    section_id: Optional[str]
    text: str
    normalized_text: str
    passage_index: int
    section_title: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalCandidate:
    passage_id: str
    document_id: str
    section_id: Optional[str]
    passage_text: str
    normalized_text: str
    lexical_score: Optional[float] = None
    dense_score: Optional[float] = None
    lexical_score_normalized: Optional[float] = None
    dense_score_normalized: Optional[float] = None
    hybrid_score: Optional[float] = None
    rerank_score: Optional[float] = None
    overlap_matched: bool = False
    overlap_boost: float = 0.0
    source_methods: list[str] = field(default_factory=list)
    rank_lexical: Optional[int] = None
    rank_dense: Optional[int] = None
    rank_hybrid: Optional[int] = None
    rank_rerank: Optional[int] = None
    metadata: dict = field(default_factory=dict)


@dataclass
class AnchorPassage:
    passage_id: str
    text: str
    rank: int
    scores: dict[str, float]
    section_title: Optional[str]
    section_order_index: Optional[int]
    window_passage_ids: list[str]
    window_text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class EvidenceBundleDomain:
    query_id: str
    mode: str
    anchors: list[AnchorPassage]
    bundle_id: Optional[str] = None


@dataclass
class ClaimDomain:
    claim_id: str
    statement: str
    supporting_passage_ids: list[str]
    support_type: str  # "direct" | "interpretive"


@dataclass
class CitationDomain:
    passage_id: str
    quote: str


@dataclass
class ObjectionDomain:
    issue: str
    related_passage_ids: list[str]


@dataclass
class AnswerDraftDomain:
    final_answer: str
    claims: list[ClaimDomain]
    supporting_citations: list[CitationDomain]
    objections_raised: list[ObjectionDomain]
    confidence_notes: str
    draft_id: Optional[str] = None


@dataclass
class UnsupportedClaimDomain:
    claim_id: str
    reason: str


@dataclass
class CitationIssueDomain:
    passage_id: str
    issue: str


@dataclass
class VerificationReportDomain:
    status: str  # "pass" | "pass_with_warnings" | "fail"
    supported_claims: list[str]
    unsupported_claims: list[UnsupportedClaimDomain]
    citation_issues: list[CitationIssueDomain]
    notes: str
    report_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Interfaces
# ---------------------------------------------------------------------------


class EmbedderInterface(ABC):
    @abstractmethod
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        ...


class LexicalRetrieverInterface(ABC):
    @abstractmethod
    def build_index(self, passages: list[PassageForIndex]) -> None:
        ...

    @abstractmethod
    def save_index(self, path: str) -> None:
        ...

    @abstractmethod
    def load_index(self, path: str) -> None:
        ...

    @abstractmethod
    def search(self, query: str, top_k: int) -> list[RetrievalCandidate]:
        ...


class DenseRetrieverInterface(ABC):
    @abstractmethod
    def build_index(self, passages: list[PassageForIndex]) -> None:
        ...

    @abstractmethod
    def save_index(self, path: str) -> None:
        ...

    @abstractmethod
    def load_index(self, path: str) -> None:
        ...

    @abstractmethod
    def search(self, query: str, top_k: int) -> list[RetrievalCandidate]:
        ...


class RerankerInterface(ABC):
    @abstractmethod
    def rerank(
        self, query: str, candidates: list[RetrievalCandidate]
    ) -> list[RetrievalCandidate]:
        ...


class AnswerGeneratorInterface(ABC):
    @abstractmethod
    def generate(
        self, question: str, evidence_bundle: EvidenceBundleDomain
    ) -> AnswerDraftDomain:
        ...


class VerifierInterface(ABC):
    @abstractmethod
    def verify(
        self,
        question: str,
        evidence_bundle: EvidenceBundleDomain,
        answer_draft: AnswerDraftDomain,
    ) -> VerificationReportDomain:
        ...
