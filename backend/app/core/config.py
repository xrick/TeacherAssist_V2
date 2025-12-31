"""
Configuration management using Pydantic Settings.
"""

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application
    app_name: str = "TeacherAssist V2"
    app_version: str = "2.0.0"
    debug: bool = False

    # LLM Configuration
    llm_provider: Literal["ollama", "openai"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"

    # Generation Limits
    max_slides_per_presentation: int = 50
    max_concurrent_generations: int = 3
    generation_timeout_seconds: int = 600

    # Storage Paths
    template_storage_path: Path = Path("data/templates")
    output_storage_path: Path = Path("data/outputs")
    cache_storage_path: Path = Path("data/cache")

    # Redis Cache
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    # Cost Control
    daily_cost_budget_usd: float = 10.0
    cost_per_1k_tokens: float = 0.002


# Global settings instance
settings = Settings()
