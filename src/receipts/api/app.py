"""The FastAPI application. Handlers stay thin; rules live in plain functions.

Nothing here reads a secret: the api-image check boots this with an empty environment.
The `/ui` mount and the `/` redirect are Wave 0 lines; L4 adds `/api/runs*` around them.

W2 wiring: `create_app()` stores a `LazyRunService` on `app.state.run_service` and the
passcode-enforcing `starter` on `app.state.run_starter` before `mount_ui(app)`, so L4's
`get_run_service` and L5's `resolve_service` both see them. The proxy resolves the real service
on the first call that finds the three settings present (see `receipts.api.wiring`).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse

from receipts import __version__
from receipts.api.models import Health
from receipts.api.routes import router as runs_router
from receipts.api.wiring import LazyRunService, make_starter
from receipts.ui.app import UI_PATH, mount_ui

router = APIRouter()


def git_sha() -> str:
    """The commit this build came from: GIT_SHA baked in at build time, else the first seven
    characters of Render's RENDER_GIT_COMMIT (not a secret), else "unknown"."""
    baked = os.environ.get("GIT_SHA")
    if baked:
        return baked
    return os.environ.get("RENDER_GIT_COMMIT", "unknown")[:7]


@router.get("/healthz")
def healthz() -> Health:
    return Health(status="ok", sha=git_sha(), version=__version__)


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url=UI_PATH, status_code=302)


def create_app() -> FastAPI:
    app = FastAPI(title="Receipts", version=__version__)
    app.include_router(router)
    app.include_router(runs_router)
    service = LazyRunService(app)
    app.state.run_service = service
    app.state.run_starter = make_starter(service)
    mount_ui(app)
    return app


app = create_app()
