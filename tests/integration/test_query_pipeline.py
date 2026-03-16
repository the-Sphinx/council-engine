"""
Integration test: end-to-end query pipeline using in-memory index and FakeLLMClient.
"""
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.conftest import FakeLLMClient, SAMPLE_CORPUS


@pytest.fixture
def project_with_index(db, tmp_path):
    """Create a project, ingest SAMPLE_CORPUS, and build indices."""
    from app.db.models import Project
    from app.ingestion.loaders import CorpusManifest
    from app.services.document_service import build_index, ingest_document

    project = Project(name="Integration Test Project")
    db.add(project)
    db.commit()

    corpus_file = tmp_path / "corpus.txt"
    corpus_file.write_text(SAMPLE_CORPUS, encoding="utf-8")

    manifest = CorpusManifest(
        title="Test Corpus",
        source_type="uploaded_text",
        language="en",
        raw_text_path=corpus_file,
        sectioning_strategy="paragraph",
        passage_strategy="natural_units",
    )
    doc = ingest_document(db, project.id, manifest)

    # Build indices into tmp dir
    from app.ingestion.indexer import IndexManager
    from app.retrieval.dense import SentenceTransformerEmbedder
    from app.core.interfaces import PassageForIndex
    from app.db.models import Passage

    index_dir = tmp_path / "indices" / project.id
    im = IndexManager(index_dir)

    passages_db = (
        db.query(Passage)
        .filter(Passage.document_id == doc.id)
        .order_by(Passage.passage_index)
        .all()
    )
    pfi = [
        PassageForIndex(
            passage_id=p.id,
            document_id=p.document_id,
            section_id=p.section_id,
            text=p.text,
            normalized_text=p.normalized_text,
            passage_index=p.passage_index,
        )
        for p in passages_db
    ]

    embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")
    im.build_lexical(pfi)
    im.build_dense(pfi, embedder)

    return project.id, im, passages_db


def test_lexical_retrieval_returns_results(project_with_index, db):
    project_id, im, passages = project_with_index

    from app.retrieval.lexical import BM25Retriever
    retriever = BM25Retriever(im)
    results = retriever.search("patience virtue", top_k=5)

    assert len(results) > 0
    # The "patience" passage should be in top results
    texts = [r.passage_text for r in results]
    assert any("patience" in t.lower() or "virtue" in t.lower() for t in texts)


def test_dense_retrieval_returns_results(project_with_index, db):
    project_id, im, passages = project_with_index

    from app.retrieval.dense import NumpyDenseRetriever, SentenceTransformerEmbedder
    embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")
    retriever = NumpyDenseRetriever(im, embedder)
    results = retriever.search("spiritual practice", top_k=5)

    assert len(results) > 0


def test_hybrid_fusion_scores_in_range(project_with_index, db):
    project_id, im, passages = project_with_index

    from app.retrieval.lexical import BM25Retriever
    from app.retrieval.dense import NumpyDenseRetriever, SentenceTransformerEmbedder
    from app.retrieval.hybrid import compute_hybrid_scores, merge_candidates, normalize_scores

    embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")
    lex = BM25Retriever(im).search("patience", top_k=10)
    den = NumpyDenseRetriever(im, embedder).search("patience", top_k=10)
    merged = merge_candidates(lex, den)
    normalize_scores(merged, "lexical")
    normalize_scores(merged, "dense")
    result = compute_hybrid_scores(merged)

    for c in result:
        assert 0.0 <= c.hybrid_score <= 1.0


def test_full_pipeline_returns_evidence_bundle(project_with_index, db):
    project_id, im, passages = project_with_index

    from app.core.config import Settings
    from app.retrieval.dense import NumpyDenseRetriever, SentenceTransformerEmbedder
    from app.retrieval.lexical import BM25Retriever
    from app.retrieval.pipeline import RetrievalPipeline
    from app.retrieval.reranker import NoOpReranker

    cfg = Settings().get_retrieval_config()
    cfg.reranker_enabled = False
    embedder = SentenceTransformerEmbedder("all-MiniLM-L6-v2")
    pipeline = RetrievalPipeline(
        lexical_retriever=BM25Retriever(im),
        dense_retriever=NumpyDenseRetriever(im, embedder),
        reranker=NoOpReranker(),
        config=cfg,
    )

    # Need a project in DB for query FK
    from app.db.models import Query, Project
    proj = db.get(Project, project_id)
    q = Query(project_id=project_id, question_text="What does patience mean?")
    db.add(q)
    db.flush()

    bundle, debug = pipeline.run(query_id=q.id, question="What does patience mean?", db=db)

    assert bundle.query_id == q.id
    assert len(bundle.anchors) > 0
    assert bundle.mode == "source_only"
    db.rollback()


def test_answer_generation_with_fake_llm(project_with_index, db):
    project_id, im, passages = project_with_index

    # Build a minimal evidence bundle
    from app.core.interfaces import AnchorPassage, EvidenceBundleDomain
    anchor_passage_id = passages[5].id  # "Patience is a virtue"

    bundle = EvidenceBundleDomain(
        query_id="test-query",
        mode="source_only",
        anchors=[
            AnchorPassage(
                passage_id=anchor_passage_id,
                text=passages[5].text,
                rank=1,
                scores={"hybrid": 0.9},
                section_title=None,
                section_order_index=None,
                window_passage_ids=[anchor_passage_id],
                window_text=passages[5].text,
            )
        ],
    )

    fake_llm = FakeLLMClient(passage_id=anchor_passage_id)

    from app.generation.answer_generator import GroundedAnswerGenerator
    generator = GroundedAnswerGenerator(fake_llm)
    draft = generator.generate("What does the text say about patience?", bundle)

    assert draft.final_answer
    assert len(draft.claims) > 0
    assert all(c.claim_id for c in draft.claims)


def test_answer_generation_retries_through_shared_runner(project_with_index, db):
    project_id, im, passages = project_with_index

    from app.core.interfaces import AnchorPassage, EvidenceBundleDomain
    from app.generation.answer_generator import GroundedAnswerGenerator

    anchor_passage_id = passages[5].id
    bundle = EvidenceBundleDomain(
        query_id="test-query",
        mode="source_only",
        anchors=[
            AnchorPassage(
                passage_id=anchor_passage_id,
                text=passages[5].text,
                rank=1,
                scores={"hybrid": 0.9},
                section_title=None,
                section_order_index=None,
                window_passage_ids=[anchor_passage_id],
                window_text=passages[5].text,
            )
        ],
    )

    class RetryLLM:
        def __init__(self):
            self.calls = 0

        def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
            self.calls += 1
            if self.calls == 1:
                return '{"final_answer":"Patience is a virtue."}'
            return (
                '{"final_answer":"Patience is a virtue.","claims":[{"claim_id":"c1",'
                '"statement":"Patience is a virtue.","supporting_passage_ids":["'
                + anchor_passage_id
                + '"],"support_type":"direct"}],"supporting_citations":[{"passage_id":"'
                + anchor_passage_id
                + '","quote":"Patience is a virtue"}],"objections_raised":[],'
                '"confidence_notes":"Direct support."}'
            )

    draft = GroundedAnswerGenerator(RetryLLM()).generate(
        "What does the text say about patience?",
        bundle,
    )

    assert draft.final_answer == "Patience is a virtue."
    assert draft.claims[0].supporting_passage_ids == [anchor_passage_id]


def test_verifier_with_fake_llm(project_with_index, db):
    project_id, im, passages = project_with_index

    from app.core.interfaces import (
        AnchorPassage, EvidenceBundleDomain,
        AnswerDraftDomain, ClaimDomain, CitationDomain,
    )
    anchor_passage_id = passages[5].id

    bundle = EvidenceBundleDomain(
        query_id="test-query",
        mode="source_only",
        anchors=[
            AnchorPassage(
                passage_id=anchor_passage_id,
                text=passages[5].text,
                rank=1,
                scores={"hybrid": 0.9},
                section_title=None,
                section_order_index=None,
                window_passage_ids=[anchor_passage_id],
                window_text=passages[5].text,
            )
        ],
    )

    draft = AnswerDraftDomain(
        final_answer="Patience is a virtue.",
        claims=[ClaimDomain("c1", "Patience is a virtue.", [anchor_passage_id], "direct")],
        supporting_citations=[CitationDomain(anchor_passage_id, "Patience is a virtue found in stillness.")],
        objections_raised=[],
        confidence_notes="Direct support.",
    )

    fake_llm = FakeLLMClient(passage_id=anchor_passage_id)
    from app.generation.verifier import LLMVerifier
    verifier = LLMVerifier(fake_llm)
    report = verifier.verify("What does the text say about patience?", bundle, draft)

    assert report.status in ("pass", "pass_with_warnings", "fail")
    assert report.status == "pass"


def test_query_endpoint_returns_structured_success(project_with_index, db):
    project_id, im, passages = project_with_index

    from app.db.session import get_db
    from app.main import app
    import app.main as main_module
    from app.core.interfaces import (
        AnswerDraftDomain,
        CitationDomain,
        ClaimDomain,
        VerificationReportDomain,
    )

    app.dependency_overrides.clear()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    original_index_managers = dict(main_module._index_managers)
    original_generator = main_module._generator
    original_verifier = main_module._verifier
    original_get_generator = main_module.get_generator
    original_get_verifier = main_module.get_verifier

    try:
        main_module._index_managers = {project_id: im}
        main_module._generator = None
        main_module._verifier = None

        class StubGenerator:
            def generate(self, question, evidence_bundle):
                anchor = evidence_bundle.anchors[0]
                return AnswerDraftDomain(
                    final_answer="The text describes patience as a virtue.",
                    claims=[
                        ClaimDomain(
                            "c1",
                            "Patience is a virtue.",
                            [anchor.passage_id],
                            "direct",
                        )
                    ],
                    supporting_citations=[
                        CitationDomain(anchor.passage_id, anchor.text[:60])
                    ],
                    objections_raised=[],
                    confidence_notes="Direct textual support found.",
                )

        class StubVerifier:
            def verify(self, question, evidence_bundle, answer_draft):
                return VerificationReportDomain(
                    status="pass",
                    supported_claims=["c1"],
                    unsupported_claims=[],
                    citation_issues=[],
                    notes="All claims verified.",
                )

        def fake_generator():
            return StubGenerator()

        def fake_verifier():
            return StubVerifier()

        main_module.get_generator = fake_generator
        main_module.get_verifier = fake_verifier

        client = TestClient(app)
        response = client.post(
            f"/api/projects/{project_id}/queries",
            json={"question": "What does the text say about patience?"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["final_answer"]
        assert payload["verification_status"] == "pass"
        assert isinstance(payload["citations"], list)
        assert len(payload["citations"]) == 1
        assert payload["debug_url"]
    finally:
        app.dependency_overrides.clear()
        main_module._index_managers = original_index_managers
        main_module._generator = original_generator
        main_module._verifier = original_verifier
        main_module.get_generator = original_get_generator
        main_module.get_verifier = original_get_verifier


def test_query_endpoint_returns_structured_generation_error(project_with_index, db):
    project_id, im, _passages = project_with_index

    from app.db.session import get_db
    from app.main import app
    import app.main as main_module

    class BrokenGenerator:
        def generate(self, question, evidence_bundle):
            from app.generation.answer_generator import GenerationError

            raise GenerationError("Answer generator request failed: test failure")

    class StubVerifier:
        def verify(self, question, evidence_bundle, answer_draft):
            raise AssertionError("verifier should not be called")

    app.dependency_overrides.clear()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    original_index_managers = dict(main_module._index_managers)
    original_generator = main_module._generator
    original_verifier = main_module._verifier
    original_get_generator = main_module.get_generator
    original_get_verifier = main_module.get_verifier

    try:
        main_module._index_managers = {project_id: im}
        main_module._generator = BrokenGenerator()
        main_module._verifier = StubVerifier()

        def fake_generator():
            return main_module._generator

        def fake_verifier():
            return main_module._verifier

        main_module.get_generator = fake_generator
        main_module.get_verifier = fake_verifier

        client = TestClient(app)
        response = client.post(
            f"/api/projects/{project_id}/queries",
            json={"question": "What does the text say about patience?"},
        )

        assert response.status_code == 500
        payload = response.json()
        assert payload["detail"]["error"] == "generation_failed"
        assert "Answer generator request failed" in payload["detail"]["message"]
    finally:
        app.dependency_overrides.clear()
        main_module._index_managers = original_index_managers
        main_module._generator = original_generator
        main_module._verifier = original_verifier
        main_module.get_generator = original_get_generator
        main_module.get_verifier = original_get_verifier
