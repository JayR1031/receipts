"""`SqlRunRepo`: the `RunRepo` protocol over the `runs` table, plus the run-to-user link.

The engine is built lazily (`LazyEngine`, shared with `SqlUserRepo` in `receipts.db.users`), on
first use, from the injected URL or from `sqlalchemy_url(get_settings().database_url)` with
`pool_pre_ping=True` (Neon suspends idle compute, ADR-0005), or injected whole so two repos share
one pool. Constructing a repo never reads settings, so the api image boots with an empty
environment; a repo used without a URL raises `MissingSettingError("DATABASE_URL")`.

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

Run-to-user link (issue #41, ADR-0008), beyond the frozen protocol: `claim_run` sets `user_id` on
a run's existing row, `list_runs_for(user_id)` and `count_runs_since(user_id, since)` scope to one
user, or with `None` to the runs that belong to no user (signed-out passcode runs). `list_runs()`
still returns every run. A placeholder row, and every run until it is claimed, has `user_id` NULL;
`save_run`, `append_event` and `save_battlecard` never touch the column, so a claim survives the
harness's later writes.

Schema on the deployed database: `create_all` creates `users` but never adds a column to the
existing Neon `runs` table, so on Postgres `create_schema` also sends `_POSTGRES_USER_ID_DDL`
(`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`): additive, idempotent, and a no-op on
a database `create_all` built fresh. SQLite gets the column from `create_all` (a fresh file or
`:memory:`) and has no `IF NOT EXISTS` on `ADD COLUMN`, so it is not sent there. The `ALTER`
takes a brief `ACCESS EXCLUSIVE` lock on `runs` once per process (`create_schema` runs on first
real use); a nullable column with no default is a catalogue-only change on Postgres.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime

from sqlalchemy import ColumnElement, Engine, StaticPool, create_engine, func, select, text
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


# Postgres only, after `create_all` (which has created `users` by then). Both are idempotent.
_POSTGRES_USER_ID_DDL = (
    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS user_id VARCHAR(64) REFERENCES users(id)",
    "CREATE INDEX IF NOT EXISTS ix_runs_user_id ON runs (user_id)",
)


def _create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        for statement in _POSTGRES_USER_ID_DDL:
            conn.execute(text(statement))


async def create_schema(engine: Engine) -> None:
    """Create `runs` and `users` if missing, and add `runs.user_id` to an existing Postgres
    `runs` table (module docstring). Safe to run repeatedly; nothing runs at import."""
    await asyncio.to_thread(_create_schema, engine)


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


def _owned_by(user_id: str | None) -> ColumnElement[bool]:
    """`user_id IS NULL` for `None` (runs that belong to no user), else that user's runs."""
    return RunRow.user_id.is_(None) if user_id is None else RunRow.user_id == user_id


def _locked_row(session: Session, run_id: RunId, created_at: datetime) -> RunRow:
    """The run's row, locked for update, created as a placeholder when it does not exist yet."""
    row = session.get(RunRow, run_id, with_for_update=True)
    if row is None:
        row = _placeholder(run_id, created_at)
        session.add(row)
    return row


class LazyEngine:
    """The engine both repos share the pattern of. `url=None` defers to `DATABASE_URL` on first
    use; an injected `engine` is used as is, so two repos can share one pool. `dispose()` disposes
    the engine either way: whoever shares one disposes it once."""

    def __init__(self, url: str | None = None, *, engine: Engine | None = None) -> None:
        self._url = url
        self._engine = engine
        self._engine_lock = threading.Lock()  # the engine is first built in worker threads

    @property
    def engine(self) -> Engine:
        with self._engine_lock:
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
        with self._engine_lock:
            engine, self._engine = self._engine, None
        if engine is not None:
            await asyncio.to_thread(engine.dispose)


class SqlRunRepo(LazyEngine):
    """See the module docstring. `url=None` defers to `DATABASE_URL` on first use."""

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
        return self._summaries()

    def _summaries(self, *where: ColumnElement[bool]) -> list[RunSummary]:
        query = select(RunRow).where(*where).order_by(RunRow.created_at.desc())
        with self._session() as session:
            rows = session.scalars(query).all()
        return [_summary(row) for row in rows]

    # --- beyond the protocol: the run-to-user link (issue #41) -----------------------------

    async def claim_run(self, run_id: RunId, user_id: str) -> None:
        """Link an existing run to the user who started it.

        Raises `LookupError` when the run has no row, and creates none: `InProcessRunService.start`
        writes the row before it returns the id, so a missing row is a wiring bug, and a silent
        no-op would leave a signed-in user's run counted and listed as a signed-out one.
        """
        await asyncio.to_thread(self._claim_run, run_id, user_id)

    def _claim_run(self, run_id: RunId, user_id: str) -> None:
        with self._session() as session, session.begin():
            row = session.get(RunRow, run_id, with_for_update=True)
            if row is None:
                raise LookupError(f"no run to claim: {run_id}")
            row.user_id = user_id

    async def list_runs_for(self, user_id: str | None) -> list[RunSummary]:
        """That user's runs, or with `None` the runs that belong to no user; newest first."""
        return await asyncio.to_thread(self._summaries, _owned_by(user_id))

    async def count_runs_since(self, user_id: str | None, since: datetime) -> int:
        """Runs with `created_at >= since` for that user (or, with `None`, for no user).
        `since` must be timezone-aware, like every stored time."""
        return await asyncio.to_thread(self._count_runs_since, user_id, since)

    def _count_runs_since(self, user_id: str | None, since: datetime) -> int:
        query = (
            select(func.count())
            .select_from(RunRow)
            .where(_owned_by(user_id), RunRow.created_at >= since)
        )
        with self._session() as session:
            return session.execute(query).scalar_one()

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
