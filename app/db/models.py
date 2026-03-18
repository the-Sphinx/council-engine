import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="project", cascade="all, delete-orphan"
    )
    queries: Mapped[list["Query"]] = relationship(
        "Query", back_populates="project", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en")
    raw_text_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_text_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="documents")
    sections: Mapped[list["Section"]] = relationship(
        "Section", back_populates="document", cascade="all, delete-orphan"
    )
    passages: Mapped[list["Passage"]] = relationship(
        "Passage", back_populates="document", cascade="all, delete-orphan"
    )


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    parent_section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True
    )
    section_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="sections")
    passages: Mapped[list["Passage"]] = relationship(
        "Passage", back_populates="section"
    )

    __table_args__ = (
        Index("ix_sections_document_id", "document_id"),
        Index("ix_sections_order", "document_id", "order_index"),
    )


class Passage(Base):
    __tablename__ = "passages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    section_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("sections.id", ondelete="SET NULL"), nullable=True
    )
    passage_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="passages")
    section: Mapped["Section | None"] = relationship(
        "Section", back_populates="passages"
    )
    windows: Mapped[list["PassageWindow"]] = relationship(
        "PassageWindow",
        foreign_keys="PassageWindow.anchor_passage_id",
        back_populates="anchor_passage",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_passages_document_id", "document_id"),
        Index("ix_passages_doc_index", "document_id", "passage_index"),
    )


class PassageWindow(Base):
    __tablename__ = "passage_windows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    anchor_passage_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("passages.id", ondelete="CASCADE"), nullable=False
    )
    start_passage_index: Mapped[int] = mapped_column(Integer, nullable=False)
    end_passage_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_text: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    anchor_passage: Mapped["Passage"] = relationship(
        "Passage", foreign_keys=[anchor_passage_id], back_populates="windows"
    )

    __table_args__ = (
        Index("ix_windows_anchor", "anchor_passage_id"),
        Index("ix_windows_document_range", "document_id", "start_passage_index", "end_passage_index"),
    )


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(String(36), nullable=False)
    section_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    passage_id: Mapped[str] = mapped_column(String(36), nullable=False)
    quote_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_label: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)


class Query(Base):
    __tablename__ = "queries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(50), default="source_only")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    project: Mapped["Project"] = relationship("Project", back_populates="queries")
    retrieval_results: Mapped[list["RetrievalResult"]] = relationship(
        "RetrievalResult", back_populates="query", cascade="all, delete-orphan"
    )
    evidence_bundles: Mapped[list["EvidenceBundle"]] = relationship(
        "EvidenceBundle", back_populates="query", cascade="all, delete-orphan"
    )
    answer_drafts: Mapped[list["AnswerDraft"]] = relationship(
        "AnswerDraft", back_populates="query", cascade="all, delete-orphan"
    )
    verification_reports: Mapped[list["VerificationReport"]] = relationship(
        "VerificationReport", back_populates="query", cascade="all, delete-orphan"
    )
    debug_artifacts: Mapped[list["QueryDebugArtifact"]] = relationship(
        "QueryDebugArtifact", back_populates="query", cascade="all, delete-orphan"
    )
    citations: Mapped[list["Citation"]] = relationship(
        "Citation", back_populates=None, cascade="all, delete-orphan",
        foreign_keys="Citation.query_id"
    )


class RetrievalResult(Base):
    __tablename__ = "retrieval_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    passage_id: Mapped[str] = mapped_column(String(36), nullable=False)
    retrieval_method: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    query: Mapped["Query"] = relationship("Query", back_populates="retrieval_results")

    __table_args__ = (Index("ix_retrieval_results_query_id", "query_id"),)


class EvidenceBundle(Base):
    __tablename__ = "evidence_bundles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    bundle_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    query: Mapped["Query"] = relationship("Query", back_populates="evidence_bundles")


class QueryDebugArtifact(Base):
    __tablename__ = "query_debug_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    original_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_query: Mapped[str] = mapped_column(Text, nullable=False)
    lexical_query: Mapped[str | None] = mapped_column(Text, nullable=True)
    expanded_terms_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    retrieval_config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    lexical_hits_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    dense_hits_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    merged_candidates_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reranked_candidates_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    query: Mapped["Query"] = relationship("Query", back_populates="debug_artifacts")

    __table_args__ = (Index("ix_query_debug_artifacts_query_id", "query_id"),)


class AnswerDraft(Base):
    __tablename__ = "answer_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    claims_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    citations_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    objections_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    query: Mapped["Query"] = relationship("Query", back_populates="answer_drafts")


class VerificationReport(Base):
    __tablename__ = "verification_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    query_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("queries.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    supported_claims_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    unsupported_claims_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    citation_issues_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    query: Mapped["Query"] = relationship(
        "Query", back_populates="verification_reports"
    )
