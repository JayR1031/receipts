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

The verifier is L2's `receipts.verify.verify_claim` (pure; merged in PR #25). Claims it would not
verify first get up to two Mellea repairs (`live_repair_factory`, GitHub issue #39, ADR-0007);
the verifier still judges every claim.

Sign-in (issue #41, ADR-0008). `create_app()` stores a `LiveGate` on `app.state.gate`; the UI
starts runs, lists History and shows the account line through it. Like the proxy, it reads
settings per call, never in `create_app()`.
- `identify` is `current_user` with the Gate's own clock (`app.state.clock`, else UTC now). It
  never calls `get_clock(request)`: the UI hands over Gradio's request, whose `app` is Gradio's
  sub-app, not this one.
- `start`: local demo mode (no passcode configured and the proxy on the demo) replays the demo as
  `make_starter` does, uncounted and unclaimed. Otherwise the start rule (`may_start`) decides
  from today's (UTC) count of the visitor's own runs: the user's when signed in, the runs with no
  user when signed out (passcode compared in constant time); then the Keenable key, refused as
  `PermissionError("KEENABLE_API_KEY is not set")` (the name only), so the UI needs to recognise
  only `PermissionError`; then the run starts on the same proxy the UI follows for events, and a
  signed-in user's run is claimed right after (the brief's accepted sub-second unclaimed window).
  A session is signed in only while its `users` row exists: `identify` reads no database, so
  `start` reads the row first, as `account` does. A row the owner deleted (the cookie lives 7
  days), or no live repo to read it from, means signed out: the passcode and the signed-out cap
  apply and the run is never claimed (on Postgres the claim would fail on the foreign key after
  the run had started).
- `history`: that user's runs, or the runs with no user; `account`: the email, today's count and
  the limit that applies. On the demo (local, or half-configured) nothing is stored, so History
  is the demo's list and the account line is signed out, `0 of SIGNED_OUT_RUNS_PER_DAY`, with
  sign-in hidden.
- `POST /api/runs` and `GET /api/runs` use the same rules (`runs_today`, `history_for`).

Pools: when the live repo is built first, `app.state.user_repo` becomes a `SqlUserRepo` on the
same engine, so sign-in shares the run repo's pool. When a sign-in reaches the users store before
the live service exists (`/auth/callback` or `/auth/me` is the first request to need it),
`receipts.auth.routes.get_user_repo` builds a `SqlUserRepo` on its own engine, and building the
live repo later keeps that one: the process then holds two pools, one for users and one for
runs, until it restarts.

Identity provider: built per process, not per request. `receipts.auth.routes` builds the real
Google provider from `sign_in_config(settings)` on the first callback that needs it and caches it
on `app.state.identity_provider`; nothing here or in `create_app()` builds it. Its key cache never
expires: per request would cost one extra GET to Google's key set per sign-in; per process keeps
a key Google has withdrawn until a token names an unknown `kid` and forces a refetch. The latter
is accepted for this app (ADR-0008).
"""

from __future__ import annotations

import asyncio
import logging
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from datetime import UTC, datetime
from typing import Literal, cast

from fastapi import FastAPI
from pydantic import SecretStr
from starlette.requests import Request

from receipts.auth.limits import may_start
from receipts.auth.models import AccountStatus, SessionUser, StartDecision, User
from receipts.auth.routes import Clock, current_user, missing_sign_in_settings
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
from receipts.db import SqlRunRepo, SqlUserRepo, create_schema
from receipts.fakes import FakeRunService
from receipts.harness import (
    Coordinator,
    InProcessRunService,
    ModelFactory,
    RepairFactory,
    SpecialistRunner,
    Verify,
    load_pack,
)
from receipts.harness.live import (
    KeenableFetchClient,
    KeenableSearchClient,
    live_model_factory,
    live_repair_factory,
)
from receipts.settings import (
    MissingSettingError,
    Settings,
    get_settings,
    require_keenable_key,
)
from receipts.ui.demo import demo_service as ui_demo_service
from receipts.verify import verify_claim

__all__ = [
    "MODE_HEADER",
    "DemoRunService",
    "LazyRunService",
    "LiveGate",
    "Mode",
    "Starter",
    "active_mode",
    "build_live_service",
    "demo_fallback",
    "history_for",
    "live_repo_of",
    "live_settings_present",
    "make_starter",
    "missing_live_settings",
    "passcode_configured",
    "resolve_run_service",
    "runs_today",
    "start_of_utc_day",
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
    repair_factory: RepairFactory | None = live_repair_factory,
) -> InProcessRunService:
    """The real service: two packs, Keenable clients, L2's verifier, Mellea repairs, `SqlRunRepo`.

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
        repair_factory=repair_factory,
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
    _user_repo_for(app, repo)  # sign-in shares this pool
    return service


def _user_repo_for(app: FastAPI, repo: SqlRunRepo) -> SqlUserRepo:
    """`app.state.user_repo`, or a `SqlUserRepo` on `repo`'s engine, cached there."""
    configured: object = getattr(app.state, "user_repo", None)
    if isinstance(configured, SqlUserRepo):
        return configured
    users = SqlUserRepo(engine=repo.engine)
    app.state.user_repo = users
    return users


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

    async def live_repo(self) -> SqlRunRepo | None:
        """The live service's `SqlRunRepo`, its schema created; `None` on the fallback."""
        service = await self._service()
        repo: object = getattr(self._app.state, "live_repo", None)
        if isinstance(service, InProcessRunService) and isinstance(repo, SqlRunRepo):
            return repo
        return None


async def live_repo_of(service: RunService) -> SqlRunRepo | None:
    """The live repo behind a `LazyRunService`; `None` for any other service (a fake, the demo)."""
    return await service.live_repo() if isinstance(service, LazyRunService) else None


def start_of_utc_day(now: datetime) -> datetime:
    """00:00 UTC on `now`'s UTC date, where every daily limit's window starts."""
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return now.astimezone(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


async def _count_today(repo: SqlRunRepo | None, user_id: str | None, now: datetime) -> int:
    if repo is None:
        return 0  # the demo stores nothing, so nothing counts
    return await repo.count_runs_since(user_id, start_of_utc_day(now))


async def runs_today(service: RunService, user_id: str | None, now: datetime) -> int:
    """Today's (UTC) runs of that user, or with `None` the runs with no user; 0 on the demo."""
    return await _count_today(await live_repo_of(service), user_id, now)


async def history_for(service: RunService, user: SessionUser | None) -> list[RunSummary]:
    """History: the user's runs, or the runs with no user (newest first); on the demo or any
    service without a live repo, `service.list()` as before issue #41."""
    repo = await live_repo_of(service)
    if repo is None:
        return await service.list()
    return await repo.list_runs_for(user.user_id if user is not None else None)


def _serves_demo(service: RunService) -> bool:
    resolved = service.resolve() if isinstance(service, LazyRunService) else service
    return isinstance(resolved, DemoRunService)


def _passcode_ok(presented: str, settings: Settings) -> bool:
    """A non-blank passcode is configured and `presented` matches it (constant time)."""
    expected = settings.demo_passcode
    if expected is None or not expected.get_secret_value().strip():
        return False
    return secrets.compare_digest(presented.encode(), expected.get_secret_value().encode())


def _check_passcode(presented: str, settings: Settings) -> None:
    """`PermissionError` unless a non-blank passcode is configured and matches (constant time)."""
    if not _passcode_ok(presented, settings):
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


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _require_key(settings: Settings) -> None:
    """`require_keenable_key`, refused as `PermissionError` naming the variable, never a value."""
    try:
        require_keenable_key(settings)
    except MissingSettingError as exc:
        raise PermissionError(f"{exc.name} is not set") from exc


async def _decide(
    repo: SqlRunRepo | None,
    settings: Settings,
    passcode: str,
    user: SessionUser | None,
    now: datetime,
) -> StartDecision:
    """The start rule with today's counts; only the visitor's own count is read, the other is 0
    (`may_start` reads one per branch). Keywords, because the two counts are adjacent ints."""
    signed_in = user is not None
    user_runs = await _count_today(repo, user.user_id, now) if signed_in else 0
    signed_out_runs = 0 if signed_in else await _count_today(repo, None, now)
    return may_start(
        user=user,
        passcode_ok=_passcode_ok(passcode, settings),
        user_runs_today=user_runs,
        signed_out_runs_today=signed_out_runs,
        per_user_limit=settings.runs_per_user_per_day,
        signed_out_cap=settings.signed_out_runs_per_day,
    )


def _demo_account(settings: Settings) -> AccountStatus:
    """The account line with no live repo (local demo or half-configured): nothing is stored, so
    nothing is counted, and with no users table every visitor reads as signed out. The limit is
    the signed-out cap, never 0 (Rule Zero: `0 of 0` reads as none left while runs still start).
    Sign-in stays hidden: a session would read as signed out here anyway."""
    return AccountStatus(
        email=None,
        runs_used=0,
        runs_limit=settings.signed_out_runs_per_day,
        sign_in_available=False,
    )


class LiveGate:
    """The live `receipts.auth.gate.Gate` (module docstring, "Sign-in"). `service` is the proxy
    `create_app()` stores on `app.state.run_service`, so a run it starts is the one the UI follows;
    `app` gives the live repo, the user repo and the clock, all read at call time."""

    def __init__(self, service: LazyRunService, app: FastAPI) -> None:
        self._service = service
        self._app = app

    def _clock(self) -> Clock:
        configured: object = getattr(self._app.state, "clock", None)
        return cast(Clock, configured) if callable(configured) else _utc_now

    def identify(self, request: Request) -> SessionUser | None:
        return current_user(request, get_settings(), self._clock())

    async def _row(self, repo: SqlRunRepo | None, user: SessionUser | None) -> User | None:
        """The session's `users` row, or `None`: signed out, no live repo (so no users table to
        read), or a row the owner deleted while the cookie is still valid. `identify` reads no
        database, so `start` and `account` both read the row here."""
        if user is None or repo is None:
            return None
        return await _user_repo_for(self._app, repo).get(user.user_id)

    async def start(self, request: RunRequest, passcode: str, user: SessionUser | None) -> RunId:
        settings = get_settings()
        if not passcode_configured(settings) and _serves_demo(self._service):
            return await self._service.start(request)  # local demo: no passcode, not counted
        repo = await self._service.live_repo()
        visitor = user if await self._row(repo, user) is not None else None
        decision = await _decide(repo, settings, passcode, visitor, self._clock()())
        if not decision.allowed:
            raise PermissionError(decision.reason)
        _require_key(settings)  # after the start rule: a stranger learns nothing about the key
        run_id = await self._service.start(request)
        if visitor is not None and repo is not None:
            await repo.claim_run(run_id, visitor.user_id)
        return run_id

    async def history(self, user: SessionUser | None) -> list[RunSummary]:
        return await history_for(self._service, user)

    async def account(self, user: SessionUser | None) -> AccountStatus:
        repo = await self._service.live_repo()
        settings = get_settings()
        if repo is None:
            return _demo_account(settings)
        found = await self._row(repo, user)
        now = self._clock()()
        available = not missing_sign_in_settings(settings)
        if found is None:  # signed out, or a session whose user row is gone
            used = await _count_today(repo, None, now)
            limit = settings.signed_out_runs_per_day
            return AccountStatus(
                email=None, runs_used=used, runs_limit=limit, sign_in_available=available
            )
        used = await _count_today(repo, found.id, now)
        limit = settings.runs_per_user_per_day
        return AccountStatus(
            email=found.email, runs_used=used, runs_limit=limit, sign_in_available=available
        )
