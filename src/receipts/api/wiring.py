"""W2 wiring: the real `InProcessRunService`, resolved lazily, and the UI's passcode starter.

Nothing here reads a setting at import or in `create_app()`. `resolve_run_service(app)` is called
per request (through `LazyRunService`) and builds the live service the first time all three of
`DATABASE_URL`, `KEENABLE_API_KEY` and `ANTHROPIC_API_KEY` are set (a blank value counts as
unset), caching it on `app.state.live_run_service`; otherwise it returns the demo fallback and
caches no live service.

Why a proxy: L5's `mount_ui(app)` captures the service at mount time, inside `create_app()`,
where no secret may be read. So `create_app()` stores a `LazyRunService` on
`app.state.run_service` before mounting; L4's `get_run_service` and L5's `resolve_service` both
see the proxy, and every call on it resolves to the live service or the fallback at call time.

The demo fallback is `DemoRunService` over L5's invented demo script (`receipts.ui.demo`), one per
app, so the API and the UI show the same demo run. It must never pass off invented claims as the
user's comparison:
- every run it starts carries the script's own invented pair, whatever the user typed, so neither
  the battlecard nor History puts the user's names next to invented "verified" claims;
- the first time it serves a run while `DEMO_PASSCODE` is set (a public deploy whose live settings
  drifted), it logs a WARNING naming the missing variables, never their values;
- `/healthz` reports the mode in the `X-Receipts-Mode` header (`active_mode`).

The UI starter: with no passcode configured (local dev, keyless) and the proxy on the demo, the
Run panel replays the demo without a passcode. In every other case it applies the same two checks
as `POST /api/runs` (passcode, then Keenable key), so once a passcode is set the UI cannot start a
run the API would refuse. `POST /api/runs` is L4's and always needs a configured passcode.

The verifier is L2's `receipts.verify.verify_claim` (pure; merged in PR #25).
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from typing import Literal

from fastapi import FastAPI
from pydantic import SecretStr

from receipts.contracts import (
    Battlecard,
    FetchClient,
    RunEvent,
    RunId,
    RunRepo,
    RunRequest,
    RunService,
    RunSummary,
    SearchClient,
    StartedEvent,
)
from receipts.db import SqlRunRepo, create_schema
from receipts.fakes import FakeRunService
from receipts.harness import (
    Coordinator,
    InProcessRunService,
    ModelFactory,
    SpecialistRunner,
    Verify,
    load_pack,
)
from receipts.harness.live import KeenableFetchClient, KeenableSearchClient, live_model_factory
from receipts.settings import Settings, get_settings, require_keenable_key
from receipts.ui.demo import demo_service as ui_demo_service
from receipts.verify import verify_claim

__all__ = [
    "MODE_HEADER",
    "DemoRunService",
    "LazyRunService",
    "Mode",
    "Starter",
    "active_mode",
    "build_live_service",
    "demo_fallback",
    "live_settings_present",
    "make_starter",
    "missing_live_settings",
    "passcode_configured",
    "resolve_run_service",
]

logger = logging.getLogger(__name__)

PACK_NAMES = ("pricing", "positioning_seo")
MODE_HEADER = "X-Receipts-Mode"

Mode = Literal["live", "demo"]
Starter = Callable[[RunRequest, str], Awaitable[RunId]]


def _is_set(value: SecretStr | str | None) -> bool:
    text = value.get_secret_value() if isinstance(value, SecretStr) else value
    return bool(text and text.strip())


def missing_live_settings(settings: Settings) -> tuple[str, ...]:
    """The names (never the values) of the live settings that are unset or blank."""
    values = {
        "ANTHROPIC_API_KEY": settings.anthropic_api_key,
        "DATABASE_URL": settings.database_url,
        "KEENABLE_API_KEY": settings.keenable_api_key,
    }
    return tuple(name for name, value in values.items() if not _is_set(value))


def live_settings_present(settings: Settings) -> bool:
    return not missing_live_settings(settings)


def passcode_configured(settings: Settings) -> bool:
    return _is_set(settings.demo_passcode)


def build_live_service(
    settings: Settings,
    *,
    search: SearchClient | None = None,
    fetch: FetchClient | None = None,
    model_factory: ModelFactory = live_model_factory,
    repo: RunRepo | None = None,
    verify: Verify | None = None,
) -> InProcessRunService:
    """The real service: two packs, Keenable clients, L2's verifier, `SqlRunRepo`.

    Keyword arguments exist for tests and the integration run (a stub client, a SQLite repo);
    production passes `settings` and the repo. Raises `MissingSettingError("KEENABLE_API_KEY")`
    when the key is absent or blank; the repo reads `DATABASE_URL` on its first use.
    """
    if search is None or fetch is None:
        key = require_keenable_key(settings).get_secret_value()
        search = search if search is not None else KeenableSearchClient(key)
        fetch = fetch if fetch is not None else KeenableFetchClient(key)
    runner = SpecialistRunner(
        search,
        fetch,
        model_factory=model_factory,
        verify=verify if verify is not None else verify_claim,
    )
    coordinator = Coordinator(
        [load_pack(name) for name in PACK_NAMES],
        runner,
        max_concurrent=settings.max_concurrent_specialists,
    )
    return InProcessRunService(coordinator, repo if repo is not None else SqlRunRepo())


def _own_request(script: Sequence[RunEvent]) -> RunRequest:
    started = next((event for event in script if isinstance(event, StartedEvent)), None)
    if started is None:
        raise ValueError("a demo script needs a StartedEvent naming its own subject and rival")
    return RunRequest(subject=started.subject, rival=started.rival, category=started.category)


class DemoRunService:
    """The demo fallback: replays an invented script under the script's own names."""

    def __init__(self, inner: FakeRunService) -> None:
        self._inner = inner
        self.request = _own_request(inner.script)
        self._warned = False

    async def start(self, request: RunRequest) -> RunId:
        # The user's request is dropped on purpose: the invented claims are about the script's
        # own pair, so the user's names must not head the card or the History row.
        self._warn_once()
        return await self._inner.start(self.request)

    def _warn_once(self) -> None:
        settings = get_settings()
        if self._warned or not passcode_configured(settings):
            return
        self._warned = True
        logger.warning(
            "demo mode: DEMO_PASSCODE is set but %s is missing, so runs replay the invented demo "
            "(%s vs %s), not a live comparison",
            ", ".join(missing_live_settings(settings)),
            self.request.subject,
            self.request.rival,
        )

    async def events(self, run_id: RunId) -> AsyncIterator[RunEvent]:
        async for event in self._inner.events(run_id):
            yield event

    async def get(self, run_id: RunId) -> Battlecard | None:
        return await self._inner.get(run_id)

    async def list(self) -> list[RunSummary]:
        return await self._inner.list()


def demo_fallback(app: FastAPI) -> DemoRunService:
    """This app's demo fallback, built on first use (never at import or in `create_app()`)."""
    cached: object = getattr(app.state, "demo_run_service", None)
    if isinstance(cached, DemoRunService):
        return cached
    service = DemoRunService(ui_demo_service())
    app.state.demo_run_service = service
    return service


def resolve_run_service(app: FastAPI, *, fallback: RunService | None = None) -> RunService:
    """The cached live service, or build and cache it when the three settings are present,
    or the fallback (this app's `DemoRunService` by default). Never raises on missing keys."""
    cached: object = getattr(app.state, "live_run_service", None)
    if isinstance(cached, InProcessRunService):
        return cached
    settings = get_settings()
    if not live_settings_present(settings):
        return fallback if fallback is not None else demo_fallback(app)
    repo = SqlRunRepo()
    service = build_live_service(settings, repo=repo)
    app.state.live_run_service = service
    app.state.live_repo = repo  # kept here so schema setup never reads a private attribute
    app.state.schema_ready = False
    return service


def active_mode(app: FastAPI) -> Mode:
    """ "live" when the live service is cached or the three settings are present, else "demo".
    Reads presence only: builds no client and touches no database."""
    cached: object = getattr(app.state, "live_run_service", None)
    if isinstance(cached, InProcessRunService) or live_settings_present(get_settings()):
        return "live"
    return "demo"


async def _ensure_schema(app: FastAPI) -> None:
    """`create_schema` once, on the first real use (never at startup)."""
    repo: object = getattr(app.state, "live_repo", None)
    if isinstance(repo, SqlRunRepo) and not getattr(app.state, "schema_ready", False):
        await create_schema(repo.engine)
        app.state.schema_ready = True


class LazyRunService:
    """A `RunService` whose every call resolves the real service (or the fallback) at call time."""

    def __init__(self, app: FastAPI, *, fallback: RunService | None = None) -> None:
        self._app = app
        self._fallback = fallback
        self._lock = asyncio.Lock()

    def resolve(self) -> RunService:
        """The service a call made now would use; no schema work, no network."""
        return resolve_run_service(self._app, fallback=self._fallback)

    async def _service(self) -> RunService:
        async with self._lock:
            service = self.resolve()
            if isinstance(service, InProcessRunService):
                await _ensure_schema(self._app)
            return service

    async def start(self, request: RunRequest) -> RunId:
        return await (await self._service()).start(request)

    async def events(self, run_id: RunId) -> AsyncIterator[RunEvent]:
        service = await self._service()
        async for event in service.events(run_id):
            yield event

    async def get(self, run_id: RunId) -> Battlecard | None:
        return await (await self._service()).get(run_id)

    async def list(self) -> list[RunSummary]:
        return await (await self._service()).list()


def _serves_demo(service: RunService) -> bool:
    resolved = service.resolve() if isinstance(service, LazyRunService) else service
    return isinstance(resolved, DemoRunService)


def _check_passcode(presented: str, settings: Settings) -> None:
    """`PermissionError` unless a non-blank passcode is configured and matches (constant time)."""
    expected = settings.demo_passcode
    if expected is None or not expected.get_secret_value().strip():
        raise PermissionError("a valid passcode is required")
    if not secrets.compare_digest(presented.encode(), expected.get_secret_value().encode()):
        raise PermissionError("a valid passcode is required")


def make_starter(service: RunService) -> Starter:
    """The UI's `starter`.

    No passcode configured and `service` on the demo: replay the demo (its own names). Otherwise
    the same two checks as `POST /api/runs`, passcode first so a stranger learns nothing about the
    key: a wrong, blank or unconfigured passcode raises `PermissionError`, a missing key raises
    `MissingSettingError("KEENABLE_API_KEY")`. Gradio shows the message; no run starts.
    """

    async def start(request: RunRequest, passcode: str) -> RunId:
        settings = get_settings()
        if not passcode_configured(settings) and _serves_demo(service):
            return await service.start(request)
        _check_passcode(passcode, settings)
        require_keenable_key(settings)
        return await service.start(request)

    return start
