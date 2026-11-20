"""`/api/runs*` against the Wave 0 fakes, and (issue #41) against a live service on a SQLite
file with a quiet specialist. No network, no real keys, no `DATABASE_URL` opened.

All text here is invented; identities are synthetic (`fake-sub-...`, `...@example.com`).
Settings are read through `get_settings()` (an `lru_cache`), so each test clears the cache after
setting the environment it needs.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from receipts.api.app import create_app
from receipts.api.routes import DEMO_RUN_ID
from receipts.auth.session import SESSION_COOKIE, new_session, sign_session
from receipts.contracts import (
    Battlecard,
    DomainPack,
    RunEvent,
    RunId,
    RunRequest,
    RunSummary,
)
from receipts.db import SqlRunRepo, SqlUserRepo, create_schema
from receipts.fakes import FakeRunService
from receipts.harness import Coordinator, InProcessRunService
from receipts.settings import get_settings

PASSCODE = "open-sesame"
BODY = {"subject": "Acme Widgets", "rival": "Zeta Gadgets", "category": "widgets"}
ENV_NAMES = (
    "DEMO_PASSCODE",
    "KEENABLE_API_KEY",
    "DATABASE_URL",
    "ANTHROPIC_API_KEY",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "SESSION_SECRET",
    "RUNS_PER_USER_PER_DAY",
    "SIGNED_OUT_RUNS_PER_DAY",
)


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    for name in ENV_NAMES:
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


# --- issue #41: the list is scoped by session; a passcode run is a signed-out run ----------------

T_NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
SESSION_KEY = "not-a-real-session-secret-for-tests"  # invented


def _now() -> datetime:
    return T_NOW


class _QuietSpecialist:
    """No claims, no model, no network: a run goes from `StartedEvent` to `DoneEvent` at once."""

    async def run(
        self, run_id: RunId, request: RunRequest, pack: DomainPack
    ) -> AsyncIterator[RunEvent]:
        del run_id, request, pack
        return
        yield  # pragma: no cover


@dataclass(frozen=True)
class LiveApi:
    app: FastAPI
    runs: SqlRunRepo
    users: SqlUserRepo
    service: InProcessRunService


@pytest.fixture
async def live_api(
    tmp_path: Path, sample_pack: DomainPack, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[LiveApi]:
    """`create_app()` with the live service cached on a SQLite file (what `resolve_run_service`
    builds once the three settings are present), a passcode, a key and sign-in configured."""
    _configure(monkeypatch, passcode=True, key=True)
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-client-id.apps.example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "not-a-real-client-secret")
    monkeypatch.setenv("SESSION_SECRET", SESSION_KEY)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'unopened.db'}")
    get_settings.cache_clear()
    app = create_app()
    runs = SqlRunRepo(url=f"sqlite:///{tmp_path / 'api.db'}")
    coordinator = Coordinator([sample_pack], _QuietSpecialist(), max_concurrent=1, clock=_now)
    service = InProcessRunService(coordinator, runs, clock=_now)
    app.state.live_run_service = service
    app.state.live_repo = runs
    app.state.schema_ready = False
    app.state.clock = _now
    await create_schema(runs.engine)
    users = SqlUserRepo(engine=runs.engine)
    app.state.user_repo = users
    yield LiveApi(app=app, runs=runs, users=users, service=service)
    await runs.dispose()


async def _seed(runs: SqlRunRepo, prefix: str, count: int, user_id: str | None) -> list[str]:
    ids: list[str] = []
    for i in range(count):
        run_id = RunId(f"run-{prefix}-{i:03d}")
        await runs.save_run(
            RunSummary(
                run_id=run_id,
                subject="Acme Widgets",
                rival="Zeta Gadgets",
                status="done",
                verified_count=0,
                total_count=0,
                started_at=T_NOW - timedelta(hours=1) + timedelta(seconds=i),
            )
        )
        if user_id is not None:
            await runs.claim_run(run_id, user_id)
        ids.append(run_id)
    return ids


def _client(app: FastAPI, session_token: str | None = None) -> httpx.AsyncClient:
    cookie = {} if session_token is None else {"cookie": f"{SESSION_COOKIE}={session_token}"}
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://receipts", headers=cookie
    )


def _token(user_id: str) -> str:
    return sign_session(new_session(user_id, now=T_NOW), secret=SecretStr(SESSION_KEY))


async def _two_users_and_unowned(live: LiveApi) -> tuple[str, list[str], list[str]]:
    me = await live.users.get_or_create("fake-sub-0001", "visitor-0001@example.com", T_NOW)
    other = await live.users.get_or_create("fake-sub-0002", "other@example.com", T_NOW)
    mine = await _seed(live.runs, "mine", 2, me.id)
    await _seed(live.runs, "theirs", 1, other.id)
    unowned = await _seed(live.runs, "unowned", 1, None)
    return me.id, mine, unowned


async def test_get_runs_with_a_session_cookie_lists_that_users_runs_and_shared_unsigned_runs(
    live_api: LiveApi,
) -> None:
    """Ask Receipts / POST /api/runs stores a signed-out row; signed-in History must still
    list it, and must never list another signed-in person's runs."""
    me, mine, unowned = await _two_users_and_unowned(live_api)
    async with _client(live_api.app, _token(me)) as client:
        response = await client.get("/api/runs")
    assert response.status_code == 200
    rows = response.json()
    ids = [row["run_id"] for row in rows]
    assert set(ids) == {*mine, *unowned}
    assert not any(run_id.startswith("run-theirs-") for run_id in ids)
    assert [row["started_at"] for row in rows] == sorted(
        (row["started_at"] for row in rows), reverse=True
    )


@pytest.mark.parametrize("cookie", [None, "tampered"], ids=["no-cookie", "tampered-cookie"])
async def test_get_runs_without_a_valid_session_lists_only_runs_with_no_user(
    live_api: LiveApi, cookie: str | None
) -> None:
    me, _mine, unowned = await _two_users_and_unowned(live_api)
    token = None if cookie is None else _token(me)[:-2] + "xx"
    async with _client(live_api.app, token) as client:
        response = await client.get("/api/runs")
    assert response.status_code == 200
    assert [row["run_id"] for row in response.json()] == unowned


async def test_post_run_at_the_signed_out_cap_is_429_naming_the_count(
    live_api: LiveApi,
) -> None:
    await _seed(live_api.runs, "unowned", 20, None)
    async with _client(live_api.app) as client:
        response = await client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": PASSCODE})
    assert response.status_code == 429
    assert "20 of 20" in response.json()["detail"]
    assert "(UTC)" in response.json()["detail"]
    assert len(await live_api.runs.list_runs()) == 20  # nothing started


async def test_post_run_counts_as_a_signed_out_run_even_with_a_session_cookie(
    live_api: LiveApi,
) -> None:
    """`X-Demo-Passcode` runs are signed-out runs: never claimed, counted against the cap."""
    me, _mine, unowned = await _two_users_and_unowned(live_api)
    async with _client(live_api.app, _token(me)) as client:
        response = await client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": PASSCODE})
    assert response.status_code == 202
    run_id = RunId(response.json()["run_id"])
    await live_api.service.wait(run_id)
    assert [s.run_id for s in await live_api.runs.list_runs_for(None)] == [run_id, *unowned]
    assert len(await live_api.runs.list_runs_for(me)) == 2  # the user's own two, unchanged
    async with _client(live_api.app, _token(me)) as listed:
        history = await listed.get("/api/runs")
    assert run_id in {row["run_id"] for row in history.json()}


async def test_post_run_checks_the_passcode_then_the_cap_then_the_key(
    live_api: LiveApi, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stranger learns nothing about the cap or the key; the key comes after the start rule."""
    await _seed(live_api.runs, "unowned", 20, None)
    monkeypatch.delenv("KEENABLE_API_KEY")
    get_settings.cache_clear()
    async with _client(live_api.app) as client:
        wrong = await client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": "wrong"})
        right = await client.post("/api/runs", json=BODY, headers={"X-Demo-Passcode": PASSCODE})
    assert (wrong.status_code, right.status_code) == (401, 429)
    assert wrong.json()["detail"] == "a valid X-Demo-Passcode is required"
