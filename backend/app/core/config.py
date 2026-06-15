"""Application configuration via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ─── Application ────────────────────────────────────────────────────
    app_env: Literal["development", "staging", "production"] = "development"
    app_secret_key: str = "change-me-in-production"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    frontend_url: str = "http://localhost:3000"

    # ─── Database ───────────────────────────────────────────────────────
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "aeka"
    postgres_password: str = "aeka_dev_password"
    postgres_db: str = "aeka"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ─── Redis ──────────────────────────────────────────────────────────
    redis_host: str = "localhost"
    redis_port: int = 6379

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # ─── Object Storage ─────────────────────────────────────────────────
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "aeka-documents"
    aws_region: str = "us-east-1"

    # ─── LLM ────────────────────────────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""

    default_llm_provider: Literal["openai", "anthropic", "google"] = "openai"
    default_llm_model: str = "gpt-4o"
    fallback_llm_provider: Literal["openai", "anthropic", "google"] = "anthropic"
    fallback_llm_model: str = "claude-sonnet-4-6-20250514"

    # ─── Embeddings ─────────────────────────────────────────────────────
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ─── Observability ──────────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "aeka-backend"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
