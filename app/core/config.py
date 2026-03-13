from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "kordocqa"
    app_env: Literal["local", "dev", "prod", "test"] = "local"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://kordocqa:kordocqa@localhost:5432/kordocqa"
    redis_url: str = "redis://localhost:6379/0"

    admin_token: Optional[str] = None

    provider_name: str = "openai"
    openai_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-large"
    llm_model: str = "gpt-4.1-mini"
    embedding_dimension: int = Field(default=1536, ge=1)

    enable_tracing: bool = False
    langfuse_public_key: Optional[str] = None
    langfuse_secret_key: Optional[str] = None
    langfuse_host: Optional[str] = None

    max_upload_size_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    chunk_size_chars: int = Field(default=700, ge=100)
    chunk_overlap_chars: int = Field(default=80, ge=0)
    retrieval_trigram_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    embedding_index_batch_size: int = Field(default=32, ge=1, le=512)
    embedding_auto_index_max_chunks: int = Field(default=500, ge=1)
    query_top_k: int = Field(default=5, ge=1, le=50)
    query_lexical_k: int = Field(default=20, ge=1, le=200)
    query_semantic_k: int = Field(default=20, ge=1, le=200)
    query_prompt_version: Literal["v1", "v2"] = "v1"
    eval_default_dataset_path: str = "app/evals/datasets/ko_sample_eval.jsonl"
    eval_reports_dir: str = "app/evals/reports"
    eval_cache_prefix: str = "evals"
    eval_cache_ttl_seconds: int = Field(default=300, ge=0, le=86400)

    @model_validator(mode="after")
    def validate_chunking(self) -> "Settings":
        if self.chunk_overlap_chars >= self.chunk_size_chars:
            raise ValueError("CHUNK_OVERLAP_CHARS must be smaller than CHUNK_SIZE_CHARS.")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
