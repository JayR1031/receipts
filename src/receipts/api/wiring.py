"""W2 wiring: the real `InProcessRunService`, resolved lazily, and the UI's passcode starter.

Nothing here reads a setting at import or in `create_app()`. `resolve_run_service(app)` is called
per request (through `LazyRunService`) and builds the live service the first time all three of
`DATABASE_URL`, `KEENABLE_API_KEY` and `ANTHROPIC_API_KEY` are present, caching it on
`app.state.live_run_service`; otherwise it returns the lane's fake fallback and caches nothing.

Why a proxy: L5's `mount_ui(app)` captures the service at mount time, inside `create_app()`,
where no secret may be read. So `create_app()` stores a `LazyRunService` on
`app.state.run_service` before mounting; L4's `get_run_service` and L5's `resolve_service` both
see the proxy, and every call on it resolves to the live service or the fallback at call time.
The fallback is L4's demo service (`receipts.api.demo`), so `/api/runs*` behave exactly as in
W1 without keys; the UI then replays that same invented demo instead of `receipts.ui.demo`.

The verifier is L2's `receipts.verify.verify_claim` (pure; merged in PR #25).
"""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import FastAPI

from receipts.api.demo import demo_service
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
)
from receipts.db import SqlRunRepo, create_schema
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
from receipts.verify import verify_claim

__all__ = [
    "LazyRunService",
    "Starter",
    "build_live_service",
    "live_settings_present",
    "make_starter",
    "resolve_run_service",
]

PACK_NAMES = ("pricing", "positioning_seo")

Starter = Callable[[RunRequest, str], Awaitable[RunId]]


def live_settings_present(settings: Settings) -> bool:
    return bool(settings.database_url and settings.keenable_api_key and settings.anthropic_api_key)


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
    production passes only `settings`. Raises `MissingSettingError("KEENABLE_API_KEY")` when
    the key is absent; the repo reads `DATABASE_URL` on its first use.
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


def resolve_run_service(app: FastAPI, *, fallback: RunService | None = None) -> RunService:
    """The cached live service, or build and cache it when the three settings are present,
    or the fallback (L4's demo service by default). Never raises on missing keys."""
    cached: object = getattr(app.state, "live_run_service", None)
    if isinstance(cached, InProcessRunService):
        return cached
    settings = get_settings()
    if not live_settings_present(settings):
        return fallback if fallback is not None else demo_service()
    service = build_live_service(settings)
    app.state.live_run_service = service
    app.state.schema_ready = False
    return service


async def _ensure_schema(app: FastAPI, service: RunService) -> None:
    """`create_schema` once, on the first real use (never at startup)."""
    if isinstance(service, InProcessRunService) and not getattr(app.state, "schema_ready", False):
        repo: object = getattr(service, "_repo", None)
        if isinstance(repo, SqlRunRepo):
            await create_schema(repo.engine)
        app.state.schema_ready = True


class LazyRunService:
    """A `RunService` whose every call resolves the real service (or the fallback) at call time."""

    def __init__(self, app: FastAPI, *, fallback: RunService | None = None) -> None:
        self._app = app
        self._fallback = fallback
        self._lock = asyncio.Lock()

    async def _service(self) -> RunService:
        async with self._lock:
            service = resolve_run_service(self._app, fallback=self._fallback)
            await _ensure_schema(self._app, service)
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


def make_starter(service: RunService) -> Starter:
    """The UI's `starter`: the same two checks as `POST /api/runs`, then `service.start`.

    A wrong, blank or unconfigured passcode raises `PermissionError`; a missing key raises
    `MissingSettingError("KEENABLE_API_KEY")`. Gradio shows the message; no run starts.
    """

    async def start(request: RunRequest, passcode: str) -> RunId:
        settings = get_settings()
        expected = settings.demo_passcode
        if expected is None or not expected.get_secret_value().strip():
            raise PermissionError("a valid passcode is required")
        if not secrets.compare_digest(passcode.encode(), expected.get_secret_value().encode()):
            raise PermissionError("a valid passcode is required")
        require_keenable_key(settings)
        return await service.start(request)

    return start
