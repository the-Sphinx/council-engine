"""
Integration test: ingest a small corpus into DB and verify passage/window counts.
"""

import tempfile
from pathlib import Path

import pytest

from app.db.models import Document, Passage, PassageWindow, Section
from app.ingestion.loaders import CorpusManifest
from app.services.document_service import ingest_document


SMALL_CORPUS = """\
Line one of the test corpus.
Line two of the test corpus.
Line three is here.
Line four follows.
Line five is last."""


@pytest.fixture
def corpus_file():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(SMALL_CORPUS)
        return Path(f.name)


def test_ingest_creates_document(db, corpus_file):
    # Create a project first
    from app.db.models import Project
    project = Project(name="Test Project")
    db.add(project)
    db.commit()

    manifest = CorpusManifest(
        title="Test Corpus",
        source_type="uploaded_text",
        language="en",
        raw_text_path=corpus_file,
        sectioning_strategy="paragraph",
        passage_strategy="natural_units",
    )
    doc = ingest_document(db, project.id, manifest)

    assert doc.id is not None
    assert doc.title == "Test Corpus"
    assert doc.project_id == project.id


def test_ingest_creates_passages(db, corpus_file):
    from app.db.models import Project
    project = Project(name="Test Project 2")
    db.add(project)
    db.commit()

    manifest = CorpusManifest(
        title="Test Corpus",
        source_type="uploaded_text",
        language="en",
        raw_text_path=corpus_file,
        sectioning_strategy="paragraph",
        passage_strategy="natural_units",
    )
    doc = ingest_document(db, project.id, manifest)

    passages = db.query(Passage).filter(Passage.document_id == doc.id).all()
    assert len(passages) == 5  # 5 non-empty lines


def test_ingest_creates_windows(db, corpus_file):
    from app.db.models import Project
    project = Project(name="Test Project 3")
    db.add(project)
    db.commit()

    manifest = CorpusManifest(
        title="Test Corpus",
        source_type="uploaded_text",
        language="en",
        raw_text_path=corpus_file,
        sectioning_strategy="paragraph",
        passage_strategy="natural_units",
    )
    doc = ingest_document(db, project.id, manifest)

    windows = db.query(PassageWindow).filter(PassageWindow.document_id == doc.id).all()
    assert len(windows) == 5  # One window per passage


def test_passage_offsets_slice_back(db, corpus_file):
    from app.db.models import Project
    project = Project(name="Test Project 4")
    db.add(project)
    db.commit()

    manifest = CorpusManifest(
        title="Test Corpus",
        source_type="uploaded_text",
        language="en",
        raw_text_path=corpus_file,
        sectioning_strategy="paragraph",
        passage_strategy="natural_units",
    )
    doc = ingest_document(db, project.id, manifest)

    # Read normalized text
    norm_text = Path(doc.normalized_text_path).read_text(encoding="utf-8")
    passages = (
        db.query(Passage)
        .filter(Passage.document_id == doc.id)
        .order_by(Passage.passage_index)
        .all()
    )

    # Each passage's text should be a substring of the normalized document
    for p in passages:
        assert p.text in norm_text or p.text.strip() in norm_text


def test_passage_indices_sequential(db, corpus_file):
    from app.db.models import Project
    project = Project(name="Test Project 5")
    db.add(project)
    db.commit()

    manifest = CorpusManifest(
        title="Test Corpus",
        source_type="uploaded_text",
        language="en",
        raw_text_path=corpus_file,
        sectioning_strategy="paragraph",
        passage_strategy="natural_units",
    )
    doc = ingest_document(db, project.id, manifest)
    passages = (
        db.query(Passage)
        .filter(Passage.document_id == doc.id)
        .order_by(Passage.passage_index)
        .all()
    )
    indices = [p.passage_index for p in passages]
    assert indices == list(range(len(indices)))
