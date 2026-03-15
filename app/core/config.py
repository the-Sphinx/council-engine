from pathlib import Path
from typing import Optional

import yaml
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class RetrievalConfig:
    def __init__(self, data: dict):
        r = data.get("retrieval", {})
        self.top_k_lexical: int = r.get("top_k_lexical", 30)
        self.top_k_dense: int = r.get("top_k_dense", 30)
        self.top_k_rerank: int = r.get("top_k_rerank", 25)
        self.top_k_anchors: int = r.get("top_k_anchors", 6)
        self.lexical_weight: float = r.get("lexical_weight", 0.5)
        self.dense_weight: float = r.get("dense_weight", 0.5)
        self.context_window_radius: int = r.get("context_window_radius", 1)
        self.max_bundle_passages: int = r.get("max_bundle_passages", 12)
        self.min_anchor_score: Optional[float] = r.get("min_anchor_score", None)
        self.reranker_enabled: bool = r.get("reranker_enabled", True)


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
    LLM_MODEL: str = "llama3.1:8b"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_TIMEOUT_SECONDS: float = 45.0
    EMBEDDER_MODEL: str = "all-MiniLM-L6-v2"
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
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
        return RetrievalConfig(data)


settings = Settings()
