"""`SqlUserRepo` and the run-to-user link on SQLite `:memory:` (issue #41, ADR-0008).

Synthetic identities only (`fake-sub-...`, `...@example.com`); no network, no `DATABASE_URL`.
The Neon side (the `users.sub` UNIQUE and the `runs.user_id` foreign key on the deployed table)
is proven in `tests/test_db_constraints.py`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from receipts.contracts import Battlecard, RunId, RunSummary, StartedEvent
from receipts.db import SqlRunRepo, SqlUserRepo, UserRow, create_schema, make_engine
from receipts.settings import MissingSettingError, get_settings

T0 = datetime(2026, 11, 15, 9, 0, tzinfo=UTC)
SUB = "fake-sub-0001"
EMAIL = "first@example.com"


@dataclass(frozen=True)
class Repos:
    runs: SqlRunRepo
    users: SqlUserRepo


@pytest.fixture
async def repos() -> AsyncIterator[Repos]:
    """One shared `:memory:` engine, injected into both repos, as the wiring will share one."""
    engine = make_engine("sqlite:///:memory:")
    await create_schema(engine)
    yield Repos(runs=SqlRunRepo(engine=engine), users=SqlUserRepo(engine=engine))
    engine.dispose()


def _summary(run_id: str, started_at: datetime) -> RunSummary:
    return RunSummary(
        run_id=RunId(run_id),
        subject="Acme Widgets",
        rival="Zeta Gadgets",
        status="running",
        verified_count=0,
        total_count=0,
        started_at=started_at,
    )


def _user_rows(users: SqlUserRepo) -> int:
    with users.engine.connect() as conn:
        return conn.execute(select(func.count()).select_from(UserRow)).scalar_one()


async def _run(repos: Repos, run_id: str, at: datetime, user_id: str | None = None) -> RunId:
    rid = RunId(run_id)
    await repos.runs.save_run(_summary(run_id, at))
    if user_id is not None:
        await repos.runs.claim_run(rid, user_id)
    return rid


# --- SqlUserRepo ---------------------------------------------------------------------------


async def test_get_or_create_is_idempotent_on_sub(repos: Repos) -> None:
    first = await repos.users.get_or_create(SUB, EMAIL, T0)
    again = await repos.users.get_or_create(SUB, "changed@example.com", T0 + timedelta(days=1))

    assert again == first  # same id, original email and created_at: the first row is the user
    assert first.id.startswith("user-")
    assert (first.sub, first.email, first.created_at) == (SUB, EMAIL, T0)
    assert _user_rows(repos.users) == 1  # 1 of 1 rows


async def test_two_subs_are_two_users(repos: Repos) -> None:
    one = await repos.users.get_or_create("fake-sub-0001", "one@example.com", T0)
    two = await repos.users.get_or_create("fake-sub-0002", "two@example.com", T0)

    assert one.id != two.id
    assert _user_rows(repos.users) == 2


async def test_get_returns_the_user_or_none(repos: Repos) -> None:
    created = await repos.users.get_or_create(SUB, EMAIL, T0)

    assert await repos.users.get(created.id) == created
    assert await repos.users.get("user-nobody") is None


async def test_a_concurrent_first_sign_in_that_wins_the_insert_is_re_read(
    repos: Repos, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two first sign-ins with one `sub`: the loser's insert hits the UNIQUE and re-reads."""
    winner = await repos.users.get_or_create(SUB, EMAIL, T0)
    real_by_sub = repos.users._by_sub
    calls: list[str] = []

    def miss_first_lookup(sub: str) -> object:
        calls.append(sub)
        return None if len(calls) == 1 else real_by_sub(sub)

    monkeypatch.setattr(repos.users, "_by_sub", miss_first_lookup)

    loser = await repos.users.get_or_create(SUB, "other@example.com", T0 + timedelta(seconds=1))

    assert loser == winner
    assert calls == [SUB, SUB]  # the miss, then the re-read after the unique violation
    assert _user_rows(repos.users) == 1


async def test_user_repo_without_url_fails_on_first_use_not_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        users = SqlUserRepo()  # construction never touches settings or the network
        with pytest.raises(MissingSettingError) as excinfo:
            await users.get("user-nobody")
        assert excinfo.value.name == "DATABASE_URL"
    finally:
        get_settings.cache_clear()


# --- the run-to-user link ------------------------------------------------------------------


async def test_a_claimed_run_is_listed_for_its_user_and_not_for_signed_out(
    repos: Repos,
) -> None:
    user = await repos.users.get_or_create(SUB, EMAIL, T0)
    claimed = await _run(repos, "run-claimed", T0, user.id)

    mine = await repos.runs.list_runs_for(user.id)
    signed_out = await repos.runs.list_runs_for(None)

    assert [s.run_id for s in mine] == [claimed]
    assert claimed not in {s.run_id for s in signed_out}


async def test_a_run_never_claimed_is_listed_for_signed_out_only(repos: Repos) -> None:
    user = await repos.users.get_or_create(SUB, EMAIL, T0)
    unclaimed = await _run(repos, "run-unclaimed", T0)

    assert [s.run_id for s in await repos.runs.list_runs_for(None)] == [unclaimed]
    assert await repos.runs.list_runs_for(user.id) == []


async def test_list_runs_for_is_newest_first_and_only_that_user(repos: Repos) -> None:
    one = await repos.users.get_or_create("fake-sub-0001", "one@example.com", T0)
    two = await repos.users.get_or_create("fake-sub-0002", "two@example.com", T0)
    older = await _run(repos, "run-one-older", T0, one.id)
    newer = await _run(repos, "run-one-newer", T0 + timedelta(minutes=5), one.id)
    await _run(repos, "run-two", T0 + timedelta(minutes=1), two.id)

    assert [s.run_id for s in await repos.runs.list_runs_for(one.id)] == [newer, older]


async def test_list_runs_still_returns_every_run(repos: Repos) -> None:
    """The frozen `RunRepo.list_runs()`: every run, claimed or not, newest first."""
    user = await repos.users.get_or_create(SUB, EMAIL, T0)
    unclaimed = await _run(repos, "run-unclaimed", T0)
    claimed = await _run(repos, "run-claimed", T0 + timedelta(minutes=1), user.id)

    assert [s.run_id for s in await repos.runs.list_runs()] == [claimed, unclaimed]


async def _still_claimed(repos: Repos, user_id: str, run_id: RunId) -> None:
    assert [s.run_id for s in await repos.runs.list_runs_for(user_id)] == [run_id]
    assert await repos.runs.list_runs_for(None) == []


async def test_a_claim_survives_the_later_save_run_append_event_and_save_battlecard(
    repos: Repos,
) -> None:
    """The harness writes the run again after `start` returns: all three writes keep the claim."""
    user = await repos.users.get_or_create(SUB, EMAIL, T0)
    claimed = await _run(repos, "run-claimed", T0, user.id)

    await repos.runs.save_run(_summary("run-claimed", T0).model_copy(update={"status": "done"}))
    await _still_claimed(repos, user.id, claimed)

    await repos.runs.append_event(
        StartedEvent(
            run_id=claimed,
            ts=T0,
            subject="Acme Widgets",
            rival="Zeta Gadgets",
            domains=("pricing",),
        )
    )
    await _still_claimed(repos, user.id, claimed)

    await repos.runs.save_battlecard(
        Battlecard(
            run_id=claimed,
            subject="Acme Widgets",
            rival="Zeta Gadgets",
            claims=(),
            verified_count=0,
            total_count=0,
            started_at=T0,
            finished_at=T0 + timedelta(minutes=1),
        )
    )
    await _still_claimed(repos, user.id, claimed)


async def test_claim_run_on_a_missing_run_raises_lookup_error(repos: Repos) -> None:
    user = await repos.users.get_or_create(SUB, EMAIL, T0)

    with pytest.raises(LookupError, match="run-missing"):
        await repos.runs.claim_run(RunId("run-missing"), user.id)
    assert await repos.runs.list_runs() == []  # no placeholder row was created


# --- count_runs_since ----------------------------------------------------------------------


async def test_count_runs_since_counts_only_the_window_and_only_that_user(
    repos: Repos,
) -> None:
    since = T0 + timedelta(hours=1)
    one = await repos.users.get_or_create("fake-sub-0001", "one@example.com", T0)
    two = await repos.users.get_or_create("fake-sub-0002", "two@example.com", T0)
    await _run(repos, "run-one-before", since - timedelta(seconds=1), one.id)
    await _run(repos, "run-one-at", since, one.id)  # `created_at >= since`: the boundary counts
    await _run(repos, "run-one-after", since + timedelta(minutes=5), one.id)
    await _run(repos, "run-two-after", since + timedelta(minutes=5), two.id)
    await _run(repos, "run-signed-out-after", since + timedelta(minutes=5))

    assert await repos.runs.count_runs_since(one.id, since) == 2
    assert await repos.runs.count_runs_since(two.id, since) == 1


async def test_count_runs_since_none_counts_only_runs_with_no_user(repos: Repos) -> None:
    since = T0 + timedelta(hours=1)
    user = await repos.users.get_or_create(SUB, EMAIL, T0)
    await _run(repos, "run-signed-out-before", since - timedelta(minutes=1))
    await _run(repos, "run-signed-out-at", since)
    await _run(repos, "run-signed-out-after", since + timedelta(minutes=1))
    await _run(repos, "run-user-after", since + timedelta(minutes=1), user.id)

    assert await repos.runs.count_runs_since(None, since) == 2
    assert await repos.runs.count_runs_since(user.id, since) == 1
