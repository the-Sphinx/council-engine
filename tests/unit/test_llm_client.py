from __future__ import annotations

import httpx

from app.generation.answer_generator import GenerationError, GroundedAnswerGenerator
from app.generation.llm_client import OllamaClient
from app.generation.verifier import LLMVerifier, VerificationError
from app.core.interfaces import AnchorPassage, AnswerDraftDomain, CitationDomain, ClaimDomain, EvidenceBundleDomain


def _bundle() -> EvidenceBundleDomain:
    return EvidenceBundleDomain(
        query_id="q1",
        mode="source_only",
        anchors=[
            AnchorPassage(
                passage_id="p1",
                text="Patience is a virtue.",
                rank=1,
                scores={"hybrid": 0.9},
                section_title=None,
                section_order_index=None,
                window_passage_ids=["p1"],
                window_text="Patience is a virtue.",
            )
        ],
    )


def test_ollama_client_falls_back_to_openai_compatible_endpoint(monkeypatch):
    calls = []

    def fake_post(url, json, timeout):
        calls.append(url)
        request = httpx.Request("POST", url)
        if url.endswith("/api/chat"):
            return httpx.Response(404, request=request, text="not found")
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": '{"ok": true}'}}]},
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    client = OllamaClient(base_url="http://localhost:11434", model="llama3.1:8b")
    output = client.chat("system", "user")

    assert output == '{"ok": true}'
    assert calls == [
        "http://localhost:11434/api/chat",
        "http://localhost:11434/v1/chat/completions",
    ]


def test_ollama_client_reports_missing_model_before_fallback(monkeypatch):
    def fake_post(url, json, timeout):
        request = httpx.Request("POST", url)
        if url.endswith("/api/chat"):
            return httpx.Response(
                404,
                request=request,
                json={"error": "model 'llama3.1:8b' not found"},
            )
        raise AssertionError("fallback should not be called for missing Ollama model")

    monkeypatch.setattr(httpx, "post", fake_post)

    client = OllamaClient(base_url="http://localhost:11434", model="llama3.1:8b")

    try:
        client.chat("system", "user")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "not installed" in str(exc)
        assert "ollama pull llama3.1:8b" in str(exc)


class FailingLLM:
    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        raise RuntimeError("boom")


def test_answer_generator_wraps_transport_failures():
    generator = GroundedAnswerGenerator(FailingLLM())

    try:
        generator.generate("What is patience?", _bundle())
        assert False, "expected GenerationError"
    except GenerationError as exc:
        assert "request failed" in str(exc)


def test_verifier_wraps_transport_failures():
    verifier = LLMVerifier(FailingLLM())
    draft = AnswerDraftDomain(
        final_answer="Patience is a virtue.",
        claims=[ClaimDomain("c1", "Patience is a virtue.", ["p1"], "direct")],
        supporting_citations=[CitationDomain("p1", "Patience is a virtue.")],
        objections_raised=[],
        confidence_notes="Direct support.",
    )

    try:
        verifier.verify("What is patience?", _bundle(), draft)
        assert False, "expected VerificationError"
    except VerificationError as exc:
        assert "request failed" in str(exc)
