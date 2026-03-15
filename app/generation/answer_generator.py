"""
GroundedAnswerGenerator: sends evidence bundle to LLM and returns structured AnswerDraftDomain.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

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


@dataclass
class ParseAttempt:
    output: AnswerGeneratorOutput | None
    should_retry: bool


class GroundedAnswerGenerator(AnswerGeneratorInterface):
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def generate(
        self, question: str, evidence_bundle: EvidenceBundleDomain
    ) -> AnswerDraftDomain:
        user_prompt = build_answer_user_prompt(question, evidence_bundle)
        valid_ids = {a.passage_id for a in evidence_bundle.anchors}

        try:
            raw = self._llm.chat(ANSWER_GENERATOR_SYSTEM, user_prompt)
        except Exception as exc:
            logger.warning("Answer generator request failed, using fallback: %s", exc)
            return self._build_fallback_answer(evidence_bundle)
        attempt = self._parse_and_validate(raw, valid_ids)
        output = attempt.output

        if output is None and attempt.should_retry:
            # Retry once with explicit correction
            correction_prompt = (
                user_prompt
                + "\n\nIMPORTANT: Your previous response was not valid JSON. "
                "Return ONLY a valid JSON object, nothing else."
            )
            try:
                raw2 = self._llm.chat(ANSWER_GENERATOR_SYSTEM, correction_prompt)
            except Exception as exc:
                logger.warning("Answer generator retry failed, using fallback: %s", exc)
                return self._build_fallback_answer(evidence_bundle)
            output = self._parse_and_validate(raw2, valid_ids).output

        if output is None:
            logger.warning(
                "Falling back to deterministic extractive answer for query %r",
                question[:120],
            )
            return self._build_fallback_answer(evidence_bundle)

        return self._to_domain(output)

    def _parse_and_validate(
        self, raw: str, valid_ids: set[str]
    ) -> ParseAttempt:
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

            return ParseAttempt(output=output, should_retry=False)
        except json.JSONDecodeError as e:
            logger.warning("Answer generator parse error: %s", e)
            return ParseAttempt(output=None, should_retry=True)
        except Exception as e:
            logger.warning("Answer generator parse error: %s", e)
            return ParseAttempt(output=None, should_retry=False)

    def _build_fallback_answer(
        self,
        evidence_bundle: EvidenceBundleDomain,
    ) -> AnswerDraftDomain:
        anchors = evidence_bundle.anchors[:3]
        if not anchors:
            raise GenerationError("Answer generator failed and no evidence was available for fallback")

        claims = []
        citations = []
        answer_parts = []
        for idx, anchor in enumerate(anchors, start=1):
            excerpt = anchor.text.strip()
            quote = excerpt[:240]
            claims.append(
                ClaimDomain(
                    claim_id=f"fallback_c{idx}",
                    statement=excerpt,
                    supporting_passage_ids=[anchor.passage_id],
                    support_type="direct",
                )
            )
            citations.append(CitationDomain(passage_id=anchor.passage_id, quote=quote))
            answer_parts.append(excerpt)

        objections = [
            ObjectionDomain(
                issue=(
                    "This answer was assembled directly from the top retrieved passages because "
                    "the local model did not return the required schema."
                ),
                related_passage_ids=[anchor.passage_id for anchor in anchors],
            )
        ]

        return AnswerDraftDomain(
            final_answer=" ".join(answer_parts),
            claims=claims,
            supporting_citations=citations,
            objections_raised=objections,
            confidence_notes=(
                "Fallback extractive answer built from top evidence after schema validation failed."
            ),
        )

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
