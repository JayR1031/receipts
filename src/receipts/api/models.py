"""Typed request and response bodies. Nothing untyped crosses the HTTP edge."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Health(BaseModel):
    model_config = ConfigDict(frozen=True)
    status: str
    sha: str
    version: str


class EchoIn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    message: str = Field(min_length=1, max_length=1000)


class EchoOut(BaseModel):
    model_config = ConfigDict(frozen=True)
    message: str
    length: int
