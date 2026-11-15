"""`/api/runs*`. Handlers stay thin; the passcode and key rules are plain functions.

The run service is looked up per request from `app.state.run_service` (W2 sets it to the real
`InProcessRunService`); when absent, the demo `FakeRunService` answers (W1 wiring convention).
Settings are read per request through `get_settings()`, never at import or in `create_app()`.
"""

from __future__ import annotations

import secrets
from typing import Annotated, cast

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status

from receipts.api.demo import DEMO_RUN_ID, demo_service
from receipts.api.models import ErrorDetail, RunAccepted
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


ServiceDep = Annotated[RunService, Depends(get_run_service)]
PasscodeDep = Annotated[str | None, Header(alias=PASSCODE_HEADER)]


@router.post(
    "/runs",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RunAccepted,
    responses={401: {"model": ErrorDetail}, 503: {"model": ErrorDetail}},
)
async def start_run(
    body: RunRequest, service: ServiceDep, x_demo_passcode: PasscodeDep = None
) -> RunAccepted:
    settings = get_settings()
    check_passcode(x_demo_passcode, settings)  # passcode first: no key status leaks to strangers
    check_keenable_key(settings)
    return RunAccepted(run_id=await service.start(body))


@router.get("/runs", response_model=list[RunSummary])
async def list_runs(service: ServiceDep) -> list[RunSummary]:
    """History: newest first, whatever order the service hands back."""
    summaries = await service.list()
    return sorted(summaries, key=lambda s: s.started_at, reverse=True)


@router.get("/runs/{run_id}", response_model=Battlecard, responses={404: {"model": ErrorDetail}})
async def get_run(run_id: str, service: ServiceDep) -> Battlecard:
    card = await service.get(RunId(run_id))
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"run {run_id} not found")
    return card
