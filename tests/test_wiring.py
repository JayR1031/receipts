"""W2 wiring: fakes without keys, the real `InProcessRunService` when the three settings are
present (stubbed factories, no network), and a UI starter that enforces the passcode and key.
Issue #41: the live `Gate` (`LiveGate`) that `create_app()` stores on `app.state.gate`.

All names, keys, identities and secrets here are invented (`fake-sub-...`, `...@example.com`).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import gradio as gr
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import Engine, inspect
from starlette.requests import Request

import receipts.api.wiring as wiring
from receipts.api.app import create_app, git_sha
from receipts.api.wiring import (
    LazyRunService,
    build_live_service,
    make_starter,
    resolve_run_service,
)
from receipts.auth.gate import Gate
from receipts.auth.models import AccountStatus, SessionUser
from receipts.auth.provider import GoogleIdentityProvider
from receipts.auth.routes import SignInConfig, get_identity_provider
from receipts.auth.session import SESSION_COOKIE, new_session, sign_session
from receipts.contracts import (
    Battlecard,
    DomainPack,
    DoneEvent,
    FetchedPage,
    RunEvent,
    RunId,
    RunRepo,
    RunRequest,
    RunService,
    RunSummary,
    SearchResult,
    StartedEvent,
)
from receipts.db import SqlRunRepo, SqlUserRepo, create_schema
from receipts.fakes import FakeRunService
from receipts.harness import Coordinator, InProcessRunService
from receipts.harness.live import KeenableFetchClient, KeenableSearchClient
from receipts.settings import MissingSettingError, Settings, get_settings
from receipts.ui.app import Starter, gated_run_stream

PASSCODE = "open-sesame"
ENV_NAMES = (
    "ANTHROPIC_API_KEY",
    "KEENABLE_API_KEY",
    "DATABASE_URL",
    "DEMO_PASSCODE",
    "GIT_SHA",
    "RENDER_GIT_COMMIT",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "SESSION_SECRET",
    "RUNS_PER_USER_PER_DAY",
    "SIGNED_OUT_RUNS_PER_DAY",
)
RENDER_SHA = "0123456789abcdef0123456789abcdef01234567"  # invented


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
    assert response.json() == []  # this app's demo fallback, nothing started yet, no live repo
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


def test_create_app_injects_the_starter_and_the_gate_into_the_ui(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deleting either injection turns this red: the UI must not bypass the passcode or the Gate.
    `build_ui` receiving the Gate also shows it was on `app.state.gate` before `mount_ui` ran."""
    seen: list[tuple[RunService, Starter | None, Gate | None]] = []
    import receipts.ui.app as ui_app

    real_build_ui = ui_app.build_ui

    def spy(
        service: RunService, starter: Starter | None = None, *, gate: Gate | None = None
    ) -> gr.Blocks:
        seen.append((service, starter, gate))
        return real_build_ui(service, starter=starter, gate=gate)

    monkeypatch.setattr(ui_app, "build_ui", spy)
    app = create_app()
    assert seen == [(app.state.run_service, app.state.run_starter, app.state.gate)]
    assert seen[0][1] is not None
    assert isinstance(seen[0][2], wiring.LiveGate)


# --- (d) git_sha: the image always bakes GIT_SHA (default "unknown"); Render sets RENDER_GIT_COMMIT


def test_git_sha_prefers_a_real_baked_sha(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_SHA", "abc1234")
    monkeypatch.setenv("RENDER_GIT_COMMIT", RENDER_SHA)
    assert git_sha() == "abc1234"


@pytest.mark.parametrize("baked", ["unknown", ""])
def test_git_sha_treats_the_image_default_as_unset_and_reads_render(
    monkeypatch: pytest.MonkeyPatch, baked: str
) -> None:
    """Render passes no build arg, so the Dockerfile's `ARG GIT_SHA=unknown` is what is baked."""
    monkeypatch.setenv("GIT_SHA", baked)
    monkeypatch.setenv("RENDER_GIT_COMMIT", RENDER_SHA)
    assert git_sha() == "0123456"


@pytest.mark.parametrize(("baked", "render"), [(None, None), ("unknown", None), ("", "")])
def test_git_sha_is_unknown_with_neither(
    monkeypatch: pytest.MonkeyPatch, baked: str | None, render: str | None
) -> None:
    for name, value in (("GIT_SHA", baked), ("RENDER_GIT_COMMIT", render)):
        if value is not None:
            monkeypatch.setenv(name, value)
    assert git_sha() == "unknown"


def test_healthz_on_render_reports_the_render_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """The deployed image's environment: baked default plus Render's runtime variable."""
    monkeypatch.setenv("GIT_SHA", "unknown")
    monkeypatch.setenv("RENDER_GIT_COMMIT", RENDER_SHA)
    assert TestClient(create_app()).get("/healthz").json()["sha"] == "0123456"


# --- (e) live Keenable clients: the mapping rules, with `_invoke` stubbed (no network) ----------

KEENABLE_KEY = "not-a-real-keenable-key"
T_LIVE = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
PAGE_URL = "https://acme.example/pricing"
LIVE_LOGGER = "receipts.harness.live"


def _clock() -> datetime:
    return T_LIVE


def _invoke_returning(raw: object) -> object:
    def invoke(arg: str) -> object:
        if isinstance(raw, BaseException):
            raise raw
        return raw

    return invoke


def _search_client(monkeypatch: pytest.MonkeyPatch, raw: object) -> KeenableSearchClient:
    client = KeenableSearchClient(KEENABLE_KEY, clock=_clock)
    monkeypatch.setattr(client, "_invoke", _invoke_returning(raw))
    return client


def _fetch_client(monkeypatch: pytest.MonkeyPatch, raw: object) -> KeenableFetchClient:
    client = KeenableFetchClient(KEENABLE_KEY, clock=_clock)
    monkeypatch.setattr(client, "_invoke", _invoke_returning(raw))
    return client


def test_search_maps_each_result_ranked_from_one_in_keenable_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = [
        {"url": "https://acme.example/a", "title": "A", "description": "first", "extra": 1},
        {"url": "https://zeta.example/b", "title": "B", "description": "second"},
    ]
    results = _search_client(monkeypatch, raw).search("acme pricing")
    assert results == [
        SearchResult(
            query="acme pricing",
            rank=1,
            url="https://acme.example/a",
            title="A",
            snippet="first",
            ts=T_LIVE,
        ),
        SearchResult(
            query="acme pricing",
            rank=2,
            url="https://zeta.example/b",
            title="B",
            snippet="second",
            ts=T_LIVE,
        ),
    ]


def test_search_skips_a_row_without_a_url_and_keeps_keenable_ranks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = [{"url": "https://acme.example/a"}, {"url": ""}, {"url": "https://zeta.example/c"}]
    results = _search_client(monkeypatch, raw).search("acme pricing")
    assert [(r.rank, r.url) for r in results] == [
        (1, "https://acme.example/a"),
        (3, "https://zeta.example/c"),
    ]


@pytest.mark.parametrize(
    "raw",
    ["Error: Keenable returned HTTP 429", {"results": []}, None, 42],
    ids=["tool-error-string", "dict-not-list", "none", "int"],
)
def test_search_that_is_not_a_result_list_gives_no_rows_and_logs(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, raw: object
) -> None:
    caplog.set_level(logging.WARNING, logger=LIVE_LOGGER)
    assert _search_client(monkeypatch, raw).search("acme pricing") == []
    assert [r.levelno for r in caplog.records] == [logging.WARNING]


def test_search_that_raises_gives_no_rows_and_logs_the_exception_type(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=LIVE_LOGGER)
    assert _search_client(monkeypatch, TimeoutError("read timed out")).search("q") == []
    assert len(caplog.records) == 1
    assert "TimeoutError" in caplog.records[0].getMessage()


def test_fetch_maps_a_body_with_content_to_an_ok_page(monkeypatch: pytest.MonkeyPatch) -> None:
    raw = {"url": PAGE_URL, "title": "Pricing", "content": "Plans start at 9 dollars per seat"}
    page = _fetch_client(monkeypatch, raw).fetch(PAGE_URL)
    assert page == FetchedPage(
        url=PAGE_URL, text="Plans start at 9 dollars per seat", fetched_at=T_LIVE, ok=True
    )


@pytest.mark.parametrize(
    "raw",
    [
        "Error: Keenable returned HTTP 404",
        {},
        {"url": PAGE_URL, "content": 123},
        {"url": PAGE_URL, "content": None},
        ["Plans start at 9 dollars per seat"],
        42,
        None,
        RuntimeError("connection reset"),
    ],
    ids=[
        "tool-error-string",
        "no-content",
        "content-not-text",
        "content-none",
        "list",
        "int",
        "none",
        "raises",
    ],
)
def test_a_failed_fetch_is_a_not_ok_page_never_a_false_claim(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, raw: object
) -> None:
    """Spec: a fetch that failed says nothing about the claim, so the page is `ok=False`."""
    caplog.set_level(logging.WARNING, logger=LIVE_LOGGER)
    page = _fetch_client(monkeypatch, raw).fetch(PAGE_URL)
    assert page == FetchedPage(url=PAGE_URL, text="", fetched_at=T_LIVE, ok=False)
    assert [r.levelno for r in caplog.records] == [logging.WARNING]


def test_a_logged_tool_error_never_carries_the_key(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger=LIVE_LOGGER)
    _fetch_client(monkeypatch, f"Error: key {KEENABLE_KEY} was refused").fetch(PAGE_URL)
    _search_client(monkeypatch, RuntimeError(f"bad key {KEENABLE_KEY}")).search("q")
    assert len(caplog.records) == 2
    assert all(KEENABLE_KEY not in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("client", [KeenableSearchClient, KeenableFetchClient])
@pytest.mark.parametrize("key", ["", "   "])
def test_live_clients_refuse_a_blank_key(
    client: type[KeenableSearchClient] | type[KeenableFetchClient], key: str
) -> None:
    """`langchain_keenable` strips a blank key to None and silently uses the keyless endpoint."""
    with pytest.raises(MissingSettingError) as excinfo:
        client(key)
    assert excinfo.value.name == "KEENABLE_API_KEY"


# --- (f) the demo fallback never passes off invented claims as the user's comparison -----------

USER_SUBJECT, USER_RIVAL = "Quillfeather Kites", "Brindlewick Kites"  # invented
USER_REQUEST = RunRequest(subject=USER_SUBJECT, rival=USER_RIVAL, category="kites")
USER_BODY = {"subject": USER_SUBJECT, "rival": USER_RIVAL, "category": "kites"}
DEMO_NAMES = ("Acme Widgets", "Zeta Gadgets")  # the demo script's own invented pair
WIRING_LOGGER = "receipts.api.wiring"
MODE_HEADER = "x-receipts-mode"


def _configure_partial(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config drift: passcode and Keenable key set, ANTHROPIC_API_KEY and DATABASE_URL missing."""
    monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    monkeypatch.setenv("KEENABLE_API_KEY", "not-a-real-keenable-key")
    get_settings.cache_clear()


def _stub_keenable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("receipts.api.wiring.KeenableSearchClient", lambda key: _StubSearch())
    monkeypatch.setattr("receipts.api.wiring.KeenableFetchClient", lambda key: _StubFetch())


def _no_demo_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("receipts.ui.demo.DEMO_DELAY_S", 0.0)


def _api(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://receipts")


async def _ui_run(app: FastAPI, passcode: str) -> tuple[str, str]:
    """Drive the Run panel's handler for a signed-out visitor: `create_app()` always wires a Gate,
    so the panel runs `gated_run_stream` over the mounted service and `app.state.gate` (the
    `starter` is unused). `None` stands for Gradio's request, which carries no session cookie."""
    snapshots = [
        snapshot
        async for snapshot in gated_run_stream(
            app.state.run_service,
            app.state.gate,
            None,
            USER_SUBJECT,
            USER_RIVAL,
            "kites",
            passcode,
        )
    ]
    return snapshots[-1]


def test_partial_config_api_run_carries_the_demo_names_not_the_users(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_partial(monkeypatch)
    client = TestClient(create_app())
    accepted = client.post("/api/runs", json=USER_BODY, headers={"X-Demo-Passcode": PASSCODE})
    assert accepted.status_code == 202
    run_id = accepted.json()["run_id"]
    card_response = client.get(f"/api/runs/{run_id}")
    card = Battlecard.model_validate(card_response.json())
    assert (card.subject, card.rival) == DEMO_NAMES
    history = client.get("/api/runs")
    assert [(row["subject"], row["rival"]) for row in history.json()] == [DEMO_NAMES]
    for text in (card_response.text, history.text):
        assert USER_SUBJECT not in text and USER_RIVAL not in text


async def test_partial_config_ui_run_carries_the_demo_names_not_the_users(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_partial(monkeypatch)
    _no_demo_delay(monkeypatch)
    progress, card = await _ui_run(create_app(), PASSCODE)
    assert DEMO_NAMES[0] in card
    assert USER_SUBJECT not in progress + card and USER_RIVAL not in progress + card


@pytest.mark.parametrize("path", ["api", "ui"])
async def test_partial_config_warns_once_naming_the_missing_settings(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, path: str
) -> None:
    _configure_partial(monkeypatch)
    caplog.set_level(logging.WARNING, logger=WIRING_LOGGER)
    app = create_app()
    async with _api(app) as client:
        for _ in range(2):
            if path == "api":
                headers = {"X-Demo-Passcode": PASSCODE}
                response = await client.post("/api/runs", json=USER_BODY, headers=headers)
                assert response.status_code == 202
            else:
                await app.state.run_starter(USER_REQUEST, PASSCODE)
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, [r.getMessage() for r in warnings]
    message = warnings[0].getMessage()
    assert "demo" in message.lower()
    assert "ANTHROPIC_API_KEY" in message and "DATABASE_URL" in message
    assert "KEENABLE_API_KEY" not in message  # set, so not named as missing
    assert PASSCODE not in message and "not-a-real-keenable-key" not in message


def test_a_blank_live_setting_counts_as_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_live(monkeypatch, tmp_path)
    _stub_keenable(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "   ")
    get_settings.cache_clear()
    app = FastAPI()
    assert not isinstance(resolve_run_service(app), InProcessRunService)
    assert getattr(app.state, "live_run_service", None) is None


def test_healthz_reports_demo_mode_without_the_three_settings() -> None:
    response = TestClient(create_app()).get("/healthz")
    assert response.status_code == 200
    assert response.headers[MODE_HEADER] == "demo"


def test_healthz_reports_demo_mode_when_a_live_setting_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_partial(monkeypatch)
    assert TestClient(create_app()).get("/healthz").headers[MODE_HEADER] == "demo"


def test_healthz_reports_live_mode_with_the_three_settings_and_builds_nothing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_live(monkeypatch, tmp_path)
    app = create_app()
    response = TestClient(app).get("/healthz")
    assert response.headers[MODE_HEADER] == "live"
    assert set(response.json()) == {"status", "sha", "version"}  # body shape unchanged
    assert getattr(app.state, "live_run_service", None) is None  # no client, no DB touched


# --- (g) no passcode configured (local dev, keyless): the demo replays under its own names -----


async def test_keyless_ui_replays_the_demo_under_its_own_names_and_history_lists_it(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _no_demo_delay(monkeypatch)
    caplog.set_level(logging.WARNING, logger=WIRING_LOGGER)
    app = create_app()
    progress, card = await _ui_run(app, "")
    assert "done" in progress.lower() and DEMO_NAMES[0] in card
    assert USER_SUBJECT not in progress + card
    async with _api(app) as client:
        history = (await client.get("/api/runs")).json()
        stored = await client.get("/api/runs/run-demo-0001")
    assert [(r["run_id"], r["subject"], r["rival"]) for r in history] == [
        ("run-demo-0001", *DEMO_NAMES)
    ]
    assert stored.status_code == 200 and USER_SUBJECT not in stored.text
    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []  # expected locally


async def test_keyless_api_start_still_needs_a_passcode() -> None:
    """L4's rule is unchanged: `POST /api/runs` without a configured passcode is 401."""
    async with _api(create_app()) as client:
        response = await client.post("/api/runs", json=USER_BODY, headers={"X-Demo-Passcode": ""})
    assert response.status_code == 401


async def test_no_passcode_with_the_live_service_refuses_the_ui_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The API would refuse this run, so the UI must too: only the demo starts without one."""
    _configure_live(monkeypatch, tmp_path)
    _stub_keenable(monkeypatch)
    app = create_app()
    with pytest.raises(PermissionError):
        await app.state.run_starter(USER_REQUEST, "")


async def test_a_configured_passcode_guards_the_demo_fallback_too(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Public URL safety: once DEMO_PASSCODE is set, a wrong one starts nothing, demo or not."""
    monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    get_settings.cache_clear()
    app = create_app()
    with pytest.raises(PermissionError):
        await app.state.run_starter(USER_REQUEST, "wrong")
    assert await app.state.run_service.list() == []


async def test_starter_treats_a_whitespace_passcode_as_unconfigured(
    monkeypatch: pytest.MonkeyPatch, fake_run_service: FakeRunService
) -> None:
    monkeypatch.setenv("DEMO_PASSCODE", "   ")
    monkeypatch.setenv("KEENABLE_API_KEY", "not-a-real-keenable-key")
    get_settings.cache_clear()
    with pytest.raises(PermissionError):
        await make_starter(fake_run_service)(USER_REQUEST, "   ")
    assert fake_run_service.requests == {}


async def test_starter_checks_the_passcode_before_the_key(
    monkeypatch: pytest.MonkeyPatch, fake_run_service: FakeRunService
) -> None:
    """A stranger with a wrong passcode learns nothing about whether the key is set."""
    monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    get_settings.cache_clear()
    with pytest.raises(PermissionError):
        await make_starter(fake_run_service)(USER_REQUEST, "wrong")


async def test_concurrent_first_calls_build_once_and_create_the_schema_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import receipts.api.wiring as wiring

    _configure_live(monkeypatch, tmp_path)
    _stub_keenable(monkeypatch)
    builds: list[int] = []
    schemas: list[int] = []
    real_build = wiring.build_live_service
    real_schema = wiring.create_schema

    def counting_build(settings: Settings, *, repo: RunRepo | None = None) -> InProcessRunService:
        builds.append(1)
        return real_build(settings, repo=repo)

    async def counting_schema(engine: Engine) -> None:
        schemas.append(1)
        await real_schema(engine)

    monkeypatch.setattr(wiring, "build_live_service", counting_build)
    monkeypatch.setattr(wiring, "create_schema", counting_schema)
    proxy = LazyRunService(FastAPI())
    results = await asyncio.gather(*(proxy.list() for _ in range(8)))
    assert results == [[]] * 8
    assert (len(builds), len(schemas)) == (1, 1)


# --- (h) the live Gate (issue #41): identify, start, history and account ------------------------

T_NOW = datetime(2026, 11, 16, 12, 0, tzinfo=UTC)
DAY_START = datetime(2026, 11, 16, tzinfo=UTC)
LATE_YESTERDAY = DAY_START - timedelta(hours=1)
SESSION_KEY = "not-a-real-session-secret-for-tests"  # invented
SUB, EMAIL = "fake-sub-0001", "visitor-0001@example.com"
GATE_REQUEST = RunRequest(subject="Acme Widgets", rival="Zeta Gadgets", category="widgets")
LIMIT_5 = r"^5 of 5 runs used today \(UTC\)"
CAP_20 = r"^20 of 20 signed-out runs used today \(UTC\)"
NO_PASSCODE = "a valid passcode is required"


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
class Live:
    app: FastAPI
    gate: Gate
    runs: SqlRunRepo
    users: SqlUserRepo
    service: InProcessRunService


def _install_live(app: FastAPI, runs: SqlRunRepo, pack: DomainPack) -> InProcessRunService:
    """What `resolve_run_service` caches once the three settings are present, with a quiet
    specialist and a fixed clock in place of Keenable, Anthropic and the wall clock."""
    coordinator = Coordinator([pack], _QuietSpecialist(), max_concurrent=1, clock=_now)
    service = InProcessRunService(coordinator, runs, clock=_now)
    app.state.live_run_service = service
    app.state.live_repo = runs
    app.state.schema_ready = False
    app.state.clock = _now
    return service


@pytest.fixture
async def live(
    tmp_path: Path, sample_pack: DomainPack, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[Live]:
    """`create_app()` with a live service on a SQLite file, a passcode and a Keenable key set."""
    monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    monkeypatch.setenv("KEENABLE_API_KEY", "not-a-real-keenable-key")
    get_settings.cache_clear()
    app = create_app()
    runs = SqlRunRepo(url=f"sqlite:///{tmp_path / 'live.db'}")
    service = _install_live(app, runs, sample_pack)
    await create_schema(runs.engine)  # so a test can seed rows before the Gate's first call
    users = SqlUserRepo(engine=runs.engine)
    app.state.user_repo = users
    yield Live(app=app, gate=app.state.gate, runs=runs, users=users, service=service)
    await runs.dispose()


def _configure_sign_in(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """The four sign-in settings (invented values); `DATABASE_URL` is a SQLite file nobody opens
    in these tests, because the live service is already cached on the app."""
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "fake-client-id.apps.example.com")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "not-a-real-client-secret")
    monkeypatch.setenv("SESSION_SECRET", SESSION_KEY)
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'sign-in.db'}")
    get_settings.cache_clear()


async def _signed_in(live: Live, sub: str = SUB, email: str = EMAIL) -> SessionUser:
    user = await live.users.get_or_create(sub, email, T_NOW - timedelta(days=1))
    return new_session(user.id, now=T_NOW)


async def _seed(
    runs: SqlRunRepo,
    count: int,
    *,
    user_id: str | None,
    prefix: str = "seed",
    at: datetime = T_NOW - timedelta(hours=1),
) -> list[RunId]:
    """`count` finished runs started at `at` (a second apart), claimed by `user_id` if given."""
    ids: list[RunId] = []
    for i in range(count):
        run_id = RunId(f"run-{prefix}-{i:03d}")
        summary = RunSummary(
            run_id=run_id,
            subject="Acme Widgets",
            rival="Zeta Gadgets",
            status="done",
            verified_count=0,
            total_count=0,
            started_at=at + timedelta(seconds=i),
        )
        await runs.save_run(summary)
        if user_id is not None:
            await runs.claim_run(run_id, user_id)
        ids.append(run_id)
    return ids


def test_start_of_utc_day_is_midnight_utc_of_the_utc_date() -> None:
    late_in_new_york = datetime(2026, 11, 16, 23, 30, tzinfo=timezone(timedelta(hours=-5)))
    assert wiring.start_of_utc_day(late_in_new_york) == datetime(2026, 11, 17, tzinfo=UTC)
    assert wiring.start_of_utc_day(T_NOW) == DAY_START


def test_create_app_stores_a_live_gate_and_builds_nothing() -> None:
    app = create_app()
    gate: Gate = app.state.gate
    assert isinstance(gate, wiring.LiveGate)
    for name in ("live_run_service", "user_repo", "identity_provider"):
        assert getattr(app.state, name, None) is None, name  # all built on first use


async def test_signed_in_start_needs_no_passcode_and_claims_the_run(live: Live) -> None:
    user = await _signed_in(live)
    run_id = await live.gate.start(GATE_REQUEST, "", user)
    await live.service.wait(run_id)
    assert [s.run_id for s in await live.runs.list_runs_for(user.user_id)] == [run_id]
    assert await live.runs.count_runs_since(None, DAY_START) == 0  # not a signed-out run


async def test_signed_in_at_the_limit_is_refused_and_starts_nothing(live: Live) -> None:
    """A correct passcode does not turn a signed-in user at the limit into a signed-out run."""
    user = await _signed_in(live)
    await _seed(live.runs, 5, user_id=user.user_id)
    with pytest.raises(PermissionError, match=LIMIT_5):
        await live.gate.start(GATE_REQUEST, PASSCODE, user)
    assert len(await live.runs.list_runs()) == 5


async def test_runs_before_midnight_utc_do_not_count_today(live: Live) -> None:
    user = await _signed_in(live)
    await _seed(live.runs, 5, user_id=user.user_id, at=LATE_YESTERDAY)
    run_id = await live.gate.start(GATE_REQUEST, "", user)
    await live.service.wait(run_id)
    assert len(await live.runs.list_runs_for(user.user_id)) == 6


async def test_signed_out_with_a_wrong_passcode_is_refused_and_starts_nothing(live: Live) -> None:
    with pytest.raises(PermissionError, match=NO_PASSCODE):
        await live.gate.start(GATE_REQUEST, "wrong", None)
    assert await live.runs.list_runs() == []


async def test_signed_out_with_the_right_passcode_at_the_cap_is_refused(live: Live) -> None:
    await _seed(live.runs, 20, user_id=None)
    with pytest.raises(PermissionError, match=CAP_20):
        await live.gate.start(GATE_REQUEST, PASSCODE, None)
    assert len(await live.runs.list_runs()) == 20


async def test_signed_out_with_the_right_passcode_starts_a_run_with_no_user(live: Live) -> None:
    run_id = await live.gate.start(GATE_REQUEST, PASSCODE, None)
    await live.service.wait(run_id)
    assert [s.run_id for s in await live.runs.list_runs_for(None)] == [run_id]


class _CountsRepo(SqlRunRepo):
    """Different counts for a user and for no user, so a count in the wrong `may_start` slot, or
    the wrong owner counted, changes the decision. Records every count it is asked for."""

    def __init__(self, url: str, counts: dict[str | None, int]) -> None:
        super().__init__(url)
        self.counts = counts
        self.asked: list[tuple[str | None, datetime]] = []

    async def count_runs_since(self, user_id: str | None, since: datetime) -> int:
        self.asked.append((user_id, since))
        return self.counts[user_id]


SLOT_USER = "user-slot-0001"


@pytest.mark.parametrize(
    ("signed_in", "counts", "refusal"),
    [
        (True, {SLOT_USER: 3, None: 0}, r"^3 of 3 runs used today \(UTC\)"),
        (False, {SLOT_USER: 0, None: 7}, r"^7 of 7 signed-out runs used today \(UTC\)"),
        (True, {SLOT_USER: 2, None: 7}, None),
        (False, {SLOT_USER: 3, None: 6}, None),
    ],
    ids=["signed-in-at-limit", "signed-out-at-cap", "signed-in-under", "signed-out-under"],
)
async def test_each_count_reaches_its_own_may_start_slot(
    tmp_path: Path,
    sample_pack: DomainPack,
    monkeypatch: pytest.MonkeyPatch,
    signed_in: bool,
    counts: dict[str | None, int],
    refusal: str | None,
) -> None:
    """`may_start` takes the two counts as adjacent ints, so a swapped call would type-check.
    Distinct limits (3 per user, 7 signed out) also catch swapped limits in the reason."""
    for name, value in (
        ("DEMO_PASSCODE", PASSCODE),
        ("KEENABLE_API_KEY", "not-a-real-keenable-key"),
        ("RUNS_PER_USER_PER_DAY", "3"),
        ("SIGNED_OUT_RUNS_PER_DAY", "7"),
    ):
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    app = create_app()
    repo = _CountsRepo(f"sqlite:///{tmp_path / 'slots.db'}", counts)
    service = _install_live(app, repo, sample_pack)
    owner = SLOT_USER if signed_in else None
    user = (
        SessionUser(user_id=SLOT_USER, expires_at=T_NOW + timedelta(days=1)) if signed_in else None
    )
    if refusal is None:
        await service.wait(await app.state.gate.start(GATE_REQUEST, PASSCODE, user))
    else:
        with pytest.raises(PermissionError, match=refusal):
            await app.state.gate.start(GATE_REQUEST, PASSCODE, user)
    assert repo.asked == [(owner, DAY_START)]  # only the visitor's own count, from 00:00 UTC
    await repo.dispose()


async def test_a_missing_keenable_key_is_a_permission_error_naming_it(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The UI then needs only `PermissionError`; the message is the name, never a value."""
    monkeypatch.delenv("KEENABLE_API_KEY")
    get_settings.cache_clear()
    user = await _signed_in(live)
    for passcode, who in ((PASSCODE, None), ("", user)):
        with pytest.raises(PermissionError) as excinfo:
            await live.gate.start(GATE_REQUEST, passcode, who)
        assert str(excinfo.value) == "KEENABLE_API_KEY is not set"
        assert not isinstance(excinfo.value, MissingSettingError)
    assert await live.runs.list_runs() == []


async def test_a_wrong_passcode_is_refused_before_the_key_is_checked(
    live: Live, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stranger learns nothing about whether the key is set."""
    monkeypatch.delenv("KEENABLE_API_KEY")
    get_settings.cache_clear()
    with pytest.raises(PermissionError, match=NO_PASSCODE):
        await live.gate.start(GATE_REQUEST, "wrong", None)


async def test_the_run_id_from_gate_start_is_followed_through_app_state_run_service(
    live: Live,
) -> None:
    """The UI follows a gated run with `app.state.run_service.events(run_id)`."""
    run_id = await live.gate.start(GATE_REQUEST, PASSCODE, None)
    events = [event async for event in live.app.state.run_service.events(run_id)]
    assert isinstance(events[0], StartedEvent) and events[0].subject == GATE_REQUEST.subject
    assert isinstance(events[-1], DoneEvent)
    assert {event.run_id for event in events} == {run_id}


async def test_history_is_the_users_runs_signed_in_and_unowned_runs_signed_out(
    live: Live,
) -> None:
    user = await _signed_in(live)
    other = await _signed_in(live, "fake-sub-0002", "other@example.com")
    mine = await _seed(live.runs, 2, user_id=user.user_id, prefix="mine")
    await _seed(live.runs, 1, user_id=other.user_id, prefix="other")
    unowned = await _seed(live.runs, 1, user_id=None, prefix="unowned")
    assert [s.run_id for s in await live.gate.history(user)] == mine[::-1]  # newest first
    assert [s.run_id for s in await live.gate.history(None)] == unowned


async def test_account_signed_in_shows_the_email_and_todays_count_for_that_user(
    live: Live, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_sign_in(monkeypatch, tmp_path)
    user = await _signed_in(live)
    await _seed(live.runs, 2, user_id=user.user_id, prefix="mine")
    await _seed(live.runs, 3, user_id=user.user_id, prefix="old", at=LATE_YESTERDAY)
    await _seed(live.runs, 4, user_id=None, prefix="unowned")
    assert await live.gate.account(user) == AccountStatus(
        email=EMAIL, runs_used=2, runs_limit=5, sign_in_available=True
    )
    assert await live.gate.account(None) == AccountStatus(
        email=None, runs_used=4, runs_limit=20, sign_in_available=True
    )


async def test_account_of_a_deleted_user_reads_as_signed_out(
    live: Live, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_sign_in(monkeypatch, tmp_path)
    ghost = new_session("user-deleted-0001", now=T_NOW)
    await _seed(live.runs, 2, user_id=ghost.user_id, prefix="ghost")
    await _seed(live.runs, 4, user_id=None, prefix="unowned")
    assert await live.gate.account(ghost) == AccountStatus(
        email=None, runs_used=4, runs_limit=20, sign_in_available=True
    )


async def test_account_hides_sign_in_when_it_is_not_configured(live: Live) -> None:
    assert await live.gate.account(None) == AccountStatus(
        email=None, runs_used=0, runs_limit=20, sign_in_available=False
    )


async def test_local_demo_starts_without_a_passcode_or_a_key_signed_in_or_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local demo (no passcode configured, no live settings): the demo branch decides before the
    start rule and the key check. Run through either, a blank passcode is refused signed out and
    the missing Keenable key is refused for everyone. No run table exists here, so there is
    nothing to count or claim (the half-configured tests below pin the uncounted part)."""
    _no_demo_delay(monkeypatch)
    app = create_app()
    signed_in = SessionUser(user_id="user-demo-0001", expires_at=T_NOW + timedelta(days=1))
    for who in (None, signed_in):
        run_id = await app.state.gate.start(USER_REQUEST, "", who)
        events = [event async for event in app.state.run_service.events(run_id)]
        assert isinstance(events[-1], DoneEvent)
        assert USER_SUBJECT not in str(events)  # the demo's own names, as before issue #41


async def test_demo_mode_history_is_the_service_list_and_the_account_is_zeros(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Even with sign-in configured: the demo stores nothing, so there is nothing to count."""
    _no_demo_delay(monkeypatch)
    _configure_sign_in(monkeypatch, tmp_path)
    app = create_app()
    run_id = await app.state.gate.start(USER_REQUEST, "", None)
    _ = [event async for event in app.state.run_service.events(run_id)]
    assert [s.run_id for s in await app.state.gate.history(None)] == [run_id]
    assert await app.state.gate.account(None) == AccountStatus(
        email=None, runs_used=0, runs_limit=0, sign_in_available=False
    )


def _session_token(user_id: str) -> str:
    return sign_session(new_session(user_id, now=T_NOW), secret=SecretStr(SESSION_KEY))


def _request_with(token: str | None, app: FastAPI) -> Request:
    """A request as Gradio hands it over: its `app` is Gradio's sub-app, not ours."""
    headers = [] if token is None else [(b"cookie", f"{SESSION_COOKIE}={token}".encode())]
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/ui/gradio_api/queue/join",
        "headers": headers,
        "query_string": b"",
        "app": app,
    }
    return Request(scope)


def test_identify_reads_a_valid_session_cookie_and_nothing_else(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _configure_sign_in(monkeypatch, tmp_path)
    app = create_app()
    app.state.clock = _now
    token = _session_token("user-0001")
    assert app.state.gate.identify(_request_with(token, FastAPI())) == new_session(
        "user-0001", now=T_NOW
    )
    assert app.state.gate.identify(_request_with(None, FastAPI())) is None
    assert app.state.gate.identify(_request_with(token[:-2] + "xx", FastAPI())) is None


def test_identify_uses_the_apps_clock_not_the_gradio_sub_apps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`get_clock(request)` would read the sub-app's state; the Gate reads `app.state.clock`."""
    _configure_sign_in(monkeypatch, tmp_path)
    app = create_app()
    app.state.clock = lambda: T_NOW + timedelta(days=8)  # past the 7-day session
    sub_app = FastAPI()
    sub_app.state.clock = _now
    assert app.state.gate.identify(_request_with(_session_token("user-0001"), sub_app)) is None


def test_identify_is_none_when_sign_in_is_not_configured() -> None:
    app = create_app()
    app.state.clock = _now
    assert app.state.gate.identify(_request_with(_session_token("user-0001"), FastAPI())) is None


async def test_the_first_live_use_creates_users_and_runs_user_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`_ensure_schema` runs `create_schema` once, on the first live call, never at startup."""
    _configure_live(monkeypatch, tmp_path)
    _stub_keenable(monkeypatch)
    app = create_app()
    assert await app.state.gate.history(None) == []
    catalogue = inspect(app.state.live_repo.engine)
    assert {"runs", "users"} <= set(catalogue.get_table_names())
    assert "user_id" in {column["name"] for column in catalogue.get_columns("runs")}


def test_the_live_repo_and_the_user_repo_share_one_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """One pool: otherwise the first sign-in builds a second engine on `DATABASE_URL`."""
    _configure_live(monkeypatch, tmp_path)
    _stub_keenable(monkeypatch)
    app = create_app()
    resolve_run_service(app)
    assert isinstance(app.state.user_repo, SqlUserRepo)
    assert app.state.user_repo.engine is app.state.live_repo.engine


def test_the_identity_provider_is_built_on_first_use_and_kept_for_the_process() -> None:
    """Per process, not per request (ADR-0008): the key cache lives as long as the provider."""
    app = create_app()
    config = SignInConfig(
        "fake-client-id.apps.example.com",
        SecretStr("not-a-real-client-secret"),
        SecretStr(SESSION_KEY),
    )
    request = _request_with(None, app)
    first = get_identity_provider(request, config)
    assert isinstance(first, GoogleIdentityProvider)
    assert get_identity_provider(request, config) is first
    assert app.state.identity_provider is first


# --- (i) half-configured: DEMO_PASSCODE set, a live setting missing, so the Gate serves the demo -
# The UI always starts runs through `gate.start` (`create_app()` always wires the Gate), so these
# drive that path, not `app.state.run_starter`.


@pytest.mark.parametrize("passcode", ["wrong", "", "   "], ids=["wrong", "blank", "whitespace"])
async def test_half_configured_gate_refuses_a_wrong_or_blank_passcode_and_starts_nothing(
    monkeypatch: pytest.MonkeyPatch, passcode: str
) -> None:
    _configure_partial(monkeypatch)
    app = create_app()
    with pytest.raises(PermissionError, match=f"^{NO_PASSCODE}$"):
        await app.state.gate.start(USER_REQUEST, passcode, None)
    assert await app.state.run_service.list() == []


async def test_half_configured_gate_checks_the_passcode_before_the_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No Keenable key: a wrong passcode is refused as a wrong passcode, so a stranger learns
    nothing about the key; the right passcode reaches the key check, which names the variable."""
    monkeypatch.setenv("DEMO_PASSCODE", PASSCODE)
    get_settings.cache_clear()
    app = create_app()
    with pytest.raises(PermissionError, match=f"^{NO_PASSCODE}$"):
        await app.state.gate.start(USER_REQUEST, "wrong", None)
    with pytest.raises(PermissionError) as excinfo:
        await app.state.gate.start(USER_REQUEST, PASSCODE, None)
    assert str(excinfo.value) == "KEENABLE_API_KEY is not set"
    assert await app.state.run_service.list() == []


async def test_half_configured_gate_replays_the_demo_with_the_passcode_uncounted_and_unclaimed(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """A signed-out cap of 1: had the first demo run counted, the second would be refused. The demo
    stores nothing, so neither a run repo nor a user repo is ever built for a claim to write to.
    The drift is logged once, naming the missing settings."""
    _configure_partial(monkeypatch)
    monkeypatch.setenv("SIGNED_OUT_RUNS_PER_DAY", "1")
    get_settings.cache_clear()
    _no_demo_delay(monkeypatch)
    caplog.set_level(logging.WARNING, logger=WIRING_LOGGER)
    app = create_app()
    for _ in range(2):
        run_id = await app.state.gate.start(USER_REQUEST, PASSCODE, None)
        events = [event async for event in app.state.run_service.events(run_id)]
        assert isinstance(events[0], StartedEvent)
        assert (events[0].subject, events[0].rival) == DEMO_NAMES
        assert isinstance(events[-1], DoneEvent)
    history = await app.state.gate.history(None)
    assert [(s.subject, s.rival) for s in history] == [DEMO_NAMES]
    for name in ("live_run_service", "live_repo", "user_repo"):
        assert getattr(app.state, name, None) is None, name
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1, [r.getMessage() for r in warnings]
