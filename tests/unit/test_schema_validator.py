import pytest
from pydantic import ValidationError
from app.generation.schema_validator import AnswerGeneratorOutput, VerifierOutput


VALID_ANSWER = {
    "final_answer": "The text discusses patience.",
    "claims": [
        {
            "claim_id": "c1",
            "statement": "Patience is mentioned.",
            "supporting_passage_ids": ["p1"],
            "support_type": "direct",
        }
    ],
    "supporting_citations": [{"passage_id": "p1", "quote": "Patience is a virtue"}],
    "objections_raised": [],
    "confidence_notes": "Good evidence.",
}


def test_valid_answer_parses():
    output = AnswerGeneratorOutput.model_validate(VALID_ANSWER)
    assert output.final_answer == "The text discusses patience."
    assert len(output.claims) == 1


def test_missing_field_raises():
    bad = {**VALID_ANSWER}
    del bad["final_answer"]
    with pytest.raises(ValidationError):
        AnswerGeneratorOutput.model_validate(bad)


def test_invalid_support_type():
    bad = {**VALID_ANSWER}
    bad["claims"] = [{"claim_id": "c1", "statement": "x", "supporting_passage_ids": [], "support_type": "invented"}]
    with pytest.raises(ValidationError):
        AnswerGeneratorOutput.model_validate(bad)


def test_validate_passage_ids_detects_hallucination():
    output = AnswerGeneratorOutput.model_validate(VALID_ANSWER)
    hallucinated = output.validate_passage_ids({"p2"})  # p1 not in valid set
    assert "p1" in hallucinated


def test_validate_passage_ids_all_valid():
    output = AnswerGeneratorOutput.model_validate(VALID_ANSWER)
    hallucinated = output.validate_passage_ids({"p1"})
    assert hallucinated == []


def test_validate_citation_quotes_mismatch():
    output = AnswerGeneratorOutput.model_validate(VALID_ANSWER)
    mismatches = output.validate_citation_quotes({"p1": "Completely different text."})
    assert "p1" in mismatches


def test_validate_citation_quotes_match():
    output = AnswerGeneratorOutput.model_validate(VALID_ANSWER)
    # Quote "Patience is a virtue." must be a substring of the passage text
    mismatches = output.validate_citation_quotes({"p1": "Patience is a virtue found in stillness."})
    assert mismatches == []


def test_verifier_output_valid():
    data = {
        "status": "pass",
        "supported_claims": ["c1"],
        "unsupported_claims": [],
        "citation_issues": [],
        "notes": "All good.",
    }
    output = VerifierOutput.model_validate(data)
    assert output.status == "pass"


def test_verifier_invalid_status():
    data = {
        "status": "invalid_status",
        "supported_claims": [],
        "unsupported_claims": [],
        "citation_issues": [],
        "notes": "",
    }
    with pytest.raises(ValidationError):
        VerifierOutput.model_validate(data)
