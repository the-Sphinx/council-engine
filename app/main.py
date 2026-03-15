"""
FastAPI app factory with lifespan.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import Base, engine

logger = get_logger(__name__)

# Global state: loaded index managers per project
_index_managers: dict[str, object] = {}
_generator = None
_verifier = None


def reload_project_index(project_id: str, index_manager) -> None:
    _index_managers[project_id] = index_manager
    logger.info("Reloaded index for project %s", project_id)


def get_pipeline_for_project(project_id: str):
    """Returns a RetrievalPipeline for the given project, or raises KeyError."""
    if project_id not in _index_managers:
        raise KeyError(f"No index for project {project_id}")

    from app.core.config import settings
    from app.ingestion.indexer import IndexManager
    from app.retrieval.dense import NumpyDenseRetriever, SentenceTransformerEmbedder
    from app.retrieval.lexical import BM25Retriever
    from app.retrieval.pipeline import RetrievalPipeline
    from app.retrieval.reranker import get_reranker

    im = _index_managers[project_id]
    retrieval_cfg = settings.get_retrieval_config()

    embedder = SentenceTransformerEmbedder(settings.EMBEDDER_MODEL)
    lexical = BM25Retriever(im)
    dense = NumpyDenseRetriever(im, embedder)
    reranker = get_reranker(retrieval_cfg.reranker_enabled, settings.RERANKER_MODEL)

    return RetrievalPipeline(
        lexical_retriever=lexical,
        dense_retriever=dense,
        reranker=reranker,
        config=retrieval_cfg,
    )


def get_generator():
    global _generator
    if _generator is None:
        from app.generation.answer_generator import GroundedAnswerGenerator
        from app.generation.llm_client import get_llm_client
        _generator = GroundedAnswerGenerator(get_llm_client(settings))
    return _generator


def get_verifier():
    global _verifier
    if _verifier is None:
        from app.generation.verifier import LLMVerifier
        from app.generation.llm_client import get_llm_client
        _verifier = LLMVerifier(get_llm_client(settings))
    return _verifier


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Heyet — Source-Grounded Q&A")

    # Ensure required directories exist
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.INDICES_DIR.mkdir(parents=True, exist_ok=True)
    (settings.DATA_DIR / "eval_runs").mkdir(parents=True, exist_ok=True)

    # Create DB tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables ready")

    # Load existing indices from disk
    _load_all_indices()

    yield

    # Shutdown
    logger.info("Shutting down Heyet")


def _load_all_indices() -> None:
    """At startup, load all indices found on disk into memory."""
    if not settings.INDICES_DIR.exists():
        return

    from app.ingestion.indexer import IndexManager

    for project_dir in settings.INDICES_DIR.iterdir():
        if project_dir.is_dir():
            project_id = project_dir.name
            im = IndexManager(project_dir)
            if im.load():
                _index_managers[project_id] = im
                logger.info("Loaded index for project %s", project_id)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Heyet",
        description="Source-Grounded Q&A API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routers
    from app.api import documents, evals, projects, queries

    app.include_router(projects.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(queries.router, prefix="/api")
    app.include_router(evals.router, prefix="/api")

    # Serve UI
    ui_dir = Path(__file__).parent.parent / "ui"
    if ui_dir.exists():
        app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")

    return app


app = create_app()
