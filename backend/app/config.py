"""Application configuration via environment variables.

Uses pydantic-settings to read from .env file and environment variables.
Crashes at startup if a required variable is missing — fail fast, not at
runtime when a user request hits the missing config.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed application settings.

    Every field here maps to an environment variable of the same name.
    Pydantic validates the type at load time — if DATABASE_URL is missing
    or DEBUG isn't a valid bool, the app won't start.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Required (no default = must be set) ---
    DATABASE_URL: str

    # --- Optional (have sensible defaults) ---
    DEBUG: bool = False
    APP_NAME: str = "AbhiMart"
    APP_VERSION: str = "0.1.0"

    # --- AI ---
    GEMINI_API_KEY: str
    LANGSMITH_TRACING: bool = False
    LANGSMITH_API_KEY: str = ""
    LANGSMITH_PROJECT: str = "abhimart"
    LANGSMITH_ENDPOINT: str = "https://api.smith.langchain.com"


@lru_cache
def get_settings() -> Settings:
    """Cached settings instance.

    Why lru_cache? We don't want to re-read .env on every request.
    The settings are loaded once and reused for the lifetime of the process.
    """
    return Settings()
