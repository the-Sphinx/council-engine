"""
GroundedAnswerGenerator: sends evidence bundle to LLM and returns structured AnswerDraftDomain.
"""

from __future__ import annotations

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
from app.generation.structured_generation import StructuredGenerationRunner

logger = get_logger(__name__)


class GenerationError(Exception):
    pass


class GroundedAnswerGenerator(AnswerGeneratorInterface):
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client
        self._runner = StructuredGenerationRunner(llm_client)

    def generate(
        self, question: str, evidence_bundle: EvidenceBundleDomain
    ) -> AnswerDraftDomain:
        user_prompt = build_answer_user_prompt(question, evidence_bundle)
        valid_ids = {a.passage_id for a in evidence_bundle.anchors}
        result = self._runner.run(
            system_prompt=ANSWER_GENERATOR_SYSTEM,
            user_prompt=user_prompt,
            output_model=AnswerGeneratorOutput,
            schema_label="answer generator output",
        )

        if result.parsed is None:
            logger.warning(
                "Falling back to deterministic extractive answer for query %r after %s attempts: %s",
                question[:120],
                result.attempts,
                result.failure_reason,
            )
            return self._build_fallback_answer(evidence_bundle)

        output = result.parsed
        self._filter_hallucinated_passage_ids(output, valid_ids)
        return self._to_domain(output)

    def _filter_hallucinated_passage_ids(
        self,
        output: AnswerGeneratorOutput,
        valid_ids: set[str],
    ) -> None:
        bad_ids = set(output.validate_passage_ids(valid_ids))
        if bad_ids:
            logger.warning("Hallucinated passage IDs detected: %s", bad_ids)
            for claim in output.claims:
                claim.supporting_passage_ids = [
                    pid for pid in claim.supporting_passage_ids if pid not in bad_ids
                ]
            output.supporting_citations = [
                c for c in output.supporting_citations if c.passage_id not in bad_ids
            ]

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
