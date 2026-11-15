"""Prove the `runs` table's constraints reject the rows they exist to stop (spec, AGENTS.md s4).

Each test inserts one bad row with a raw `insert(runs_table)` and asserts `IntegrityError`, then
counts rows with that id: zero. A rejected insert aborts its transaction, so nothing persists;
the only valid row written (the duplicate-key test) is deleted in a `finally`. The NULL `id`
case cannot key on its id, so it compares the table's total row count before and after.

The schema has no CHECK, UNIQUE or foreign key beyond the primary key and NOT NULL columns
(`created_at`, `subject`, `rival`, `status`, `events`), so those are the constraints proven.
`varchar(n)` length limits (id 64, subject 200, status 16, ...) are intentionally untested: they
are enforced only on Postgres, raise `DataError` rather than `IntegrityError`, and are outside the
constraint kinds listed at spec:48 (NOT NULL, FK, CHECK, unique).
SQLite would also enforce these, but the module runs against Postgres only (Neon) because that
is what the constraints protect in production; it is skipped, by name, without `DATABASE_URL`.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import Engine, Table, create_engine, delete, func, insert, null, select
from sqlalchemy.exc import IntegrityError

from receipts.db import create_schema
from receipts.db.schema import RunRow
from receipts.settings import sqlalchemy_url

pytestmark = pytest.mark.integration

assert isinstance(RunRow.__table__, Table)
RUNS: Table = RunRow.__table__


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip(
            "DATABASE_URL not set: runs-table constraint tests (test_db_constraints) skipped"
        )
    eng = create_engine(sqlalchemy_url(url), pool_pre_ping=True)
    try:
        asyncio.run(create_schema(eng))
        yield eng
    finally:
        eng.dispose()


def _new_id() -> str:
    return f"constraint-test-{uuid4()}"


def _valid(run_id: str) -> dict[str, object]:
    return {
        "id": run_id,
        "created_at": datetime.now(tz=UTC),
        "subject": "subject",
        "rival": "rival",
        "status": "running",
        "events": [],
    }


def _count(engine: Engine, run_id: str) -> int:
    with engine.connect() as conn:
        return conn.execute(
            select(func.count()).select_from(RUNS).where(RUNS.c.id == run_id)
        ).scalar_one()


def _assert_rejected(engine: Engine, values: dict[str, object]) -> None:
    run_id = str(values["id"])
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(insert(RUNS).values(**values))
    assert _count(engine, run_id) == 0


def test_duplicate_primary_key_is_rejected(engine: Engine) -> None:
    run_id = _new_id()
    try:
        with engine.begin() as conn:
            conn.execute(insert(RUNS).values(**_valid(run_id)))
        with pytest.raises(IntegrityError), engine.begin() as conn:
            conn.execute(insert(RUNS).values(**_valid(run_id)))
        assert _count(engine, run_id) == 1
    finally:
        with engine.begin() as conn:
            conn.execute(delete(RUNS).where(RUNS.c.id == run_id))
    assert _count(engine, run_id) == 0


@pytest.mark.parametrize("column", ["subject", "rival", "status", "created_at", "events"])
def test_null_in_required_column_is_rejected(engine: Engine, column: str) -> None:
    values = _valid(_new_id())
    values[column] = null()  # SQL NULL; a bare None in a JSON column binds JSON 'null'
    _assert_rejected(engine, values)


def test_null_id_is_rejected(engine: Engine) -> None:
    with engine.connect() as conn:
        before = conn.execute(select(func.count()).select_from(RUNS)).scalar_one()
    values = _valid(_new_id())
    values["id"] = null()  # the primary key implies NOT NULL; no id to key a count on
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(insert(RUNS).values(**values))
    with engine.connect() as conn:
        after = conn.execute(select(func.count()).select_from(RUNS)).scalar_one()
    assert after == before
