"""The FastAPI application. Handlers stay thin; rules live in plain functions.

Nothing here reads a secret: the api-image check boots this with an empty environment.
The `/ui` mount and the `/` redirect are Wave 0 lines; L4 adds `/api/runs*` around them.

W2 wiring: `create_app()` stores a `LazyRunService` on `app.state.run_service` and the
passcode-enforcing `starter` on `app.state.run_starter` before `mount_ui(app)`, so L4's
`get_run_service` and L5's `resolve_service` both see them. The proxy resolves the real service
on the first call that finds the three settings present (see `receipts.api.wiring`).

`/healthz` reports the active mode, `live` or `demo`, in the `X-Receipts-Mode` header; the JSON
body is unchanged (L4 owns the `Health` model and the OpenAPI document).

Issue #41: `create_app()` includes the `/auth/*` router and stores the live `Gate` (`LiveGate`) on
`app.state.gate` before `mount_ui(app)`, beside `run_starter` (which the UI uses when no Gate is
set). Like the proxy, the Gate reads settings per call; nothing here reads one.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.responses import RedirectResponse

from receipts import __version__
from receipts.api.models import Health
from receipts.api.routes import router as runs_router
from receipts.api.wiring import MODE_HEADER, LazyRunService, LiveGate, active_mode, make_starter
from receipts.auth.routes import router as auth_router
from receipts.ui.app import UI_PATH, mount_ui

router = APIRouter()


UNKNOWN_SHA = "unknown"


def git_sha() -> str:
    """The commit this build came from: GIT_SHA baked in at build time, else the first seven
    characters of Render's RENDER_GIT_COMMIT (not a secret), else "unknown".

    The image always sets GIT_SHA (`ARG GIT_SHA=unknown` in the Dockerfile) and Render's build
    passes no build arg, so the baked "unknown" counts as unset; otherwise `/healthz` on Render
    would never reach RENDER_GIT_COMMIT."""
    baked = os.environ.get("GIT_SHA", "").strip()
    if baked and baked != UNKNOWN_SHA:
        return baked
    return os.environ.get("RENDER_GIT_COMMIT", "").strip()[:7] or UNKNOWN_SHA


@router.get("/healthz")
def healthz(request: Request, response: Response) -> Health:
    response.headers[MODE_HEADER] = active_mode(request.app)
    return Health(status="ok", sha=git_sha(), version=__version__)


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url=UI_PATH, status_code=302)


def create_app() -> FastAPI:
    app = FastAPI(title="Receipts", version=__version__)
    app.include_router(router)
    app.include_router(runs_router)
    app.include_router(auth_router)
    service = LazyRunService(app)
    app.state.run_service = service
    app.state.run_starter = make_starter(service)
    app.state.gate = LiveGate(service, app)
    mount_ui(app)
    return app


app = create_app()
