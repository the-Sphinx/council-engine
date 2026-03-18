from pathlib import Path
from typing import Optional

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetrievalConfig:
    def __init__(self, data: dict, settings: "Settings | None" = None):
        r = data.get("retrieval", {})
        self.top_k_lexical: int = r.get("top_k_lexical", 30)
        self.top_k_dense: int = r.get("top_k_dense", 30)
        self.top_k_rerank: int = r.get("top_k_rerank", 25)
        self.reranker_top_k: int = _override_or_default(
            settings,
            "RETRIEVAL_RERANKER_TOP_K",
            r.get("reranker_top_k", self.top_k_rerank),
        )
        self.top_k_anchors: int = r.get("top_k_anchors", 6)
        self.hybrid_alpha: float = _override_or_default(
            settings,
            "RETRIEVAL_HYBRID_ALPHA",
            r.get("hybrid_alpha", r.get("lexical_weight", 0.5)),
        )
        self.hybrid_beta: float = _override_or_default(
            settings,
            "RETRIEVAL_HYBRID_BETA",
            r.get("hybrid_beta", r.get("dense_weight", 0.5)),
        )
        self.lexical_weight: float = self.hybrid_alpha
        self.dense_weight: float = self.hybrid_beta
        self.context_window_radius: int = r.get("context_window_radius", 1)
        self.max_bundle_passages: int = r.get("max_bundle_passages", 12)
        self.min_anchor_score: Optional[float] = r.get("min_anchor_score", None)
        self.reranker_enabled: bool = _override_or_default(
            settings,
            "RETRIEVAL_RERANKER_ENABLED",
            r.get("reranker_enabled", True),
        )
        self.overlap_boost_enabled: bool = _override_or_default(
            settings,
            "RETRIEVAL_OVERLAP_BOOST_ENABLED",
            r.get("overlap_boost_enabled", False),
        )
        self.overlap_boost_value: float = _override_or_default(
            settings,
            "RETRIEVAL_OVERLAP_BOOST_VALUE",
            r.get("overlap_boost_value", 0.05),
        )
        self.lexical_query_expansion_enabled: bool = r.get(
            "lexical_query_expansion_enabled",
            True,
        )
        self.lexical_query_expansions: dict[str, list[str]] = r.get(
            "lexical_query_expansions",
            {},
        )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = "sqlite:///./heyet.db"
    DATA_DIR: Path = Path("./data")
    INDICES_DIR: Path = Path("./data/indices")
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "qwen2.5:7b"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_TIMEOUT_SECONDS: float = 45.0
    EMBEDDER_MODEL: str = "all-MiniLM-L6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RETRIEVAL_HYBRID_ALPHA: Optional[float] = None
    RETRIEVAL_HYBRID_BETA: Optional[float] = None
    RETRIEVAL_OVERLAP_BOOST_ENABLED: Optional[bool] = None
    RETRIEVAL_OVERLAP_BOOST_VALUE: Optional[float] = None
    RETRIEVAL_RERANKER_ENABLED: Optional[bool] = None
    RETRIEVAL_RERANKER_TOP_K: Optional[int] = None
    LOG_LEVEL: str = "INFO"
    CONFIG_YAML: Path = Path("./config.yaml")

    @field_validator("DATA_DIR", "INDICES_DIR", mode="before")
    @classmethod
    def make_path(cls, v):
        return Path(v)

    def get_retrieval_config(self) -> RetrievalConfig:
        if self.CONFIG_YAML.exists():
            with open(self.CONFIG_YAML) as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}
        return RetrievalConfig(data, settings=self)


def _override_or_default(settings: "Settings | None", name: str, default):
    if settings is None:
        return default
    value = getattr(settings, name, None)
    return default if value is None else value


settings = Settings()
