"""Lazy settings. Nothing here runs at import; `get_settings()` reads the environment on
first call so the image boots with no secrets (ADR-0005). Frozen after Wave 0; ADR-0008
lifted the freeze for issue #41 only, to add the five sign-in and limit names.

The ten names this module knows: ANTHROPIC_API_KEY, KEENABLE_API_KEY, DATABASE_URL,
DEMO_PASSCODE, MAX_CONCURRENT_SPECIALISTS, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
SESSION_SECRET, RUNS_PER_USER_PER_DAY, SIGNED_OUT_RUNS_PER_DAY. Nothing else is read here.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True, extra="ignore")

    anthropic_api_key: SecretStr | None = None
    keenable_api_key: SecretStr | None = None
    database_url: str | None = None
    demo_passcode: SecretStr | None = None
    max_concurrent_specialists: int = 4
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    session_secret: SecretStr | None = None
    runs_per_user_per_day: int = 5
    signed_out_runs_per_day: int = 20


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build once, on first use. Tests call `get_settings.cache_clear()` between cases."""
    return Settings()


class MissingSettingError(RuntimeError):
    """A required environment variable is not set; `name` is the variable's name."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"{name} is not set")


def sqlalchemy_url(url: str) -> str:
    """Pure: point a bare `postgresql://` URL at the psycopg 3 driver; leave others alone."""
    prefix = "postgresql://"
    if url.startswith(prefix):
        return "postgresql+psycopg://" + url[len(prefix) :]
    return url


def require_keenable_key(settings: Settings) -> SecretStr:
    if settings.keenable_api_key is None:
        raise MissingSettingError("KEENABLE_API_KEY")
    return settings.keenable_api_key
