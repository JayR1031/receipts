"""The FastAPI application. Handlers stay thin; rules live in plain functions."""

from __future__ import annotations

import os

from fastapi import APIRouter, FastAPI

from receipts import __version__
from receipts.api.models import EchoIn, EchoOut, Health

router = APIRouter()


def git_sha() -> str:
    """The commit this build came from; the image bakes GIT_SHA in at build time."""
    return os.environ.get("GIT_SHA", "unknown")


@router.get("/healthz")
def healthz() -> Health:
    return Health(status="ok", sha=git_sha(), version=__version__)


@router.post("/echo")
def echo(body: EchoIn) -> EchoOut:
    return EchoOut(message=body.message, length=len(body.message))


def create_app() -> FastAPI:
    app = FastAPI(title="Receipts", version=__version__)
    app.include_router(router)
    return app


app = create_app()
