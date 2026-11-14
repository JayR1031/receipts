"""Shared, frozen contracts for every lane.

Pure data and protocols: nothing here reads a database, the network or the clock.
Timestamps are fields the caller supplies. Frozen after Wave 0 (AGENTS.md section 9).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Annotated, Literal, NewType, Protocol

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter

Domain = Literal["pricing", "positioning_seo", "news_social", "product"]
About = Literal["subject", "rival"]
VerifyMethod = Literal["quote_exact", "quote_fuzzy", "search_log"]
RunStatus = Literal["queued", "running", "done", "error"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]

RunId = NewType("RunId", str)


class _Frozen(BaseModel):
    """Every contract is immutable and rejects unknown fields."""

    model_config = ConfigDict(frozen=True, extra="forbid")


# --- receipts and claims -------------------------------------------------------------


class QuoteReceipt(_Frozen):
    kind: Literal["quote"] = "quote"
    url: str
    quote: str


class SearchReceipt(_Frozen):
    kind: Literal["search"] = "search"
    query: str
    rank: int
    url: str
    ts: datetime


Receipt = Annotated[QuoteReceipt | SearchReceipt, Field(discriminator="kind")]


class Claim(_Frozen):
    domain: Domain
    about: About
    text: str
    receipt: Receipt
    verified: bool = False
    verify_method: VerifyMethod | None = None
    verify_note: str | None = None


# --- requests, search and fetch ------------------------------------------------------


class RunRequest(_Frozen):
    subject: str
    rival: str
    category: str | None = None


class SearchResult(_Frozen):
    query: str
    rank: int
    url: str
    title: str
    snippet: str
    ts: datetime


class FetchedPage(_Frozen):
    url: str
    text: str
    fetched_at: datetime
    ok: bool


# --- run events ------------------------------------------------------------------


class _EventBase(_Frozen):
    run_id: RunId
    ts: datetime
    domain: Domain | None = None


class StartedEvent(_EventBase):
    kind: Literal["started"] = "started"
    subject: str
    rival: str
    category: str | None = None
    domains: tuple[Domain, ...]


class SearchEvent(_EventBase):
    kind: Literal["search"] = "search"
    query: str
    results: tuple[SearchResult, ...]


class FetchEvent(_EventBase):
    kind: Literal["fetch"] = "fetch"
    url: str
    ok: bool


class ClaimEvent(_EventBase):
    kind: Literal["claim"] = "claim"
    claim: Claim


class VerifiedEvent(_EventBase):
    kind: Literal["verified"] = "verified"
    claim: Claim


class DroppedEvent(_EventBase):
    kind: Literal["dropped"] = "dropped"
    claim: Claim
    reason: str


class DoneEvent(_EventBase):
    kind: Literal["done"] = "done"
    verified_count: int
    total_count: int


class ErrorEvent(_EventBase):
    kind: Literal["error"] = "error"
    message: str


RunEvent = Annotated[
    StartedEvent
    | SearchEvent
    | FetchEvent
    | ClaimEvent
    | VerifiedEvent
    | DroppedEvent
    | DoneEvent
    | ErrorEvent,
    Field(discriminator="kind"),
]
RUN_EVENT_ADAPTER: TypeAdapter[RunEvent] = TypeAdapter(RunEvent)


# --- results -----------------------------------------------------------------------


class Battlecard(_Frozen):
    run_id: RunId
    subject: str
    rival: str
    claims: tuple[Claim, ...]
    verified_count: int
    total_count: int
    started_at: datetime
    finished_at: datetime


class RunSummary(_Frozen):
    run_id: RunId
    subject: str
    rival: str
    status: RunStatus
    verified_count: int
    total_count: int
    started_at: datetime


# --- domain packs (the YAML schema L1 loads and L3 writes) ---------------------------


class DomainPack(_Frozen):
    id: Domain
    display_name: str
    model: str
    effort: Effort | None = None
    system_prompt: str
    query_templates: tuple[str, ...]
    source_allow: tuple[str, ...] = ()
    source_deny: tuple[str, ...] = ()
    max_searches: int = 3
    max_fetches: int = 4
    timeout_s: int = 120
    extra_fields: tuple[str, ...] = ()
    rubric: str = ""


# --- protocols: the seams the fakes and the real clients both satisfy -------------------


class SearchClient(Protocol):
    def search(self, query: str) -> list[SearchResult]: ...


class FetchClient(Protocol):
    def fetch(self, url: str) -> FetchedPage: ...


class RunRepo(Protocol):
    async def save_run(self, summary: RunSummary) -> None: ...

    async def append_event(self, event: RunEvent) -> None: ...

    async def save_battlecard(self, card: Battlecard) -> None: ...

    async def get_run(self, run_id: RunId) -> Battlecard | None: ...

    async def list_runs(self) -> list[RunSummary]: ...


class RunService(Protocol):
    async def start(self, request: RunRequest) -> RunId: ...

    def events(self, run_id: RunId) -> AsyncIterator[RunEvent]: ...

    async def get(self, run_id: RunId) -> Battlecard | None: ...

    async def list(self) -> list[RunSummary]: ...
