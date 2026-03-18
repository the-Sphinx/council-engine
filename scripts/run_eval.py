#!/usr/bin/env python3
"""
CLI eval runner.

Usage:
    python scripts/run_eval.py \
        --project-id <uuid> \
        --eval-dataset data/evals/quran_eval_v1.json \
        --label baseline_v1
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    parser = argparse.ArgumentParser(description="Run Heyet evaluation")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--eval-dataset", required=True, type=Path)
    parser.add_argument("--label", default=None)
    parser.add_argument("--no-generation", action="store_true",
                        help="Skip generation/verification, retrieval metrics only")
    args = parser.parse_args()

    if not args.eval_dataset.exists():
        print(f"ERROR: Eval dataset not found: {args.eval_dataset}")
        sys.exit(1)

    from app.core.config import settings
    from app.db.bootstrap import ensure_database_ready
    from app.db.session import SessionLocal, engine
    from app.ingestion.indexer import IndexManager

    ensure_database_ready(engine)
    db = SessionLocal()

    # Load index
    index_dir = settings.INDICES_DIR / args.project_id
    if not index_dir.exists():
        print(f"ERROR: No index found for project {args.project_id}")
        print(f"  Expected: {index_dir}")
        print("  Run POST /api/projects/{project_id}/index first")
        sys.exit(1)

    im = IndexManager(index_dir)
    if not im.load():
        print(f"ERROR: Could not load index from {index_dir}")
        sys.exit(1)

    from app.retrieval.dense import NumpyDenseRetriever, SentenceTransformerEmbedder
    from app.retrieval.lexical import BM25Retriever
    from app.retrieval.pipeline import RetrievalPipeline
    from app.retrieval.reranker import get_reranker

    retrieval_cfg = settings.get_retrieval_config()
    embedder = SentenceTransformerEmbedder(settings.EMBEDDER_MODEL)
    lexical = BM25Retriever(im)
    dense = NumpyDenseRetriever(im, embedder)
    reranker = get_reranker(retrieval_cfg.reranker_enabled, settings.RERANKER_MODEL)
    pipeline = RetrievalPipeline(lexical, dense, reranker, retrieval_cfg)

    if args.no_generation:
        from app.generation.answer_generator import GroundedAnswerGenerator
        from app.generation.verifier import LLMVerifier

        class NoOpGenerator:
            def generate(self, question, bundle):
                from app.core.interfaces import AnswerDraftDomain
                return AnswerDraftDomain(
                    final_answer="[skipped]", claims=[], supporting_citations=[],
                    objections_raised=[], confidence_notes=""
                )

        class NoOpVerifier:
            def verify(self, question, bundle, draft):
                from app.core.interfaces import VerificationReportDomain
                return VerificationReportDomain(
                    status="pass", supported_claims=[], unsupported_claims=[],
                    citation_issues=[], notes=""
                )

        generator = NoOpGenerator()
        verifier = NoOpVerifier()
    else:
        from app.generation.answer_generator import GroundedAnswerGenerator
        from app.generation.llm_client import get_llm_client
        from app.generation.verifier import LLMVerifier
        llm = get_llm_client(settings)
        generator = GroundedAnswerGenerator(llm)
        verifier = LLMVerifier(llm)

    from app.evaluation.runner import run_eval
    run_eval(
        project_id=args.project_id,
        eval_dataset_path=args.eval_dataset,
        db=db,
        pipeline=pipeline,
        generator=generator,
        verifier=verifier,
        label=args.label,
    )

    db.close()


if __name__ == "__main__":
    main()
