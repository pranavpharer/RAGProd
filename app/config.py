from functools import lru_cache

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, populated from environment variables."""

    primary_model: str = "gemini-3.1-flash-lite"
    fallback_model: str = "gemini-3.1-flash"
    gemini_api_key: SecretStr | None = None
    api_auth_token: SecretStr | None = None

    langsmith_tracing_v2: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGSMITH_TRACING_V2", "LANGSMITH_TRACING"),
    )
    langsmith_project: str = "RAGProd"

    app_env: str = "development"
    log_level: str = "INFO"
    rate_limit: str = "20/minute"
    cache_ttl_sec: int = Field(
        default=300, ge=0,
        validation_alias=AliasChoices("CACHE_TTL_SEC", "CACHE_TTL_SECONDS"),
    )
    cache_max_entries: int = Field(default=1000, ge=1)
    max_retry: int = Field(
        default=3, ge=0, le=10,
        validation_alias=AliasChoices("MAX_RETRY", "MAX_RETRIES"),
    )
    model_timeout_sec: float = Field(default=30.0, gt=0, le=300)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}

    @model_validator(mode="after")
    def validate_production_secrets(self):
        if self.is_production:
            if (
                not self.gemini_api_key
                or not self.gemini_api_key.get_secret_value().strip()
                or self.gemini_api_key.get_secret_value().startswith("replace-with-")
            ):
                raise ValueError("GEMINI_API_KEY is required in production")
            if (
                not self.api_auth_token
                or len(self.api_auth_token.get_secret_value()) < 32
                or self.api_auth_token.get_secret_value().startswith("replace-with-")
            ):
                raise ValueError("API_AUTH_TOKEN must be at least 32 characters in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
