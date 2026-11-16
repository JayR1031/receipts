"""Prove the `runs` and `users` constraints reject the rows they exist to stop (AGENTS.md s4).

Each test inserts one bad row with a raw `insert(...)` and asserts `IntegrityError`, then counts
rows with that key: zero. A rejected insert aborts its transaction, so nothing persists; every
valid row a test writes (the duplicate-key tests, the `claim_run` round trip) is deleted in a
`finally` and counted again afterwards: zero. The NULL `id` case cannot key on its id, so it
compares the table's total row count before and after.

Constraints proven: the `runs` primary key and NOT NULL columns (`created_at`, `subject`, `rival`,
`status`, `events`); the `users.sub` UNIQUE (issue #41); and the `runs.user_id` foreign key to
`users.id` (issue #41), which `create_schema` adds to the deployed `runs` table with
`ALTER TABLE ... ADD COLUMN IF NOT EXISTS` because `create_all` never adds a column to an existing
table. The rejections assert the Postgres SQLSTATE too (23505 unique, 23503 foreign key), so a
row refused for some other reason does not pass for the constraint under test.

Why a mapping-versus-Neon check sits beside the `users.sub` rejection: once `users` exists on
Neon, `create_all` never touches it again, so dropping `unique=True` from `UserRow.sub` would leave
the rejection test green while a fresh database got no UNIQUE. The drift check turns that red.

`varchar(n)` length limits (id 64, subject 200, status 16, ...) are intentionally untested: they
are enforced only on Postgres, raise `DataError` rather than `IntegrityError`, and are outside the
constraint kinds listed at spec:48 (NOT NULL, FK, CHECK, unique).
SQLite would also enforce most of these, but the module runs against Postgres only (Neon) because
that is what the constraints protect in production; it is skipped, by name, without
`DATABASE_URL`. Synthetic identities only: `fake-sub-<uuid>`, `...@example.com`, run ids
`constraint-test-<uuid>`.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import (
    ColumnElement,
    Engine,
    Table,
    create_engine,
    delete,
    func,
    insert,
    inspect,
    null,
    select,
)
from sqlalchemy.exc import IntegrityError

from receipts.contracts import RunId
from receipts.db import SqlRunRepo, SqlUserRepo, create_schema
from receipts.db.schema import RunRow, UserRow
from receipts.settings import sqlalchemy_url

pytestmark = pytest.mark.integration

assert isinstance(RunRow.__table__, Table)
assert isinstance(UserRow.__table__, Table)
RUNS: Table = RunRow.__table__
USERS: Table = UserRow.__table__


@pytest.fixture(scope="module")
def engine() -> Iterator[Engine]:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip(
            "DATABASE_URL not set: runs and users constraint tests (test_db_constraints) skipped"
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


def _rows(engine: Engine, table: Table, where: ColumnElement[bool]) -> int:
    with engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(table).where(where)).scalar_one()


def _sqlstate(error: IntegrityError) -> object:
    """The Postgres SQLSTATE psycopg attaches to the driver error (`23505`, `23503`, ...)."""
    return getattr(error.orig, "sqlstate", None)


def _assert_rejected(
    engine: Engine, values: dict[str, object], sqlstate: str | None = None
) -> None:
    run_id = str(values["id"])
    with pytest.raises(IntegrityError) as excinfo, engine.begin() as conn:
        conn.execute(insert(RUNS).values(**values))
    if sqlstate is not None:
        assert _sqlstate(excinfo.value) == sqlstate
    assert _count(engine, run_id) == 0


def _new_sub() -> str:
    return f"fake-sub-{uuid4()}"


def _valid_user(user_id: str, sub: str) -> dict[str, object]:
    return {
        "id": user_id,
        "sub": sub,
        "email": "constraint-test@example.com",
        "created_at": datetime.now(tz=UTC),
    }


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


# --- issue #41: users.sub UNIQUE, runs.user_id foreign key, the ALTER on the deployed table ---


def test_duplicate_user_sub_is_rejected(engine: Engine) -> None:
    sub = _new_sub()
    first, second = f"constraint-test-user-{uuid4()}", f"constraint-test-user-{uuid4()}"
    try:
        with engine.begin() as conn:
            conn.execute(insert(USERS).values(**_valid_user(first, sub)))
        with pytest.raises(IntegrityError) as excinfo, engine.begin() as conn:
            conn.execute(insert(USERS).values(**_valid_user(second, sub)))  # a new id, same sub
        assert _sqlstate(excinfo.value) == "23505"  # unique_violation, not the primary key
        assert _rows(engine, USERS, USERS.c.sub == sub) == 1  # 1 of the 1 row written
    finally:
        with engine.begin() as conn:
            conn.execute(delete(USERS).where(USERS.c.sub == sub))
    assert _rows(engine, USERS, USERS.c.sub == sub) == 0


def test_users_unique_on_neon_matches_the_mapping(engine: Engine) -> None:
    """Drift check: the UNIQUE the mapping declares is the UNIQUE Neon enforces (`sub` only)."""
    declared = {column.name for column in USERS.columns if column.unique}
    deployed = {
        name
        for constraint in inspect(engine).get_unique_constraints("users")
        for name in constraint["column_names"]
    }
    assert declared == deployed == {"sub"}


def test_run_user_id_naming_no_user_is_rejected(engine: Engine) -> None:
    values = _valid(_new_id())
    values["user_id"] = f"user-missing-{uuid4().hex}"
    _assert_rejected(engine, values, sqlstate="23503")  # foreign_key_violation


async def test_claim_run_round_trip_writes_user_id_on_neon(engine: Engine) -> None:
    """The column exists on the deployed table: `claim_run` writes it, the scoped reads see it."""
    sub, run_id = _new_sub(), _new_id()
    since = datetime.now(tz=UTC)
    runs, users = SqlRunRepo(engine=engine), SqlUserRepo(engine=engine)
    try:
        user = await users.get_or_create(sub, "constraint-test@example.com", since)
        with engine.begin() as conn:
            conn.execute(insert(RUNS).values(**_valid(run_id)))
        await runs.claim_run(RunId(run_id), user.id)
        with engine.connect() as conn:
            stored = conn.execute(select(RUNS.c.user_id).where(RUNS.c.id == run_id)).scalar_one()
        assert stored == user.id
        assert [s.run_id for s in await runs.list_runs_for(user.id)] == [RunId(run_id)]
        assert await runs.count_runs_since(user.id, since) == 1
    finally:
        with engine.begin() as conn:
            conn.execute(delete(RUNS).where(RUNS.c.id == run_id))
            conn.execute(delete(USERS).where(USERS.c.sub == sub))
    assert _count(engine, run_id) == 0
    assert _rows(engine, USERS, USERS.c.sub == sub) == 0


def test_create_schema_twice_is_idempotent_on_neon(engine: Engine) -> None:
    """The fixture ran it once; two more runs raise nothing and add no second FK or index."""
    asyncio.run(create_schema(engine))
    asyncio.run(create_schema(engine))
    inspector = inspect(engine)
    assert "user_id" in {column["name"] for column in inspector.get_columns("runs")}
    user_fks = [
        fk for fk in inspector.get_foreign_keys("runs") if fk["constrained_columns"] == ["user_id"]
    ]
    assert [(fk["referred_table"], fk["referred_columns"]) for fk in user_fks] == [
        ("users", ["id"])
    ]
    user_id_indexes = [
        index for index in inspector.get_indexes("runs") if index["column_names"] == ["user_id"]
    ]
    assert [index["name"] for index in user_id_indexes] == ["ix_runs_user_id"]
