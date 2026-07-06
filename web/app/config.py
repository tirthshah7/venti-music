"""
Environment-driven configuration for the Venti web layer (build spec T3.1).

All values come from the process environment — no secret values in code,
ever (build rule 4). Locally, load `.env` into the environment when
starting the server (`uvicorn web.app.main:app --env-file .env`); Railway
injects real env vars. Settings validates presence at startup so the app
fails fast with a readable message; the engine and Spotify client modules
read the same variables from os.environ at call time.
"""
from functools import lru_cache
from typing import Literal, Optional

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Field names map 1:1 (case-insensitively) to the env var names
    listed in .env.example at the repo root."""

    # Required. min_length=1 so an exported-but-empty var fails startup
    # the same way a missing one does.
    anthropic_api_key: str = Field(min_length=1)
    spotify_client_id: str = Field(min_length=1)
    spotify_client_secret: str = Field(min_length=1)
    spotify_redirect_uri: str = Field(min_length=1)
    app_secret: str = Field(min_length=1)

    # Optional.
    llm_backend: Literal["api", "cli"] = "api"
    # None → venti_core.llm.anthropic_api.DEFAULT_MODEL decides.
    anthropic_model: Optional[str] = None

    model_config = SettingsConfigDict(extra="ignore")


class MissingConfigError(RuntimeError):
    """Startup configuration failure with a human-readable message."""


def load_settings() -> Settings:
    """Build Settings, converting pydantic's ValidationError into one
    clear startup message listing every missing/empty env var by name."""
    try:
        return Settings()
    except ValidationError as exc:
        bad = sorted(
            str(err["loc"][0]).upper()
            for err in exc.errors()
            if err["type"] in ("missing", "string_too_short")
        )
        if not bad:
            raise
        raise MissingConfigError(
            "Venti web cannot start — missing or empty required "
            f"environment variable(s): {', '.join(bad)}. "
            "See .env.example at the repo root; locally run "
            "`uvicorn web.app.main:app --env-file .env`."
        ) from None


@lru_cache
def get_settings() -> Settings:
    return load_settings()
