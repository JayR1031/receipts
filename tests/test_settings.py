"""W0 settings: lazy, no secret read at import or in create_app()."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from pydantic import SecretStr

from receipts.settings import (
    MissingSettingError,
    Settings,
    get_settings,
    require_keenable_key,
    sqlalchemy_url,
)

NAMES = (
    "ANTHROPIC_API_KEY",
    "KEENABLE_API_KEY",
    "DATABASE_URL",
    "DEMO_PASSCODE",
    "MAX_CONCURRENT_SPECIALISTS",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "SESSION_SECRET",
    "RUNS_PER_USER_PER_DAY",
    "SIGNED_OUT_RUNS_PER_DAY",
)


@pytest.fixture
def empty_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in NAMES:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()


def test_settings_construct_with_nothing_set(empty_env: None) -> None:
    settings = Settings()
    assert settings.anthropic_api_key is None
    assert settings.keenable_api_key is None
    assert settings.database_url is None
    assert settings.demo_passcode is None
    assert settings.max_concurrent_specialists == 4
    assert settings.google_client_id is None
    assert settings.google_client_secret is None
    assert settings.session_secret is None
    assert settings.runs_per_user_per_day == 5
    assert settings.signed_out_runs_per_day == 20


def test_get_settings_is_lazy_and_cached(empty_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_CONCURRENT_SPECIALISTS", "2")
    first = get_settings()
    assert first.max_concurrent_specialists == 2
    assert get_settings() is first


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite+aiosqlite:///:memory:", "sqlite+aiosqlite:///:memory:"),
    ],
)
def test_sqlalchemy_url_rewrites_only_the_bare_postgres_scheme(given: str, expected: str) -> None:
    assert sqlalchemy_url(given) == expected


def test_require_keenable_key_names_the_missing_variable(empty_env: None) -> None:
    with pytest.raises(MissingSettingError) as excinfo:
        require_keenable_key(Settings())
    assert excinfo.value.name == "KEENABLE_API_KEY"
    assert "KEENABLE_API_KEY" in str(excinfo.value)


def test_require_keenable_key_returns_the_secret(empty_env: None) -> None:
    secret = require_keenable_key(Settings(keenable_api_key=SecretStr("not-a-real-key")))
    assert secret.get_secret_value() == "not-a-real-key"


def test_create_app_boots_with_an_empty_environment() -> None:
    """Mirrors the api-image CI check: the container starts with no secrets at all."""
    root = Path(__file__).resolve().parents[1]
    code = "from receipts.api.app import create_app; create_app()"
    env = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"]}
    proc = subprocess.run(
        ["uv", "run", "--no-sync", "python", "-c", code],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
