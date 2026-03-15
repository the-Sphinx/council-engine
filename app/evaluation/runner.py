"""
Eval runner: runs the full pipeline on an eval dataset and computes metrics.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.core.interfaces import AnswerGeneratorInterface, VerifierInterface
from app.core.logging import get_logger
from app.evaluation.dataset import EvalItem, load_eval_dataset
from app.evaluation.grounding_metrics import compute_grounding_metrics
from app.evaluation.metrics import compute_retrieval_metrics
from app.retrieval.pipeline import RetrievalPipeline

logger = get_logger(__name__)


@dataclass
class EvalItemResult:
    eval_id: str
    question: str
    category: str
    retrieved_ids: list[str]
    retrieval_metrics: dict
    grounding_metrics: Optional[dict]
    verifier_status: Optional[str]
    error: Optional[str]


@dataclass
class EvalRun:
    run_id: str
    label: Optional[str]
    project_id: str
    eval_dataset_path: str
    timestamp: str
    total_items: int
    results: list[EvalItemResult]
    aggregate_metrics: dict


def run_eval(
    project_id: str,
    eval_dataset_path: Path,
    db: Session,
    pipeline: RetrievalPipeline,
    generator: AnswerGeneratorInterface,
    verifier: VerifierInterface,
    run_id: Optional[str] = None,
    label: Optional[str] = None,
    output_path: Optional[Path] = None,
) -> EvalRun:
    if run_id is None:
        run_id = str(uuid.uuid4())
    if output_path is None:
        output_path = Path(f"data/eval_runs/eval_{run_id}.json")

    eval_items = load_eval_dataset(eval_dataset_path)
    logger.info("Running eval: %d items, run_id=%s", len(eval_items), run_id)

    results: list[EvalItemResult] = []

    for item in eval_items:
        result = _run_single(item, project_id, pipeline, generator, verifier, db)
        results.append(result)

        status = result.verifier_status or "N/A"
        h10 = result.retrieval_metrics.get("hit@10", 0)
        logger.info(
            "  [%s] %-45s | hit@10=%.1f | verifier=%s",
            item.category,
            item.question[:45],
            h10,
            status,
        )

    aggregate = _aggregate(results)
    run = EvalRun(
        run_id=run_id,
        label=label,
        project_id=project_id,
        eval_dataset_path=str(eval_dataset_path),
        timestamp=datetime.utcnow().isoformat(),
        total_items=len(eval_items),
        results=results,
        aggregate_metrics=aggregate,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(_run_to_dict(run), f, indent=2, ensure_ascii=False)

    _print_summary(run)
    return run


def _run_single(
    item: EvalItem,
    project_id: str,
    pipeline: RetrievalPipeline,
    generator: AnswerGeneratorInterface,
    verifier: VerifierInterface,
    db: Session,
) -> EvalItemResult:
    try:
        # Use a dummy query_id for eval (not persisted as a real query)
        from app.db.models import Query
        q = Query(project_id=project_id, question_text=item.question, mode="source_only")
        db.add(q)
        db.flush()
        query_id = q.id

        bundle, debug = pipeline.run(query_id=query_id, question=item.question, db=db)
        db.rollback()  # Don't persist eval queries

        retrieved_ids = [a.passage_id for a in bundle.anchors]
        # Also include window passage IDs for recall calculation
        all_retrieved = list(dict.fromkeys(
            retrieved_ids + [pid for a in bundle.anchors for pid in a.window_passage_ids]
        ))

        expected = set(item.expected_relevant_passage_ids)
        alternatives = set(item.acceptable_alternative_passage_ids)
        retrieval_metrics = compute_retrieval_metrics(all_retrieved, expected, alternatives)

        # Answer generation + verification
        grounding_metrics = None
        verifier_status = None
        try:
            draft = generator.generate(item.question, bundle)
            report = verifier.verify(item.question, bundle, draft)
            valid_ids = {a.passage_id for a in bundle.anchors}
            grounding_metrics = compute_grounding_metrics(draft, report, valid_ids)
            verifier_status = report.status
        except Exception as e:
            logger.warning("Generation/verification failed for %s: %s", item.id, e)

        return EvalItemResult(
            eval_id=item.id,
            question=item.question,
            category=item.category,
            retrieved_ids=all_retrieved,
            retrieval_metrics=retrieval_metrics,
            grounding_metrics=grounding_metrics,
            verifier_status=verifier_status,
            error=None,
        )

    except Exception as e:
        db.rollback()
        logger.error("Eval item %s failed: %s", item.id, e)
        return EvalItemResult(
            eval_id=item.id,
            question=item.question,
            category=item.category,
            retrieved_ids=[],
            retrieval_metrics={},
            grounding_metrics=None,
            verifier_status=None,
            error=str(e),
        )


def _aggregate(results: list[EvalItemResult]) -> dict:
    valid = [r for r in results if not r.error]
    if not valid:
        return {}

    def avg(key):
        vals = [r.retrieval_metrics.get(key, 0) for r in valid]
        return round(sum(vals) / len(vals), 4)

    agg = {
        "total": len(results),
        "successful": len(valid),
        "failed": len(results) - len(valid),
        "hit@5": avg("hit@5"),
        "hit@10": avg("hit@10"),
        "hit@20": avg("hit@20"),
        "recall@10": avg("recall@10"),
        "precision@10": avg("precision@10"),
        "mrr": avg("mrr"),
    }

    grounding = [r for r in valid if r.grounding_metrics]
    if grounding:
        agg["citation_validity_rate"] = round(
            sum(r.grounding_metrics["citation_validity_rate"] for r in grounding) / len(grounding), 4
        )
        agg["claim_support_rate"] = round(
            sum(r.grounding_metrics["claim_support_rate"] for r in grounding) / len(grounding), 4
        )
        agg["avg_unsupported_claims"] = round(
            sum(r.grounding_metrics["unsupported_claim_count"] for r in grounding) / len(grounding), 2
        )

    return agg


def _print_summary(run: EvalRun) -> None:
    m = run.aggregate_metrics
    print(f"\n{'='*60}")
    print(f"Eval Run: {run.run_id}")
    print(f"Label: {run.label or 'unlabeled'}")
    print(f"Total: {m.get('total')} | Successful: {m.get('successful')} | Failed: {m.get('failed')}")
    print(f"{'='*60}")
    print(f"Retrieval:")
    print(f"  Hit@5:       {m.get('hit@5', 0):.4f}")
    print(f"  Hit@10:      {m.get('hit@10', 0):.4f}")
    print(f"  Hit@20:      {m.get('hit@20', 0):.4f}")
    print(f"  Recall@10:   {m.get('recall@10', 0):.4f}")
    print(f"  MRR:         {m.get('mrr', 0):.4f}")
    if "citation_validity_rate" in m:
        print(f"Grounding:")
        print(f"  Citation validity: {m.get('citation_validity_rate', 0):.4f}")
        print(f"  Claim support:     {m.get('claim_support_rate', 0):.4f}")
        print(f"  Avg unsupported:   {m.get('avg_unsupported_claims', 0):.2f}")
    print(f"{'='*60}\n")


def _run_to_dict(run: EvalRun) -> dict:
    return {
        "run_id": run.run_id,
        "label": run.label,
        "project_id": run.project_id,
        "eval_dataset_path": run.eval_dataset_path,
        "timestamp": run.timestamp,
        "total_items": run.total_items,
        "aggregate_metrics": run.aggregate_metrics,
        "results": [
            {
                "eval_id": r.eval_id,
                "question": r.question,
                "category": r.category,
                "retrieved_ids": r.retrieved_ids,
                "retrieval_metrics": r.retrieval_metrics,
                "grounding_metrics": r.grounding_metrics,
                "verifier_status": r.verifier_status,
                "error": r.error,
            }
            for r in run.results
        ],
    }
