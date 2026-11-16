"""Typed request and response bodies. Nothing untyped crosses the HTTP edge."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from receipts.contracts import RunId


class Health(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: str
    sha: str
    version: str


class RunAccepted(BaseModel):
    """`202` body of `POST /api/runs`: the id to poll with `GET /api/runs/{run_id}`."""

    model_config = ConfigDict(frozen=True)
    run_id: RunId


class ErrorDetail(BaseModel):
    """FastAPI's error envelope, named so the OpenAPI document shows it on 401/404/429/503."""

    model_config = ConfigDict(frozen=True)
    detail: str
