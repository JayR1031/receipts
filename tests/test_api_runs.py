"""`/api/runs*` against the Wave 0 fakes. No network, no database, no real keys.

All text here is invented. Settings are read through `get_settings()` (an `lru_cache`), so each
test clears the cache after setting the environment it needs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from receipts.api.app import create_app
from receipts.api.routes import DEMO_RUN_ID
from receipts.contracts import (
    Battlecard,
    RunEvent,
    RunId,
    RunRequest,
    RunSummary,
)
from receipts.fakes import FakeRunService
from receipts.settings import get_settings

PASSCODE = "open-sesame"
BODY = {"subject": "Acme Widgets", "rival": "Zeta Gadgets", "category": "widgets"}


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in ("DEMO_PASSCODE", "KEENABLE_API_KEY", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


def _configure(monkeypatch: pytest.MonkeyPatch, *, passcode: bool, key: bool) -> None:
    if passcode:
        monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    if key:
        monkeypatch.setenv("KEENABLE_API_KEY", "test-key-not-real")
    get_settings.cache_clear()


# --- POST /api/runs ----------------------------------------------------------------


def test_post_run_is_accepted_with_passcode_and_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, passcode=True, key=True)
    response = client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": PASSCODE})
    assert response.status_code == 202
    assert response.json() == {"run_id": DEMO_RUN_ID}


def test_post_run_without_passcode_header_is_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, passcode=True, key=True)
    assert client.post("/api/runs", json=BODY).status_code == 401


def test_post_run_with_wrong_passcode_is_401(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, passcode=True, key=True)
    response = client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": "wrong"})
    assert response.status_code == 401


def test_post_run_is_401_when_no_passcode_is_configured(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unconfigured deploy cannot start runs, even with the right key."""
    _configure(monkeypatch, passcode=False, key=True)
    response = client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": ""})
    assert response.status_code == 401


@pytest.mark.parametrize("configured", ["", "   "])
def test_post_run_is_401_when_the_configured_passcode_is_blank(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, configured: str
) -> None:
    """`DEMO_PASSCODE=""` is not configured: an empty header must not start a run."""
    _configure(monkeypatch, passcode=False, key=True)
    monkeypatch.setenv("DEMO_PASSCODE", configured)
    get_settings.cache_clear()
    response = client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": configured})
    assert response.status_code == 401


def test_post_run_is_503_naming_the_key_when_keenable_key_missing(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, passcode=True, key=False)
    response = client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": PASSCODE})
    assert response.status_code == 503
    assert "KEENABLE_API_KEY" in response.json()["detail"]


def test_passcode_is_checked_before_the_key(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, passcode=True, key=False)
    response = client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": "wrong"})
    assert response.status_code == 401


def test_post_run_rejects_a_malformed_body(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, passcode=True, key=True)
    response = client.post(
        "/api/runs", json={"subject": "only one"}, headers={"X-Demo-Passcode": PASSCODE}
    )
    assert response.status_code == 422


# --- GET /api/runs/{run_id} and GET /api/runs ------------------------------------------


def test_get_run_returns_the_battlecard_after_a_start(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _configure(monkeypatch, passcode=True, key=True)
    run_id = client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": PASSCODE}).json()[
        "run_id"
    ]

    response = client.get(f"/api/runs/{run_id}")

    assert response.status_code == 200
    card = Battlecard.model_validate(response.json())
    assert (card.run_id, card.subject, card.rival) == (run_id, "Acme Widgets", "Zeta Gadgets")
    assert card.total_count >= card.verified_count >= 1


def test_get_unknown_run_is_404(client: TestClient) -> None:
    assert client.get("/api/runs/run-does-not-exist").status_code == 404


def test_get_runs_lists_the_fake_service_runs(
    app: FastAPI, client: TestClient, fake_run_service: FakeRunService
) -> None:
    """`app.state.run_service` wins over the demo fallback (the W1 wiring convention)."""
    app.state.run_service = fake_run_service
    assert client.get("/api/runs").json() == []

    import asyncio

    asyncio.run(fake_run_service.start(RunRequest(subject="Acme Widgets", rival="Zeta Gadgets")))
    [summary] = [RunSummary.model_validate(s) for s in client.get("/api/runs").json()]
    assert summary.run_id == fake_run_service.run_id
    assert summary.status == "done"


class _TwoRunService:
    """A `RunService` whose `list()` is oldest first, to prove the route re-sorts."""

    def __init__(self) -> None:
        t0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
        self.summaries = [
            RunSummary(
                run_id=RunId("run-older"),
                subject="A",
                rival="B",
                status="done",
                verified_count=1,
                total_count=1,
                started_at=t0,
            ),
            RunSummary(
                run_id=RunId("run-newer"),
                subject="C",
                rival="D",
                status="running",
                verified_count=0,
                total_count=0,
                started_at=t0 + timedelta(minutes=1),
            ),
        ]

    async def start(self, request: RunRequest) -> RunId:
        return RunId("run-newer")

    async def events(self, run_id: RunId) -> AsyncIterator[RunEvent]:
        return
        yield  # pragma: no cover

    async def get(self, run_id: RunId) -> Battlecard | None:
        return None

    async def list(self) -> list[RunSummary]:
        return list(self.summaries)


def test_get_runs_is_newest_first(app: FastAPI, client: TestClient) -> None:
    app.state.run_service = _TwoRunService()
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert [s["run_id"] for s in response.json()] == ["run-newer", "run-older"]
