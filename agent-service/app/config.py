"""
CareTopicz Agent Service - Environment configuration.

Loads settings from environment variables and .env files.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env path relative to agent-service/ (parent of app/)
_AGENT_SERVICE_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _AGENT_SERVICE_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Service
    app_name: str = "CareTopicz Agent"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS - allow OpenEMR at localhost:8300
    cors_origins: list[str] = ["http://localhost:8300", "https://localhost:9300"]

    # LLM - Claude (Anthropic)
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"

    # OpenEMR FHIR API - for provider_search, appointment_check, insurance_coverage
    openemr_fhir_base_url: str = "https://localhost:9300/apis/default/fhir"
    openemr_fhir_token: str | None = None
    openemr_fhir_verify_ssl: bool = False


settings = Settings()
