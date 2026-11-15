"""The FastAPI application. Handlers stay thin; rules live in plain functions.

Nothing here reads a secret: the api-image check boots this with an empty environment.
The `/ui` mount and the `/` redirect are Wave 0 lines; L4 adds `/api/runs*` around them.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI
from fastapi.responses import RedirectResponse

from receipts import __version__
from receipts.api.models import Health
from receipts.api.routes import router as runs_router
from receipts.ui.app import UI_PATH, mount_ui

router = APIRouter()


def git_sha() -> str:
    """The commit this build came from; the image bakes GIT_SHA in at build time."""
    return os.environ.get("GIT_SHA", "unknown")


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
    mount_ui(app)
    return app


app = create_app()
