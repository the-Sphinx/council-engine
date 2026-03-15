"""
GroundedAnswerGenerator: sends evidence bundle to LLM and returns structured AnswerDraftDomain.
"""

from __future__ import annotations

import json

from app.core.interfaces import (
    AnswerDraftDomain,
    AnswerGeneratorInterface,
    CitationDomain,
    ClaimDomain,
    EvidenceBundleDomain,
    ObjectionDomain,
)
from app.core.logging import get_logger
from app.generation.llm_client import LLMClient
from app.generation.prompts import ANSWER_GENERATOR_SYSTEM, build_answer_user_prompt
from app.generation.schema_validator import AnswerGeneratorOutput

logger = get_logger(__name__)


class GenerationError(Exception):
    pass


class GroundedAnswerGenerator(AnswerGeneratorInterface):
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def generate(
        self, question: str, evidence_bundle: EvidenceBundleDomain
    ) -> AnswerDraftDomain:
        user_prompt = build_answer_user_prompt(question, evidence_bundle)
        valid_ids = {a.passage_id for a in evidence_bundle.anchors}

        raw = self._llm.chat(ANSWER_GENERATOR_SYSTEM, user_prompt)
        output = self._parse_and_validate(raw, valid_ids)

        if output is None:
            # Retry once with explicit correction
            correction_prompt = (
                user_prompt
                + "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Return ONLY a valid JSON object, nothing else."
            )
            raw2 = self._llm.chat(ANSWER_GENERATOR_SYSTEM, correction_prompt)
            output = self._parse_and_validate(raw2, valid_ids)

        if output is None:
            raise GenerationError("Answer generator failed to produce valid JSON after retry")

        return self._to_domain(output)

    def _parse_and_validate(
        self, raw: str, valid_ids: set[str]
    ) -> AnswerGeneratorOutput | None:
        try:
            data = json.loads(raw)
            output = AnswerGeneratorOutput.model_validate(data)

            # Check for hallucinated passage IDs and remove them
            bad_ids = set(output.validate_passage_ids(valid_ids))
            if bad_ids:
                logger.warning("Hallucinated passage IDs detected: %s", bad_ids)
                # Filter out bad IDs rather than hard-failing
                for claim in output.claims:
                    claim.supporting_passage_ids = [
                        pid for pid in claim.supporting_passage_ids if pid not in bad_ids
                    ]
                output.supporting_citations = [
                    c for c in output.supporting_citations if c.passage_id not in bad_ids
                ]

            return output
        except (json.JSONDecodeError, ValueError, Exception) as e:
            logger.warning("Answer generator parse error: %s", e)
            return None

    def _to_domain(self, output: AnswerGeneratorOutput) -> AnswerDraftDomain:
        claims = [
            ClaimDomain(
                claim_id=c.claim_id,
                statement=c.statement,
                supporting_passage_ids=c.supporting_passage_ids,
                support_type=c.support_type,
            )
            for c in output.claims
        ]
        citations = [
            CitationDomain(passage_id=c.passage_id, quote=c.quote)
            for c in output.supporting_citations
        ]
        objections = [
            ObjectionDomain(issue=o.issue, related_passage_ids=o.related_passage_ids)
            for o in output.objections_raised
        ]
        return AnswerDraftDomain(
            final_answer=output.final_answer,
            claims=claims,
            supporting_citations=citations,
            objections_raised=objections,
            confidence_notes=output.confidence_notes,
        )
