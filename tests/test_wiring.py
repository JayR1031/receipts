"""W2 wiring: fakes without keys, the real `InProcessRunService` when the three settings are
present (stubbed factories, no network), and a UI starter that enforces the passcode and key.

All names and keys here are invented.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import gradio as gr
import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from receipts.api.app import create_app, git_sha
from receipts.api.wiring import (
    LazyRunService,
    build_live_service,
    make_starter,
    resolve_run_service,
)
from receipts.contracts import (
    Battlecard,
    FetchedPage,
    RunRepo,
    RunRequest,
    RunService,
    SearchResult,
)
from receipts.fakes import FakeRunService
from receipts.harness import InProcessRunService
from receipts.harness.live import KeenableFetchClient, KeenableSearchClient
from receipts.settings import MissingSettingError, Settings, get_settings
from receipts.ui.app import Starter, run_stream

PASSCODE = "open-sesame"
ENV_NAMES = (
    "ANTHROPIC_API_KEY",
    "KEENABLE_API_KEY",
    "DATABASE_URL",
    "DEMO_PASSCODE",
    "GIT_SHA",
    "RENDER_GIT_COMMIT",
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
    """Drive the Run panel exactly as Gradio does: the mounted service and the injected starter."""
    snapshots = [
        snapshot
        async for snapshot in run_stream(
            app.state.run_service,
            USER_SUBJECT,
            USER_RIVAL,
            "kites",
            passcode,
            starter=app.state.run_starter,
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
