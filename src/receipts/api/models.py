"""Typed request and response bodies. Nothing untyped crosses the HTTP edge."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Health(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: str
    sha: str
    version: str
