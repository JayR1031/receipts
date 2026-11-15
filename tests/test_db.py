"""`SqlRunRepo` on SQLite: the one `runs` table round-trips every contract it stores.

All text here is invented: no real companies, people, usernames or keys. No network, and no
`DATABASE_URL`: the Neon round-trip is the `integration`-marked test at the bottom.
"""

from __future__ import annotations

import os
import threading
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import Engine

from receipts.contracts import (
    RUN_EVENT_ADAPTER,
    Battlecard,
    Claim,
    ErrorEvent,
    RunEvent,
    RunId,
    RunSummary,
)
from receipts.db import SqlRunRepo, create_schema
from receipts.db import repo as repo_module
from receipts.settings import MissingSettingError, get_settings

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
RUN_ID = RunId("run-sample-0001")


def _summary(run_id: RunId, started_at: datetime) -> RunSummary:
    return RunSummary(
        run_id=run_id,
        subject="Acme Widgets",
        rival="Zeta Gadgets",
        status="running",
        verified_count=0,
        total_count=0,
        started_at=started_at,
    )


@pytest.fixture(params=["file", "memory"])
async def repo(tmp_path: Path, request: pytest.FixtureRequest) -> AsyncIterator[SqlRunRepo]:
    url = "sqlite:///:memory:" if request.param == "memory" else f"sqlite:///{tmp_path / 'r.db'}"
    repo = SqlRunRepo(url=url)
    await create_schema(repo.engine)
    yield repo
    await repo.dispose()


async def test_every_event_kind_round_trips_in_order(
    repo: SqlRunRepo, sample_events: list[RunEvent]
) -> None:
    kinds = {e.kind for e in sample_events}
    assert len(kinds) == 8, "the fixture covers every RunEvent kind"
    await repo.save_run(_summary(RUN_ID, T0))
    for event in sample_events:
        await repo.append_event(event)

    stored = await repo.get_events(RUN_ID)

    assert stored == sample_events
    for event in stored:
        dumped = RUN_EVENT_ADAPTER.dump_python(event, mode="json")
        assert RUN_EVENT_ADAPTER.validate_python(dumped) == event


async def test_save_battlecard_then_get_run_returns_it(
    repo: SqlRunRepo, sample_claims: list[Claim]
) -> None:
    await repo.save_run(_summary(RUN_ID, T0))
    card = Battlecard(
        run_id=RUN_ID,
        subject="Acme Widgets",
        rival="Zeta Gadgets",
        claims=tuple(sample_claims),
        verified_count=2,
        total_count=3,
        started_at=T0,
        finished_at=T0 + timedelta(seconds=7),
    )
    assert await repo.get_run(RUN_ID) is None

    await repo.save_battlecard(card)

    assert await repo.get_run(RUN_ID) == card
    assert card.started_at.tzinfo is not None
    [listed] = await repo.list_runs()
    assert (listed.status, listed.verified_count, listed.total_count) == ("done", 2, 3)
    assert listed.started_at == T0


async def test_list_runs_is_newest_first(repo: SqlRunRepo) -> None:
    older = RunId("run-older")
    newer = RunId("run-newer")
    await repo.save_run(_summary(older, T0))
    await repo.save_run(_summary(newer, T0 + timedelta(minutes=5)))

    listed = await repo.list_runs()

    assert [s.run_id for s in listed] == [newer, older]
    assert all(s.started_at.tzinfo is not None for s in listed)


async def test_events_alone_set_status_counts_and_names(
    repo: SqlRunRepo, sample_events: list[RunEvent]
) -> None:
    """No `save_battlecard`: the list row is derived from the Started and Done events."""
    pending = _summary(RUN_ID, T0).model_copy(update={"subject": "pending", "rival": "pending"})
    await repo.save_run(pending)
    for event in sample_events:
        await repo.append_event(event)

    [listed] = await repo.list_runs()

    assert await repo.get_run(RUN_ID) is None
    assert listed.status == "done"
    assert (listed.verified_count, listed.total_count) == (2, 3)  # from the DoneEvent
    assert (listed.subject, listed.rival) == ("Acme Widgets", "Zeta Gadgets")  # StartedEvent


async def test_error_event_sets_status_error(
    repo: SqlRunRepo, sample_events: list[RunEvent]
) -> None:
    await repo.save_run(_summary(RUN_ID, T0))
    for event in sample_events:
        await repo.append_event(event)
        if isinstance(event, ErrorEvent):
            break

    [listed] = await repo.list_runs()

    assert listed.status == "error"
    assert (listed.verified_count, listed.total_count) == (0, 0)  # no DoneEvent yet


async def test_event_before_save_run_creates_a_placeholder_row(
    repo: SqlRunRepo, sample_events: list[RunEvent]
) -> None:
    """Placeholder rows: an event for an unknown run creates the row, listed as `running`."""
    started, search = sample_events[0], sample_events[1]

    await repo.append_event(search)  # first event is not a StartedEvent
    [blank] = await repo.list_runs()
    assert (blank.subject, blank.rival, blank.status) == ("", "", "running")
    assert blank.started_at == search.ts

    await repo.append_event(started)  # the StartedEvent fills the names in
    [filled] = await repo.list_runs()
    assert (filled.subject, filled.rival, filled.status) == ("Acme Widgets", "Zeta Gadgets", "running")
    assert [e.kind for e in await repo.get_events(RUN_ID)] == ["search", "started"]


def test_concurrent_first_use_builds_one_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    built: list[object] = []
    real_make_engine = repo_module.make_engine

    def slow_make_engine(url: str) -> Engine:
        time.sleep(0.05)  # widen the window in which a second thread would also see None
        engine = real_make_engine(url)
        built.append(engine)
        return engine

    monkeypatch.setattr(repo_module, "make_engine", slow_make_engine)
    repo = SqlRunRepo(url=f"sqlite:///{tmp_path / 'race.db'}")
    engines: list[Engine] = []
    threads = [threading.Thread(target=lambda: engines.append(repo.engine)) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(built) == 1
    assert len({id(e) for e in engines}) == 1


async def test_get_run_unknown_is_none(repo: SqlRunRepo) -> None:
    assert await repo.get_run(RunId("run-nope")) is None
    assert await repo.get_events(RunId("run-nope")) == []


async def test_repo_without_url_fails_on_first_use_not_construction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    get_settings.cache_clear()
    try:
        repo = SqlRunRepo()  # construction never touches settings or the network
        with pytest.raises(MissingSettingError) as excinfo:
            await repo.list_runs()
        assert excinfo.value.name == "DATABASE_URL"
        assert "DATABASE_URL" in str(excinfo.value)
    finally:
        get_settings.cache_clear()


@pytest.mark.integration
async def test_neon_round_trip(sample_events: list[RunEvent]) -> None:
    """Needs `DATABASE_URL` (Neon `dev` branch). Skipped, by name, when it is not set."""
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set: Neon round-trip (test_neon_round_trip) skipped")
    get_settings.cache_clear()
    run_id = RunId(f"run-integration-{int(datetime.now(tz=UTC).timestamp())}")
    repo = SqlRunRepo()
    try:
        await create_schema(repo.engine)
        await repo.save_run(_summary(run_id, datetime.now(tz=UTC)))
        for event in sample_events:
            await repo.append_event(event.model_copy(update={"run_id": run_id}))
        stored = await repo.get_events(run_id)
        assert [e.kind for e in stored] == [e.kind for e in sample_events]
        assert run_id in {s.run_id for s in await repo.list_runs()}
    finally:
        await repo.delete_run(run_id)
        await repo.dispose()
        get_settings.cache_clear()
