#!/usr/bin/env python3
"""
Run local model evaluation over a question set and record structured-generation metrics.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _safe_model_name(model_name: str) -> str:
    return model_name.replace(":", "_").replace("/", "_")


def _load_questions(path: Path, max_items: int | None = None) -> list[dict]:
    with open(path) as f:
        items = json.load(f)
    if max_items is not None:
        return items[:max_items]
    return items


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 4)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run model comparison eval for Heyet")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset", type=Path, default=Path("data/evals/questions.json"))
    parser.add_argument("--model", default=None, help="Override LLM model name for this run")
    parser.add_argument("--label", default=None)
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evals/results"))
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"ERROR: Eval dataset not found: {args.dataset}")
        sys.exit(1)

    from app.core.config import settings
    from app.db.session import Base, SessionLocal, engine
    from app.generation.answer_generator import GroundedAnswerGenerator
    from app.generation.llm_client import get_llm_client
    from app.generation.verifier import LLMVerifier
    from app.ingestion.indexer import IndexManager
    from app.retrieval.dense import NumpyDenseRetriever, SentenceTransformerEmbedder
    from app.retrieval.lexical import BM25Retriever
    from app.retrieval.pipeline import RetrievalPipeline
    from app.retrieval.reranker import get_reranker

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    model_name = args.model or settings.LLM_MODEL
    index_dir = settings.INDICES_DIR / args.project_id
    if not index_dir.exists():
        print(f"ERROR: No index found for project {args.project_id} at {index_dir}")
        sys.exit(1)

    im = IndexManager(index_dir)
    if not im.load():
        print(f"ERROR: Could not load index from {index_dir}")
        sys.exit(1)

    retrieval_cfg = settings.get_retrieval_config()
    embedder = SentenceTransformerEmbedder(settings.EMBEDDER_MODEL)
    lexical = BM25Retriever(im)
    dense = NumpyDenseRetriever(im, embedder)
    reranker = get_reranker(retrieval_cfg.reranker_enabled, settings.RERANKER_MODEL)
    pipeline = RetrievalPipeline(lexical, dense, reranker, retrieval_cfg)

    llm = get_llm_client(settings, model_override=model_name)
    generator = GroundedAnswerGenerator(llm)
    verifier = LLMVerifier(llm)
    questions = _load_questions(args.dataset, max_items=args.max_items)

    query_results: list[dict] = []
    for item in questions:
        query_result = {
            "id": item["id"],
            "question": item["question"],
            "category": item.get("category", "general"),
            "answer": None,
            "verifier": None,
            "verification_status": None,
            "error": None,
        }
        try:
            from app.db.models import Query

            query = Query(
                project_id=args.project_id,
                question_text=item["question"],
                mode=item.get("mode", "source_only"),
            )
            db.add(query)
            db.flush()

            bundle, _debug = pipeline.run(query_id=query.id, question=item["question"], db=db)
            db.rollback()

            draft = generator.generate(item["question"], bundle)
            report = verifier.verify(item["question"], bundle, draft)

            query_result["answer"] = dict(generator.last_run_info or {})
            query_result["answer"]["final_answer_preview"] = draft.final_answer[:240]
            query_result["answer"]["objections"] = [o.issue for o in draft.objections_raised]
            query_result["verifier"] = dict(verifier.last_run_info or {})
            query_result["verification_status"] = report.status
            query_result["verification_notes"] = report.notes
        except Exception as exc:
            db.rollback()
            query_result["error"] = str(exc)

        query_results.append(query_result)

    total_queries = len(query_results)
    errors = [r for r in query_results if r["error"]]
    answer_results = [r["answer"] or {} for r in query_results]
    verifier_results = [r["verifier"] or {} for r in query_results]

    answer_fallback_count = sum(1 for r in answer_results if r.get("fallback_used"))
    verifier_fallback_count = sum(1 for r in verifier_results if r.get("fallback_used"))
    full_schema_success_count = sum(
        1
        for result in query_results
        if (result["answer"] or {}).get("structured_success")
        and (result["verifier"] or {}).get("structured_success")
    )
    answer_schema_success_count = sum(1 for r in answer_results if r.get("structured_success"))
    verifier_schema_success_count = sum(1 for r in verifier_results if r.get("structured_success"))

    summary = {
        "model_name": model_name,
        "label": args.label,
        "project_id": args.project_id,
        "dataset": str(args.dataset),
        "timestamp": datetime.utcnow().isoformat(),
        "total_queries": total_queries,
        "error_count": len(errors),
        "errors": [
            {"id": r["id"], "question": r["question"], "error": r["error"]}
            for r in errors
        ],
        "fallback_count": answer_fallback_count,
        "fallback_rate": round(answer_fallback_count / total_queries, 4) if total_queries else 0.0,
        "verifier_fallback_count": verifier_fallback_count,
        "verifier_fallback_rate": round(verifier_fallback_count / total_queries, 4) if total_queries else 0.0,
        "schema_success_rate": round(full_schema_success_count / total_queries, 4) if total_queries else 0.0,
        "answer_schema_success_rate": round(answer_schema_success_count / total_queries, 4) if total_queries else 0.0,
        "verifier_schema_success_rate": round(verifier_schema_success_count / total_queries, 4) if total_queries else 0.0,
        "average_retries_used": _mean(
            [max((r.get("attempts", 0) - 1), 0) for r in answer_results + verifier_results if r]
        ),
        "answer_average_retries_used": _mean(
            [max((r.get("attempts", 0) - 1), 0) for r in answer_results if r]
        ),
        "verifier_average_retries_used": _mean(
            [max((r.get("attempts", 0) - 1), 0) for r in verifier_results if r]
        ),
        "repair_used_count": sum(
            1
            for r in answer_results + verifier_results
            if r.get("repair_attempted")
        ),
        "repair_success_count": sum(
            1
            for r in answer_results + verifier_results
            if r.get("repair_succeeded")
        ),
    }

    result = {
        "run_id": str(uuid.uuid4()),
        "summary": summary,
        "queries": query_results,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"{_safe_model_name(model_name)}_results.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Saved results to {output_path}")
    db.close()


if __name__ == "__main__":
    main()
