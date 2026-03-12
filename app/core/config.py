from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field
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


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
