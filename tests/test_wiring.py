"""W2 wiring: fakes without keys, the real `InProcessRunService` when the three settings are
present (stubbed factories, no network), and a UI starter that enforces the passcode and key.

All names and keys here are invented.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import gradio as gr
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from receipts.api.app import create_app
from receipts.api.wiring import (
    LazyRunService,
    build_live_service,
    make_starter,
    resolve_run_service,
)
from receipts.contracts import FetchedPage, RunRequest, RunService, SearchResult
from receipts.fakes import FakeRunService
from receipts.harness import InProcessRunService
from receipts.settings import MissingSettingError, get_settings
from receipts.ui.app import Starter

PASSCODE = "open-sesame"
ENV_NAMES = ("ANTHROPIC_API_KEY", "KEENABLE_API_KEY", "DATABASE_URL", "DEMO_PASSCODE")


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class _StubSearch:
    def search(self, query: str) -> list[SearchResult]:
        raise AssertionError("no network in unit tests")


class _StubFetch:
    def fetch(self, url: str) -> FetchedPage:
        raise AssertionError("no network in unit tests")


def _configure_live(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "not-a-real-anthropic-key")
    monkeypatch.setenv("KEENABLE_API_KEY", "not-a-real-keenable-key")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'runs.db'}")
    get_settings.cache_clear()


# --- (a) no keys: fakes stay in place ----------------------------------------------------


def test_create_app_without_keys_leaves_the_fakes_in_place() -> None:
    app = create_app()
    assert isinstance(app.state.run_service, LazyRunService)
    assert getattr(app.state, "live_run_service", None) is None
    response = TestClient(app).get("/api/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)  # the demo fallback answered, no live repo
    assert getattr(app.state, "live_run_service", None) is None


def test_resolve_without_keys_returns_the_fallback_and_caches_nothing(
    fake_run_service: FakeRunService,
) -> None:
    app = FastAPI()
    fallback = fake_run_service
    assert resolve_run_service(app, fallback=fallback) is fallback
    assert getattr(app.state, "live_run_service", None) is None


# --- (b) three settings present: the real service, no network --------------------------------


def test_resolve_with_the_three_settings_caches_an_in_process_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run_service: FakeRunService
) -> None:
    _configure_live(monkeypatch, tmp_path)
    monkeypatch.setattr("receipts.api.wiring.KeenableSearchClient", lambda key: _StubSearch())
    monkeypatch.setattr("receipts.api.wiring.KeenableFetchClient", lambda key: _StubFetch())
    app = FastAPI()
    first = resolve_run_service(app, fallback=fake_run_service)
    assert isinstance(first, InProcessRunService)
    assert app.state.live_run_service is first
    assert resolve_run_service(app, fallback=fake_run_service) is first


def test_build_live_service_takes_injected_clients_and_repo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_live(monkeypatch, tmp_path)
    service = build_live_service(get_settings(), search=_StubSearch(), fetch=_StubFetch())
    assert isinstance(service, InProcessRunService)


def test_build_live_service_refuses_without_the_keenable_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_live(monkeypatch, tmp_path)
    monkeypatch.delenv("KEENABLE_API_KEY")
    get_settings.cache_clear()
    with pytest.raises(MissingSettingError) as excinfo:
        build_live_service(get_settings())
    assert excinfo.value.name == "KEENABLE_API_KEY"


async def test_lazy_proxy_delegates_to_the_resolved_service(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run_service: FakeRunService
) -> None:
    """L5 captures the service at mount time, so the proxy must resolve per call."""
    _configure_live(monkeypatch, tmp_path)
    monkeypatch.setattr("receipts.api.wiring.KeenableSearchClient", lambda key: _StubSearch())
    monkeypatch.setattr("receipts.api.wiring.KeenableFetchClient", lambda key: _StubFetch())
    app = FastAPI()
    proxy = LazyRunService(app, fallback=fake_run_service)
    assert await proxy.list() == []  # the real repo, freshly created schema, no rows
    assert isinstance(app.state.live_run_service, InProcessRunService)


# --- (c) the UI starter: passcode first, then the key, then start -------------------------------


async def test_starter_rejects_a_wrong_passcode(
    monkeypatch: pytest.MonkeyPatch, fake_run_service: FakeRunService
) -> None:
    monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    monkeypatch.setenv("KEENABLE_API_KEY", "not-a-real-keenable-key")
    get_settings.cache_clear()
    fake = fake_run_service
    with pytest.raises(PermissionError):
        await make_starter(fake)(RunRequest(subject="A", rival="B"), "wrong")
    assert fake.requests == {}


async def test_starter_refuses_when_no_passcode_is_configured(
    monkeypatch: pytest.MonkeyPatch, fake_run_service: FakeRunService
) -> None:
    monkeypatch.setenv("KEENABLE_API_KEY", "not-a-real-keenable-key")
    get_settings.cache_clear()
    fake = fake_run_service
    with pytest.raises(PermissionError):
        await make_starter(fake)(RunRequest(subject="A", rival="B"), "")
    assert fake.requests == {}


async def test_starter_refuses_without_the_keenable_key(
    monkeypatch: pytest.MonkeyPatch, fake_run_service: FakeRunService
) -> None:
    monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    get_settings.cache_clear()
    fake = fake_run_service
    with pytest.raises(MissingSettingError) as excinfo:
        await make_starter(fake)(RunRequest(subject="A", rival="B"), PASSCODE)
    assert excinfo.value.name == "KEENABLE_API_KEY"
    assert fake.requests == {}


async def test_starter_starts_the_run_with_the_right_passcode_and_key(
    monkeypatch: pytest.MonkeyPatch, fake_run_service: FakeRunService
) -> None:
    monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    monkeypatch.setenv("KEENABLE_API_KEY", "not-a-real-keenable-key")
    get_settings.cache_clear()
    fake = fake_run_service
    run_id = await make_starter(fake)(RunRequest(subject="A", rival="B"), PASSCODE)
    assert fake.requests[run_id] == RunRequest(subject="A", rival="B")


def test_create_app_injects_the_starter_into_the_ui(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deleting the injection in `mount_ui` turns this red: the UI must not bypass the passcode."""
    seen: list[Starter | None] = []
    import receipts.ui.app as ui_app

    real_build_ui = ui_app.build_ui

    def spy(service: RunService, starter: Starter | None = None) -> gr.Blocks:
        seen.append(starter)
        return real_build_ui(service, starter=starter)

    monkeypatch.setattr(ui_app, "build_ui", spy)
    app = create_app()
    assert seen == [app.state.run_starter]
    assert seen[0] is not None
