"""`/api/runs*`. Handlers stay thin; the passcode, cap and key rules are plain functions.

The run service is looked up per request from `app.state.run_service` (W2 sets it to the real
`InProcessRunService`); when absent, the demo `FakeRunService` answers (W1 wiring convention).
Settings are read per request through `get_settings()`, never at import or in `create_app()`.

Issue #41 (ADR-0008), with the same rules as the UI's `Gate` (`receipts.api.wiring`):
- `POST /api/runs` keeps `X-Demo-Passcode` (401) and the key (503), and between them refuses with
  429 once today's (UTC) runs with no user have reached `SIGNED_OUT_RUNS_PER_DAY`; the detail is
  the start rule's reason, with its count and cap. An API run is a signed-out run: never claimed,
  even when the request carries a session cookie.
- `GET /api/runs` lists the signed-in user's runs when the request carries a valid session
  cookie, else the runs that belong to no user; on the demo, or a service with no live repo,
  `service.list()` as before.
- `GET /api/runs/{run_id}` is unchanged: anyone with the id can read the card.
"""

from __future__ import annotations

import secrets
from datetime import datetime
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from receipts.api.demo import DEMO_RUN_ID, demo_service
from receipts.api.models import ErrorDetail, RunAccepted
from receipts.api.wiring import history_for, runs_today
from receipts.auth.limits import may_start
from receipts.auth.routes import current_user, get_clock
from receipts.contracts import Battlecard, RunId, RunRequest, RunService, RunSummary
from receipts.settings import MissingSettingError, Settings, get_settings, require_keenable_key

__all__ = ["DEMO_RUN_ID", "get_run_service", "router"]

router = APIRouter(prefix="/api", tags=["runs"])

PASSCODE_HEADER = "X-Demo-Passcode"


def get_run_service(request: Request) -> RunService:
    """`app.state.run_service` when W2 has set it, else the demo service."""
    configured: object = getattr(request.app.state, "run_service", None)
    if configured is None:
        return demo_service()
    # `RunService` is a Protocol without runtime checks; `app.state` is untyped by Starlette.
    # W2 is the only writer of this attribute and the wiring convention fixes its type.
    return cast(RunService, configured)


def check_passcode(presented: str | None, settings: Settings) -> None:
    """401 unless a non-blank passcode is configured and the header matches it (constant time)."""
    expected = settings.demo_passcode
    if expected is None or not expected.get_secret_value().strip() or presented is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "a valid X-Demo-Passcode is required")
    if not secrets.compare_digest(presented.encode(), expected.get_secret_value().encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "a valid X-Demo-Passcode is required")


def check_keenable_key(settings: Settings) -> None:
    """503 naming the variable: a run cannot start without the search and fetch key."""
    try:
        require_keenable_key(settings)
    except MissingSettingError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"{exc.name} is not set") from exc


async def check_signed_out_cap(service: RunService, settings: Settings, now: datetime) -> None:
    """429 with the start rule's reason (`20 of 20 signed-out runs used today (UTC); ...`) once
    today's runs with no user have reached the cap. Called after the passcode has matched."""
    used = await runs_today(service, None, now)
    decision = may_start(
        user=None,
        passcode_ok=True,
        user_runs_today=0,
        signed_out_runs_today=used,
        per_user_limit=settings.runs_per_user_per_day,
        signed_out_cap=settings.signed_out_runs_per_day,
    )
    if not decision.allowed:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, decision.reason)


ServiceDep = Annotated[RunService, Depends(get_run_service)]
PasscodeDep = Annotated[str | None, Header(alias=PASSCODE_HEADER)]


@router.post(
    "/runs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RunAccepted,
    responses={
        401: {"model": ErrorDetail},
        429: {"model": ErrorDetail, "description": "Today's signed-out runs are used up."},
        503: {"model": ErrorDetail},
    },
)
async def start_run(
    request: Request, body: RunRequest, service: ServiceDep, x_demo_passcode: PasscodeDep = None
) -> RunAccepted:
    settings = get_settings()
    check_passcode(x_demo_passcode, settings)  # passcode first: no cap or key status leaks
    await check_signed_out_cap(service, settings, get_clock(request)())
    check_keenable_key(settings)
    return RunAccepted(run_id=await service.start(body))


@router.get("/runs", response_model=list[RunSummary])
async def list_runs(request: Request, service: ServiceDep) -> list[RunSummary]:
    """History, newest first: with a valid session cookie, the signed-in user's runs; without
    one, the runs that belong to no user (started with the passcode)."""
    user = current_user(request, get_settings(), get_clock(request))
    summaries = await history_for(service, user)
    return sorted(summaries, key=lambda s: s.started_at, reverse=True)


@router.get("/runs/{run_id}", response_model=Battlecard, responses={404: {"model": ErrorDetail}})
async def get_run(run_id: str, service: ServiceDep) -> Battlecard:
    card = await service.get(RunId(run_id))
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"run {run_id} not found")
    return card
