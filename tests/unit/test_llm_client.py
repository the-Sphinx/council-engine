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


class InvalidSchemaLLM:
    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        return '{"passages":[{"passage_id":"p1","text":"Patience is a virtue."}]}'


class RetryThenValidAnswerLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        self.calls += 1
        if self.calls == 1:
            return '{"final_answer":"Patience matters."}'
        return (
            '{"final_answer":"Patience is a virtue.","claims":[{"claim_id":"c1",'
            '"statement":"Patience is a virtue.","supporting_passage_ids":["p1"],'
            '"support_type":"direct"}],"supporting_citations":[{"passage_id":"p1",'
            '"quote":"Patience is a virtue."}],"objections_raised":[],"confidence_notes":"Direct support."}'
        )


class RetryThenValidVerifierLLM:
    def __init__(self):
        self.calls = 0

    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        self.calls += 1
        if self.calls == 1:
            return '{"status":"pass"}'
        return (
            '{"status":"pass","supported_claims":["c1"],"unsupported_claims":[],'
            '"citation_issues":[],"notes":"All claims supported."}'
        )


def test_answer_generator_wraps_transport_failures():
    generator = GroundedAnswerGenerator(FailingLLM())
    draft = generator.generate("What is patience?", _bundle())

    assert draft.claims[0].supporting_passage_ids == ["p1"]
    assert "Fallback extractive answer" in draft.confidence_notes


def test_verifier_wraps_transport_failures():
    verifier = LLMVerifier(FailingLLM())
    draft = AnswerDraftDomain(
        final_answer="Patience is a virtue.",
        claims=[ClaimDomain("c1", "Patience is a virtue.", ["p1"], "direct")],
        supporting_citations=[CitationDomain("p1", "Patience is a virtue.")],
        objections_raised=[],
        confidence_notes="Direct support.",
    )

    report = verifier.verify("What is patience?", _bundle(), draft)

    assert report.status == "pass_with_warnings"
    assert report.supported_claims == ["c1"]


def test_answer_generator_falls_back_to_extractive_answer_for_invalid_schema():
    generator = GroundedAnswerGenerator(InvalidSchemaLLM())
    draft = generator.generate("What is patience?", _bundle())

    assert draft.final_answer == "Patience is a virtue."
    assert draft.claims[0].supporting_passage_ids == ["p1"]
    assert "Fallback extractive answer" in draft.confidence_notes


def test_verifier_falls_back_to_deterministic_report_for_invalid_schema():
    verifier = LLMVerifier(InvalidSchemaLLM())
    draft = AnswerDraftDomain(
        final_answer="Patience is a virtue.",
        claims=[ClaimDomain("c1", "Patience is a virtue.", ["p1"], "direct")],
        supporting_citations=[CitationDomain("p1", "Patience is a virtue.")],
        objections_raised=[],
        confidence_notes="Fallback extractive answer built from top evidence after schema validation failed.",
    )

    report = verifier.verify("What is patience?", _bundle(), draft)

    assert report.status == "pass_with_warnings"
    assert report.supported_claims == ["c1"]
    assert "Fallback verification" in report.notes


def test_verifier_skips_llm_for_fallback_answer_draft():
    class ShouldNotBeCalledLLM:
        def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
            raise AssertionError("LLM should not be called for fallback answer verification")

    verifier = LLMVerifier(ShouldNotBeCalledLLM())
    draft = AnswerDraftDomain(
        final_answer="Patience is a virtue.",
        claims=[ClaimDomain("fallback_c1", "Patience is a virtue.", ["p1"], "direct")],
        supporting_citations=[CitationDomain("p1", "Patience is a virtue.")],
        objections_raised=[],
        confidence_notes="Fallback extractive answer built from top evidence after schema validation failed.",
    )

    report = verifier.verify("What is patience?", _bundle(), draft)

    assert report.status == "pass_with_warnings"
    assert report.supported_claims == ["fallback_c1"]
    assert "Fallback verification" in report.notes


def test_answer_generator_retries_and_returns_structured_output():
    generator = GroundedAnswerGenerator(RetryThenValidAnswerLLM())

    draft = generator.generate("What is patience?", _bundle())

    assert draft.final_answer == "Patience is a virtue."
    assert draft.claims[0].supporting_passage_ids == ["p1"]
    assert draft.confidence_notes == "Direct support."


def test_answer_generator_filters_hallucinated_passage_ids_after_structured_success():
    class HallucinatedAnswerLLM:
        def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
            return (
                '{"final_answer":"Patience is a virtue.","claims":[{"claim_id":"c1",'
                '"statement":"Patience is a virtue.","supporting_passage_ids":["p1","ghost"],'
                '"support_type":"direct"}],"supporting_citations":[{"passage_id":"p1",'
                '"quote":"Patience is a virtue."},{"passage_id":"ghost","quote":"ghost"}],'
                '"objections_raised":[],"confidence_notes":"Direct support."}'
            )

    generator = GroundedAnswerGenerator(HallucinatedAnswerLLM())
    draft = generator.generate("What is patience?", _bundle())

    assert draft.claims[0].supporting_passage_ids == ["p1"]
    assert [citation.passage_id for citation in draft.supporting_citations] == ["p1"]


def test_verifier_retries_and_returns_structured_output():
    verifier = LLMVerifier(RetryThenValidVerifierLLM())
    draft = AnswerDraftDomain(
        final_answer="Patience is a virtue.",
        claims=[ClaimDomain("c1", "Patience is a virtue.", ["p1"], "direct")],
        supporting_citations=[CitationDomain("p1", "Patience is a virtue.")],
        objections_raised=[],
        confidence_notes="Direct support.",
    )

    report = verifier.verify("What is patience?", _bundle(), draft)

    assert report.status == "pass"
    assert report.supported_claims == ["c1"]


def test_verifier_filters_unknown_claim_ids_and_passage_ids():
    class VerifierFilteringLLM:
        def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
            return (
                '{"status":"pass_with_warnings","supported_claims":["c1"],'
                '"unsupported_claims":[{"claim_id":"c1","reason":"warn"},{"claim_id":"ghost","reason":"bad"}],'
                '"citation_issues":[{"passage_id":"p1","issue":"warn"},{"passage_id":"ghost","issue":"bad"}],'
                '"notes":"Mixed."}'
            )

    verifier = LLMVerifier(VerifierFilteringLLM())
    draft = AnswerDraftDomain(
        final_answer="Patience is a virtue.",
        claims=[ClaimDomain("c1", "Patience is a virtue.", ["p1"], "direct")],
        supporting_citations=[CitationDomain("p1", "Patience is a virtue.")],
        objections_raised=[],
        confidence_notes="Direct support.",
    )

    report = verifier.verify("What is patience?", _bundle(), draft)

    assert [claim.claim_id for claim in report.unsupported_claims] == ["c1"]
    assert [issue.passage_id for issue in report.citation_issues] == ["p1"]
