"""`SqlRunRepo`: the `RunRepo` protocol over the `runs` table.

The engine is built lazily, on first use, from the injected URL or from
`sqlalchemy_url(get_settings().database_url)` with `pool_pre_ping=True` (Neon suspends idle
compute, ADR-0005). Constructing a repo never reads settings, so the api image boots with an
empty environment; a repo used without a URL raises `MissingSettingError("DATABASE_URL")`.

Why a sync engine behind async methods: ADR-0006 expected `create_async_engine`, but
SQLAlchemy's asyncio extension imports `greenlet`, which the frozen `uv.lock` does not carry
(`uv add` is forbidden for lanes). Every protocol method is still `async`; the blocking
SQLAlchemy call runs in a worker thread via `asyncio.to_thread`, so the event loop is never
held during I/O. W2 can swap `make_engine` for `create_async_engine` once `greenlet` is locked;
the table, the URL rewrite and the public surface do not change.

Concurrency: `append_event` reads, extends and rewrites the `events` JSON list inside one
transaction. The demo has a single writer per run (the in-process harness), so a lost update
between two processes is not a case this table has to win; `SELECT ... FOR UPDATE` is still
sent on Postgres as a belt-and-braces lock, and is a no-op on SQLite.

Placeholder rows: an event that arrives before `save_run` creates the row with `subject=""`,
`rival=""` and `status="running"`, and `created_at` set to the event's `ts`; `list_runs()` shows
it. A later `StartedEvent` fills subject, rival and category in; `save_run` overwrites names,
`created_at` and status. A first event that is not a `StartedEvent` leaves the names empty until
one arrives.
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from sqlalchemy import Engine, StaticPool, create_engine, select
from sqlalchemy.orm import Session

from receipts.contracts import (
    RUN_EVENT_ADAPTER,
    Battlecard,
    DoneEvent,
    ErrorEvent,
    RunEvent,
    RunId,
    RunStatus,
    RunSummary,
    StartedEvent,
)
from receipts.db.schema import Base, JsonObject, RunRow
from receipts.settings import MissingSettingError, get_settings, sqlalchemy_url


def make_engine(url: str) -> Engine:
    """`create_engine` with the Neon-safe defaults; `:memory:` SQLite shares one connection."""
    if url.endswith(":memory:"):
        return create_engine(url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    return create_engine(url, pool_pre_ping=True)


async def create_schema(engine: Engine) -> None:
    """Create the `runs` table if it is missing. Tests and W2 call this; nothing runs at import."""
    await asyncio.to_thread(Base.metadata.create_all, engine)


def _status(value: str) -> RunStatus:
    if value == "queued" or value == "running" or value == "done" or value == "error":
        return value
    raise ValueError(f"unknown run status in table: {value!r}")


def _counts(row: RunRow) -> tuple[int, int]:
    """Verified/total from the battlecard when there is one, else from the `done` event, else 0."""
    if row.battlecard is not None:
        card = Battlecard.model_validate(row.battlecard)
        return card.verified_count, card.total_count
    for raw in reversed(row.events):
        event = RUN_EVENT_ADAPTER.validate_python(raw)
        if isinstance(event, DoneEvent):
            return event.verified_count, event.total_count
    return 0, 0


def _summary(row: RunRow) -> RunSummary:
    verified, total = _counts(row)
    return RunSummary(
        run_id=RunId(row.id),
        subject=row.subject,
        rival=row.rival,
        status=_status(row.status),
        verified_count=verified,
        total_count=total,
        started_at=row.created_at,
    )


def _placeholder(run_id: RunId, created_at: datetime) -> RunRow:
    """A row for an event that arrives before `save_run`; `StartedEvent` fills the names in."""
    return RunRow(
        id=run_id, created_at=created_at, subject="", rival="", status="running", events=[]
    )


def _apply_event(row: RunRow, event: RunEvent) -> None:
    """Fold what the table denormalises (names, category, terminal status) out of the event."""
    if isinstance(event, StartedEvent):
        row.subject, row.rival, row.category = event.subject, event.rival, event.category
    elif isinstance(event, DoneEvent):
        row.status = "done"
    elif isinstance(event, ErrorEvent):
        row.status = "error"


def _locked_row(session: Session, run_id: RunId, created_at: datetime) -> RunRow:
    """The run's row, locked for update, created as a placeholder when it does not exist yet."""
    row = session.get(RunRow, run_id, with_for_update=True)
    if row is None:
        row = _placeholder(run_id, created_at)
        session.add(row)
    return row


class SqlRunRepo:
    """See the module docstring. `url=None` defers to `DATABASE_URL` on first use."""

    def __init__(self, url: str | None = None, *, engine: Engine | None = None) -> None:
        self._url = url
        self._engine = engine

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            self._engine = make_engine(self._resolve_url())
        return self._engine

    def _resolve_url(self) -> str:
        if self._url is not None:
            return self._url
        database_url = get_settings().database_url
        if database_url is None:
            raise MissingSettingError("DATABASE_URL")
        return sqlalchemy_url(database_url)

    def _session(self) -> Session:
        return Session(self.engine, expire_on_commit=False)

    async def dispose(self) -> None:
        if self._engine is not None:
            await asyncio.to_thread(self._engine.dispose)
            self._engine = None

    # --- RunRepo -----------------------------------------------------------------------

    async def save_run(self, summary: RunSummary) -> None:
        await asyncio.to_thread(self._save_run, summary)

    def _save_run(self, summary: RunSummary) -> None:
        with self._session() as session, session.begin():
            row = _locked_row(session, summary.run_id, summary.started_at)
            row.subject, row.rival = summary.subject, summary.rival
            row.created_at, row.status = summary.started_at, summary.status

    async def append_event(self, event: RunEvent) -> None:
        await asyncio.to_thread(self._append_event, event)

    def _append_event(self, event: RunEvent) -> None:
        with self._session() as session, session.begin():
            row = _locked_row(session, event.run_id, event.ts)
            dumped: JsonObject = RUN_EVENT_ADAPTER.dump_python(event, mode="json")
            row.events = [*row.events, dumped]  # a new list, so the JSON column is marked dirty
            _apply_event(row, event)

    async def save_battlecard(self, card: Battlecard) -> None:
        await asyncio.to_thread(self._save_battlecard, card)

    def _save_battlecard(self, card: Battlecard) -> None:
        with self._session() as session, session.begin():
            row = _locked_row(session, card.run_id, card.started_at)
            if not row.subject:
                row.subject, row.rival = card.subject, card.rival
            row.battlecard = card.model_dump(mode="json")
            row.status = "done"

    async def get_run(self, run_id: RunId) -> Battlecard | None:
        return await asyncio.to_thread(self._get_run, run_id)

    def _get_run(self, run_id: RunId) -> Battlecard | None:
        with self._session() as session:
            row = session.get(RunRow, run_id)
        if row is None or row.battlecard is None:
            return None
        return Battlecard.model_validate(row.battlecard)

    async def list_runs(self) -> list[RunSummary]:
        """Newest first by `created_at`, the order the History list shows."""
        return await asyncio.to_thread(self._list_runs)

    def _list_runs(self) -> list[RunSummary]:
        with self._session() as session:
            rows = session.scalars(select(RunRow).order_by(RunRow.created_at.desc())).all()
        return [_summary(row) for row in rows]

    # --- beyond the protocol: used by tests, the integration clean-up and W2 ---------------

    async def get_events(self, run_id: RunId) -> list[RunEvent]:
        """Every event appended to the run, in append order; `[]` for an unknown run."""
        return await asyncio.to_thread(self._get_events, run_id)

    def _get_events(self, run_id: RunId) -> list[RunEvent]:
        with self._session() as session:
            row = session.get(RunRow, run_id)
        if row is None:
            return []
        return [RUN_EVENT_ADAPTER.validate_python(raw) for raw in row.events]

    async def delete_run(self, run_id: RunId) -> None:
        await asyncio.to_thread(self._delete_run, run_id)

    def _delete_run(self, run_id: RunId) -> None:
        with self._session() as session, session.begin():
            row = session.get(RunRow, run_id)
            if row is not None:
                session.delete(row)
