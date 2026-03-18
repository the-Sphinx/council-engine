#!/usr/bin/env python3
"""
Run local model evaluation over a question set and record structured-generation metrics.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from collections import Counter
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


def _verse_prefix(text: str) -> str | None:
    if "|" not in text:
        return None
    parts = text.split("|", 2)
    if len(parts) < 2:
        return None
    if parts[0].isdigit() and parts[1].isdigit():
        return f"{parts[0]}|{parts[1]}"
    return None


def _resolve_expected_passage_ids(
    db,
    project_id: str,
    verse_refs: list[str],
) -> list[str]:
    if not verse_refs:
        return []

    from app.db.models import Passage, Document

    passages = (
        db.query(Passage.id, Passage.text)
        .join(Document, Passage.document_id == Document.id)
        .filter(Document.project_id == project_id)
        .all()
    )
    by_ref: dict[str, str] = {}
    for passage_id, text in passages:
        prefix = _verse_prefix(text)
        if prefix and prefix not in by_ref:
            by_ref[prefix] = passage_id
    return [by_ref[ref] for ref in verse_refs if ref in by_ref]


def _classify_failure(
    expected_ids: set[str],
    lexical_ids: list[str],
    dense_ids: list[str],
    merged_ids: list[str],
    reranked_ids: list[str],
    top_k: int = 10,
) -> str:
    if not expected_ids:
        return "unknown"
    lexical_set = set(lexical_ids[:top_k])
    dense_set = set(dense_ids[:top_k])
    merged_set = set(merged_ids[:top_k])
    reranked_set = set(reranked_ids[:top_k])

    if expected_ids & reranked_set:
        return "none"
    if not (expected_ids & lexical_set):
        return "lexical_miss"
    if not (expected_ids & dense_set):
        return "dense_miss"
    if (expected_ids & merged_set) and not (expected_ids & reranked_set):
        return "rerank_miss"
    return "unknown"


def _candidate_debug_rows(candidates: list, top_k: int = 10) -> list[dict]:
    rows = []
    for candidate in candidates[:top_k]:
        rows.append(
            {
                "passage_id": candidate.passage_id,
                "lexical_score": candidate.lexical_score,
                "dense_score": candidate.dense_score,
                "lexical_score_normalized": candidate.lexical_score_normalized,
                "dense_score_normalized": candidate.dense_score_normalized,
                "overlap_matched": candidate.overlap_matched,
                "overlap_boost": candidate.overlap_boost,
                "hybrid_score": candidate.hybrid_score,
                "rerank_score": candidate.rerank_score,
                "rank_lexical": candidate.rank_lexical,
                "rank_dense": candidate.rank_dense,
                "rank_hybrid": candidate.rank_hybrid,
                "rank_rerank": candidate.rank_rerank,
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Run model comparison eval for Heyet")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--dataset", type=Path, default=Path("data/evals/questions.json"))
    parser.add_argument("--model", default=None, help="Override LLM model name for this run")
    parser.add_argument("--label", default=None)
    parser.add_argument("--max-items", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, default=Path("data/evals/results"))
    parser.add_argument("--debug-dir", type=Path, default=Path("data/evals/debug"))
    parser.add_argument("--no-generation", action="store_true")
    parser.add_argument("--hybrid-alpha", type=float, default=None)
    parser.add_argument("--hybrid-beta", type=float, default=None)
    parser.add_argument("--reranker-top-k", type=int, default=None)
    parser.add_argument("--overlap-boost-value", type=float, default=None)
    parser.add_argument("--enable-overlap-boost", action="store_true")
    parser.add_argument("--disable-overlap-boost", action="store_true")
    parser.add_argument("--enable-reranker", action="store_true")
    parser.add_argument("--disable-reranker", action="store_true")
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"ERROR: Eval dataset not found: {args.dataset}")
        sys.exit(1)

    from app.core.config import settings
    from app.db.bootstrap import ensure_database_ready
    from app.db.session import SessionLocal, engine
    from app.generation.answer_generator import GroundedAnswerGenerator
    from app.generation.llm_client import get_llm_client
    from app.generation.verifier import LLMVerifier
    from app.ingestion.indexer import IndexManager
    from app.retrieval.dense import NumpyDenseRetriever, SentenceTransformerEmbedder
    from app.retrieval.lexical import BM25Retriever
    from app.retrieval.pipeline import RetrievalPipeline
    from app.retrieval.reranker import get_reranker

    ensure_database_ready(engine)
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
    if args.hybrid_alpha is not None:
        retrieval_cfg.hybrid_alpha = args.hybrid_alpha
        retrieval_cfg.lexical_weight = args.hybrid_alpha
    if args.hybrid_beta is not None:
        retrieval_cfg.hybrid_beta = args.hybrid_beta
        retrieval_cfg.dense_weight = args.hybrid_beta
    if args.reranker_top_k is not None:
        retrieval_cfg.reranker_top_k = args.reranker_top_k
    if args.enable_overlap_boost:
        retrieval_cfg.overlap_boost_enabled = True
    if args.disable_overlap_boost:
        retrieval_cfg.overlap_boost_enabled = False
    if args.overlap_boost_value is not None:
        retrieval_cfg.overlap_boost_value = args.overlap_boost_value
    if args.enable_reranker:
        retrieval_cfg.reranker_enabled = True
    if args.disable_reranker:
        retrieval_cfg.reranker_enabled = False

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
    args.debug_dir.mkdir(parents=True, exist_ok=True)
    for item in questions:
        query_result = {
            "id": item["id"],
            "question": item["question"],
            "category": item.get("category", "general"),
            "expected_passage_ids": [],
            "retrieved_passage_ids": [],
            "hit_at_5": False,
            "hit_at_10": False,
            "failure": False,
            "failure_type": None,
            "model_used": model_name,
            "answer": None,
            "verifier": None,
            "verification_status": None,
            "error": None,
            "experiment": {
                "label": args.label,
                "hybrid_alpha": retrieval_cfg.hybrid_alpha,
                "hybrid_beta": retrieval_cfg.hybrid_beta,
                "overlap_boost_enabled": retrieval_cfg.overlap_boost_enabled,
                "overlap_boost_value": retrieval_cfg.overlap_boost_value,
                "reranker_enabled": retrieval_cfg.reranker_enabled,
                "reranker_top_k": retrieval_cfg.reranker_top_k,
                "reranker_model": settings.RERANKER_MODEL,
            },
        }
        try:
            query_id = str(uuid.uuid4())

            expected_passage_ids = _resolve_expected_passage_ids(
                db,
                args.project_id,
                item.get("expected_verse_refs", []),
            )
            bundle, debug = pipeline.run(query_id=query_id, question=item["question"], db=db)
            db.rollback()

            lexical_ids = [c.passage_id for c in debug.lexical_candidates]
            dense_ids = [c.passage_id for c in debug.dense_candidates]
            merged_ids = [c.passage_id for c in debug.merged_candidates]
            reranked_ids = [c.passage_id for c in debug.reranked_candidates]
            top_k_ids = reranked_ids[:10]
            expected_set = set(expected_passage_ids)
            hit_at_5 = bool(expected_set & set(reranked_ids[:5])) if expected_set else False
            hit_at_10 = bool(expected_set & set(top_k_ids)) if expected_set else False
            failure_type = _classify_failure(
                expected_ids=expected_set,
                lexical_ids=lexical_ids,
                dense_ids=dense_ids,
                merged_ids=merged_ids,
                reranked_ids=reranked_ids,
                top_k=10,
            )
            failure = bool(expected_passage_ids) and not hit_at_10

            debug_payload = {
                "query_id": query_id,
                "query": item["question"],
                "original_query": debug.original_query,
                "normalized_query": debug.normalized_query,
                "lexical_query": debug.lexical_query,
                "expanded_terms": debug.expanded_terms,
                "experiment": {
                    "label": args.label,
                    "hybrid_alpha": debug.hybrid_alpha,
                    "hybrid_beta": debug.hybrid_beta,
                    "overlap_boost_enabled": debug.overlap_boost_enabled,
                    "overlap_boost_value": debug.overlap_boost_value,
                    "reranker_enabled": debug.reranker_enabled,
                    "reranker_top_k": debug.reranker_top_k,
                    "reranker_model": settings.RERANKER_MODEL,
                },
                "model_used": model_name,
                "expected_passage_ids": expected_passage_ids,
                "top_lexical_ids": lexical_ids[:10],
                "top_dense_ids": dense_ids[:10],
                "merged_ids": merged_ids[:10],
                "reranked_ids": top_k_ids,
                "top_lexical_candidates": _candidate_debug_rows(debug.lexical_candidates),
                "top_dense_candidates": _candidate_debug_rows(debug.dense_candidates),
                "top_merged_candidates": _candidate_debug_rows(debug.merged_candidates),
                "top_reranked_candidates": _candidate_debug_rows(debug.reranked_candidates),
                "hit_at_5": hit_at_5,
                "hit_at_10": hit_at_10,
                "failure": failure,
                "failure_type": failure_type if failure else None,
            }
            with open(args.debug_dir / f"{query_id}.json", "w") as f:
                json.dump(debug_payload, f, indent=2, ensure_ascii=False)

            query_result["expected_passage_ids"] = expected_passage_ids
            query_result["retrieved_passage_ids"] = top_k_ids
            query_result["hit_at_5"] = hit_at_5
            query_result["hit_at_10"] = hit_at_10
            query_result["failure"] = failure
            query_result["failure_type"] = failure_type if failure else None

            if not args.no_generation:
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
    hit_at_5_count = sum(1 for r in query_results if r.get("hit_at_5"))
    hit_at_10_count = sum(1 for r in query_results if r.get("hit_at_10"))
    failures = [r for r in query_results if r.get("failure")]
    failure_counts = Counter(r.get("failure_type") or "unknown" for r in failures)
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
        "hybrid_alpha": retrieval_cfg.hybrid_alpha,
        "hybrid_beta": retrieval_cfg.hybrid_beta,
        "overlap_boost_enabled": retrieval_cfg.overlap_boost_enabled,
        "overlap_boost_value": retrieval_cfg.overlap_boost_value,
        "reranker_enabled": retrieval_cfg.reranker_enabled,
        "reranker_top_k": retrieval_cfg.reranker_top_k,
        "reranker_model": settings.RERANKER_MODEL,
        "timestamp": datetime.utcnow().isoformat(),
        "generation_skipped": args.no_generation,
        "total_queries": total_queries,
        "error_count": len(errors),
        "errors": [
            {"id": r["id"], "question": r["question"], "error": r["error"]}
            for r in errors
        ],
        "hit_at_5": round(hit_at_5_count / total_queries, 4) if total_queries else 0.0,
        "hit_at_10": round(hit_at_10_count / total_queries, 4) if total_queries else 0.0,
        "failure_count": len(failures),
        "failure_types": dict(failure_counts),
    }
    if args.no_generation:
        summary.update(
            {
                "fallback_count": None,
                "fallback_rate": None,
                "verifier_fallback_count": None,
                "verifier_fallback_rate": None,
                "schema_success_rate": None,
                "answer_schema_success_rate": None,
                "verifier_schema_success_rate": None,
                "average_retries_used": None,
                "answer_average_retries_used": None,
                "verifier_average_retries_used": None,
                "repair_used_count": None,
                "repair_success_count": None,
            }
        )
    else:
        summary.update(
            {
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
        )

    result = {
        "run_id": str(uuid.uuid4()),
        "summary": summary,
        "queries": query_results,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_stem = _safe_model_name(model_name)
    if args.label:
        output_stem = f"{output_stem}_{_safe_model_name(args.label)}"
    output_path = args.output_dir / f"{output_stem}_results.json"
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Saved results to {output_path}")
    db.close()


if __name__ == "__main__":
    main()
