"""
Application settings.

All configuration is loaded from environment variables using pydantic-settings.
Variables are grouped by service/concern for clarity.

Precedence (highest → lowest):
    1. Environment variables
    2. .env file
    3. Default values defined here
"""

from functools import lru_cache
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Type-safe application configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # -------------------------------------------------------------------------
    # Application
    # -------------------------------------------------------------------------
    APP_NAME: str = "AI Workspace"
    APP_DESCRIPTION: str = "A production-ready AI knowledge workspace."
    APP_VERSION: str = "0.1.0"

    # -------------------------------------------------------------------------
    # Environment
    # -------------------------------------------------------------------------
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    # -------------------------------------------------------------------------
    # Server & CORS
    # -------------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # -------------------------------------------------------------------------
    # Database — PostgreSQL
    # -------------------------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "aiworkspace"
    POSTGRES_PASSWORD: str = "aiworkspace"
    POSTGRES_DB: str = "aiworkspace"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # -------------------------------------------------------------------------
    # Cache — Redis
    # -------------------------------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"

    # -------------------------------------------------------------------------
    # Object Storage — MinIO
    # -------------------------------------------------------------------------
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "ai-workspace"
    MINIO_SECURE: bool = False

    # -------------------------------------------------------------------------
    # Vector Database — Qdrant
    # -------------------------------------------------------------------------
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # -------------------------------------------------------------------------
    # LLM Provider
    # Supported: openai | gemini | groq | openrouter | ollama
    # -------------------------------------------------------------------------
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""
    GOOGLE_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""

    # -------------------------------------------------------------------------
    # Security — JWT
    # -------------------------------------------------------------------------
    SECRET_KEY: str = "change-me-in-production-use-a-long-random-string"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @model_validator(mode="after")
    def validate_production_secret(self) -> "Settings":
        """Prevent the documented development secret from reaching production."""
        if self.is_production and self.SECRET_KEY == "change-me-in-production-use-a-long-random-string":
            raise ValueError("SECRET_KEY must be set to a unique value in production.")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings instance. Safe to call anywhere."""
    return Settings()
