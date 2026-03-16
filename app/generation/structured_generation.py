"""
Shared structured generation utilities for schema-constrained LLM output.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger
from app.generation.llm_client import LLMClient

logger = get_logger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)


@dataclass
class StructuredGenerationAttempt:
    raw_output: str | None
    failure_stage: str | None
    failure_reason: str | None
    repair_attempted: bool
    repair_succeeded: bool


@dataclass
class StructuredGenerationResult(Generic[TModel]):
    success: bool
    parsed: TModel | None
    raw_outputs: list[str]
    attempts: int
    attempt_details: list[StructuredGenerationAttempt]
    failure_reason: str | None
    repair_attempted: bool
    repair_succeeded: bool


def build_correction_prompt(
    user_prompt: str,
    previous_output: str,
    output_model: type[BaseModel],
    failure_reason: str,
) -> str:
    schema_json = json.dumps(output_model.model_json_schema(), indent=2, ensure_ascii=False)
    return (
        f"{user_prompt}\n\n"
        "Your previous response was invalid.\n"
        "Return ONLY a valid JSON object.\n"
        "Do not include markdown, code fences, commentary, or explanations.\n"
        "Follow the schema exactly and preserve the intended meaning of your prior answer.\n"
        f"Failure reason: {failure_reason}\n\n"
        "Expected JSON schema:\n"
        f"{schema_json}\n\n"
        "Previous invalid output:\n"
        f"{previous_output}"
    )


class StructuredGenerationRunner:
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def run(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_model: type[TModel],
        max_attempts: int = 3,
        temperature: float = 0.0,
        schema_label: str = "structured output",
    ) -> StructuredGenerationResult[TModel]:
        raw_outputs: list[str] = []
        attempt_details: list[StructuredGenerationAttempt] = []
        current_prompt = user_prompt

        for attempt_number in range(1, max_attempts + 1):
            try:
                raw_output = self._llm.chat(
                    system_prompt,
                    current_prompt,
                    temperature=temperature,
                )
            except Exception as exc:
                reason = f"llm_error: {exc}"
                logger.warning(
                    "Structured generation failed for %s on attempt %s/%s: %s",
                    schema_label,
                    attempt_number,
                    max_attempts,
                    exc,
                )
                attempt_details.append(
                    StructuredGenerationAttempt(
                        raw_output=None,
                        failure_stage="llm_error",
                        failure_reason=reason,
                        repair_attempted=False,
                        repair_succeeded=False,
                    )
                )
                return self._result(
                    parsed=None,
                    raw_outputs=raw_outputs,
                    attempt_details=attempt_details,
                    failure_reason=reason,
                )

            raw_outputs.append(raw_output)
            parsed, failure_stage, failure_reason, repair_attempted, repair_succeeded = (
                self._parse_and_validate(raw_output, output_model)
            )

            if parsed is not None:
                return self._result(
                    parsed=parsed,
                    raw_outputs=raw_outputs,
                    attempt_details=attempt_details
                    + [
                        StructuredGenerationAttempt(
                            raw_output=raw_output,
                            failure_stage=None,
                            failure_reason=None,
                            repair_attempted=repair_attempted,
                            repair_succeeded=repair_succeeded,
                        )
                    ],
                    failure_reason=None,
                )

            attempt_details.append(
                StructuredGenerationAttempt(
                    raw_output=raw_output,
                    failure_stage=failure_stage,
                    failure_reason=failure_reason,
                    repair_attempted=repair_attempted,
                    repair_succeeded=repair_succeeded,
                )
            )
            logger.warning(
                "Structured generation validation failed for %s on attempt %s/%s: %s",
                schema_label,
                attempt_number,
                max_attempts,
                failure_reason,
            )

            if attempt_number < max_attempts:
                current_prompt = build_correction_prompt(
                    user_prompt=user_prompt,
                    previous_output=raw_output,
                    output_model=output_model,
                    failure_reason=failure_reason or "unknown_failure",
                )

        return self._result(
            parsed=None,
            raw_outputs=raw_outputs,
            attempt_details=attempt_details,
            failure_reason=attempt_details[-1].failure_reason if attempt_details else None,
        )

    def _parse_and_validate(
        self,
        raw_output: str,
        output_model: type[TModel],
    ) -> tuple[TModel | None, str | None, str | None, bool, bool]:
        try:
            data = json.loads(raw_output)
        except json.JSONDecodeError as exc:
            repaired = self._repair_json_candidate(raw_output)
            if repaired is None:
                return None, "json_parse", f"json_parse: {exc}", True, False
            try:
                data = json.loads(repaired)
            except json.JSONDecodeError as repair_exc:
                return None, "json_parse", f"json_parse: {repair_exc}", True, False
            try:
                parsed = output_model.model_validate(data)
                return parsed, None, None, True, True
            except ValidationError as val_exc:
                return (
                    None,
                    "schema_validation",
                    f"schema_validation: {val_exc}",
                    True,
                    True,
                )

        try:
            parsed = output_model.model_validate(data)
            return parsed, None, None, False, False
        except ValidationError as exc:
            return None, "schema_validation", f"schema_validation: {exc}", False, False

    def _repair_json_candidate(self, raw_output: str) -> str | None:
        stripped = raw_output.strip()
        candidates = [
            stripped,
            self._strip_code_fences(stripped),
        ]

        for candidate in candidates:
            if not candidate:
                continue
            extracted = self._extract_first_json_block(candidate)
            for option in (candidate.strip(), extracted):
                if option and self._looks_like_json(option):
                    return option
        return None

    def _strip_code_fences(self, text: str) -> str:
        cleaned = text.strip()
        if not cleaned.startswith("```"):
            return cleaned

        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()

    def _extract_first_json_block(self, text: str) -> str | None:
        start_positions = []
        object_start = text.find("{")
        array_start = text.find("[")
        if object_start != -1:
            start_positions.append(object_start)
        if array_start != -1:
            start_positions.append(array_start)
        if not start_positions:
            return None

        start_index = min(start_positions)
        opening = text[start_index]
        closing = "}" if opening == "{" else "]"
        depth = 0
        in_string = False
        escape = False

        for index in range(start_index, len(text)):
            char = text[index]
            if in_string:
                if escape:
                    escape = False
                elif char == "\\":
                    escape = True
                elif char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue
            if char == opening:
                depth += 1
            elif char == closing:
                depth -= 1
                if depth == 0:
                    return text[start_index:index + 1].strip()
        return None

    def _looks_like_json(self, text: str) -> bool:
        stripped = text.strip()
        return (stripped.startswith("{") and stripped.endswith("}")) or (
            stripped.startswith("[") and stripped.endswith("]")
        )

    def _result(
        self,
        *,
        parsed: TModel | None,
        raw_outputs: list[str],
        attempt_details: list[StructuredGenerationAttempt],
        failure_reason: str | None,
    ) -> StructuredGenerationResult[TModel]:
        return StructuredGenerationResult(
            success=parsed is not None,
            parsed=parsed,
            raw_outputs=raw_outputs,
            attempts=len(attempt_details),
            attempt_details=attempt_details,
            failure_reason=failure_reason,
            repair_attempted=any(a.repair_attempted for a in attempt_details),
            repair_succeeded=any(a.repair_succeeded for a in attempt_details),
        )
