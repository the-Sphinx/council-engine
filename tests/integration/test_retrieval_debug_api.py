import json

from fastapi.testclient import TestClient


def test_retrieval_debug_returns_persisted_pipeline_artifacts(db):
    from app.db.models import (
        AnswerDraft,
        EvidenceBundle,
        Project,
        Query,
        QueryDebugArtifact,
        VerificationReport,
    )
    from app.main import app

    project = Project(name="Debug Project")
    db.add(project)
    db.flush()

    query = Query(project_id=project.id, question_text="  What is patience?  ")
    db.add(query)
    db.flush()

    debug = QueryDebugArtifact(
        query_id=query.id,
        normalized_query="What is patience?",
        lexical_hits_json=json.dumps([{"passage_id": "p1", "lexical_score": 0.8}]),
        dense_hits_json=json.dumps([{"passage_id": "p1", "dense_score": 0.7}]),
        merged_candidates_json=json.dumps([{"passage_id": "p1", "hybrid_score": 0.75}]),
        reranked_candidates_json=json.dumps([{"passage_id": "p1", "rerank_score": 0.75}]),
    )
    bundle = EvidenceBundle(
        query_id=query.id,
        bundle_json=json.dumps(
            {
                "query_id": query.id,
                "mode": "source_only",
                "anchors": [{"passage_id": "p1", "text": "Patience is a virtue."}],
            }
        ),
    )
    draft = AnswerDraft(
        query_id=query.id,
        answer_text="Patience is a virtue.",
        claims_json=json.dumps([{"claim_id": "c1"}]),
        citations_json=json.dumps([{"passage_id": "p1", "quote": "Patience is a virtue."}]),
        objections_json=json.dumps([]),
    )
    report = VerificationReport(
        query_id=query.id,
        status="pass",
        supported_claims_json=json.dumps(["c1"]),
        unsupported_claims_json=json.dumps([]),
        citation_issues_json=json.dumps([]),
        notes_json=json.dumps({"notes": "All claims verified."}),
    )
    db.add_all([debug, bundle, draft, report])
    db.commit()

    app.dependency_overrides.clear()
    from app.db.session import get_db

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)
    response = client.get(f"/api/queries/{query.id}/retrieval-debug")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["normalized_query"] == "What is patience?"
    assert payload["lexical_hits"] == [{"passage_id": "p1", "lexical_score": 0.8}]
    assert payload["dense_hits"] == [{"passage_id": "p1", "dense_score": 0.7}]
    assert payload["merged_candidates"] == [{"passage_id": "p1", "hybrid_score": 0.75}]
    assert payload["reranked_candidates"] == [{"passage_id": "p1", "rerank_score": 0.75}]
