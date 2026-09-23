"""
RFPANDA - Configuration Management (Pydantic Settings)
Loads and validates environment variables for Supabase, Voyage AI, Groq, and runtime policies.
"""

import os
import json
from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application runtime configuration loaded from environment variables and .env file.
    """
    # Environment & Server
    ENVIRONMENT: str = Field(default="development", description="Application environment: development | staging | production | test")
    HOST: str = Field(default="0.0.0.0", description="Host address to bind server")
    PORT: int = Field(default=8000, description="Port number to bind server")
    DEBUG: bool = Field(default=False, description="Debug mode flag")
    TEST_MODE: bool = Field(default=False, description="Test mode flag allowing deterministic mock responses")

    # Supabase Configuration
    SUPABASE_URL: str = Field(default="https://mock.supabase.co", description="Supabase project base URL")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="mock-service-role-key", description="Supabase service role secret key")
    SUPABASE_ANON_KEY: str = Field(default="mock-anon-key", description="Supabase anonymous client key")
    SUPABASE_JWT_SECRET: str = Field(default="", description="Supabase JWT signature secret (HS256). REQUIRED for production.")

    # Voyage AI Configuration
    VOYAGE_API_KEY: str = Field(default="voyage-mock-api-key", description="Voyage AI API key")
    VOYAGE_API_URL: str = Field(default="https://api.voyageai.com/v1/embeddings", description="Voyage AI embeddings endpoint")
    VOYAGE_MODEL: str = Field(default="voyage-3", description="Voyage embedding model (1024d output)")
    VOYAGE_MAX_RETRIES: int = Field(default=3, description="Maximum retry count on Voyage rate limits / 5xx")
    VOYAGE_TIMEOUT_SECONDS: float = Field(default=15.0, description="HTTP timeout for Voyage AI calls")

    # Groq Cloud Configuration
    GROQ_API_KEY: str = Field(default="groq-mock-api-key", description="Groq Cloud API key")
    GROQ_API_URL: str = Field(default="https://api.groq.com/openai/v1", description="Groq Cloud base URL")
    GROQ_MODEL: str = Field(default="llama-3.3-70b-versatile", description="Default Groq LLM model")
    GROQ_FALLBACK_MODEL: str = Field(default="llama-3.1-8b-instant", description="Fast fallback Groq LLM model")
    GROQ_TIMEOUT_SECONDS: float = Field(default=30.0, description="Timeout for Groq streaming responses")

    # RAG Search & Similarity Thresholds
    DEFAULT_MATCH_COUNT: int = Field(default=5, description="Default number of chunks retrieved by match_documents")
    DEFAULT_SIMILARITY_THRESHOLD: float = Field(default=0.25, description="Default minimum cosine similarity score")
    MAX_MATCH_COUNT: int = Field(default=20, description="Upper bound on retrieved chunks count")

    # Memory & Health Limits (Render Free Tier 512MB RAM cap)
    MEMORY_TARGET_LIMIT_MB: float = Field(default=300.0, description="Hard target RAM limit in MB (must remain <300MB)")

    # Security & CORS
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["*"],
        description="Allowed CORS origins as list of strings or comma-separated string"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, list):
            return [str(i).strip() for i in v]
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                try:
                    parsed = json.loads(v)
                    if isinstance(parsed, list):
                        return [str(i).strip() for i in parsed]
                except json.JSONDecodeError:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        raise ValueError(v)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Factory function returning cached Settings instance.
    """
    return Settings()


settings = get_settings()
