from __future__ import annotations

from pydantic import BaseModel

from app.generation.structured_generation import (
    StructuredGenerationRunner,
    build_correction_prompt,
)


class DemoOutput(BaseModel):
    answer: str
    score: int


class SequenceLLM:
    def __init__(self, responses: list[str] | None = None, exc: Exception | None = None):
        self._responses = responses or []
        self._exc = exc
        self.prompts: list[str] = []
        self.calls = 0

    def chat(self, system: str, user: str, temperature: float = 0.0) -> str:
        self.prompts.append(user)
        self.calls += 1
        if self._exc is not None:
            raise self._exc
        return self._responses[self.calls - 1]


def test_structured_generation_succeeds_immediately():
    runner = StructuredGenerationRunner(
        SequenceLLM(responses=['{"answer":"ok","score":1}'])
    )

    result = runner.run(
        system_prompt="system",
        user_prompt="user",
        output_model=DemoOutput,
    )

    assert result.success is True
    assert result.parsed is not None
    assert result.parsed.answer == "ok"
    assert result.attempts == 1
    assert result.failure_reason is None


def test_structured_generation_repairs_code_fenced_json():
    runner = StructuredGenerationRunner(
        SequenceLLM(responses=['```json\n{"answer":"ok","score":1}\n```'])
    )

    result = runner.run(
        system_prompt="system",
        user_prompt="user",
        output_model=DemoOutput,
    )

    assert result.success is True
    assert result.parsed is not None
    assert result.parsed.score == 1
    assert result.repair_attempted is True
    assert result.repair_succeeded is True


def test_structured_generation_extracts_json_from_surrounding_text():
    runner = StructuredGenerationRunner(
        SequenceLLM(responses=['Here is the result:\n{"answer":"ok","score":1}\nThanks.'])
    )

    result = runner.run(
        system_prompt="system",
        user_prompt="user",
        output_model=DemoOutput,
    )

    assert result.success is True
    assert result.parsed is not None
    assert result.parsed.answer == "ok"
    assert result.repair_succeeded is True


def test_structured_generation_retries_after_invalid_json():
    llm = SequenceLLM(
        responses=[
            '{"answer":',
            '{"answer":"fixed","score":2}',
        ]
    )
    runner = StructuredGenerationRunner(llm)

    result = runner.run(
        system_prompt="system",
        user_prompt="user",
        output_model=DemoOutput,
    )

    assert result.success is True
    assert result.parsed is not None
    assert result.parsed.answer == "fixed"
    assert result.attempts == 2
    assert "Your previous response was invalid." in llm.prompts[1]


def test_structured_generation_retries_after_schema_failure():
    runner = StructuredGenerationRunner(
        SequenceLLM(
            responses=[
                '{"answer":"ok"}',
                '{"answer":"fixed","score":2}',
            ]
        )
    )

    result = runner.run(
        system_prompt="system",
        user_prompt="user",
        output_model=DemoOutput,
    )

    assert result.success is True
    assert result.parsed is not None
    assert result.parsed.score == 2
    assert result.attempts == 2


def test_structured_generation_reports_retry_exhaustion():
    runner = StructuredGenerationRunner(
        SequenceLLM(
            responses=[
                '{"answer":"ok"}',
                '{"answer":"still bad"}',
                '{"answer":"nope"}',
            ]
        )
    )

    result = runner.run(
        system_prompt="system",
        user_prompt="user",
        output_model=DemoOutput,
    )

    assert result.success is False
    assert result.parsed is None
    assert result.attempts == 3
    assert result.failure_reason is not None
    assert "schema_validation" in result.failure_reason


def test_structured_generation_reports_transport_failure():
    runner = StructuredGenerationRunner(SequenceLLM(exc=RuntimeError("boom")))

    result = runner.run(
        system_prompt="system",
        user_prompt="user",
        output_model=DemoOutput,
    )

    assert result.success is False
    assert result.attempts == 1
    assert result.failure_reason == "llm_error: boom"
    assert result.attempt_details[0].failure_stage == "llm_error"


def test_build_correction_prompt_includes_schema_and_invalid_output():
    prompt = build_correction_prompt(
        user_prompt="base",
        previous_output="bad output",
        output_model=DemoOutput,
        failure_reason="json_parse: bad",
    )

    assert "bad output" in prompt
    assert "Expected JSON schema" in prompt
    assert "json_parse: bad" in prompt
