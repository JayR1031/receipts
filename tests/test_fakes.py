"""W0 fakes: what every lane's unit tests run against instead of the network."""

from __future__ import annotations

from datetime import UTC, datetime

from receipts.contracts import (
    Battlecard,
    Claim,
    DoneEvent,
    RunEvent,
    RunId,
    RunRequest,
    RunSummary,
)
from receipts.fakes import FakeKeenable, FakeRunService, InMemoryRunRepo, fake_llm

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def _summary(run_id: str, minute: int) -> RunSummary:
    return RunSummary(
        run_id=RunId(run_id),
        subject="Acme Widgets",
        rival="Zeta Gadgets",
        status="done",
        verified_count=0,
        total_count=0,
        started_at=T0.replace(minute=minute),
    )


async def test_in_memory_repo_returns_what_was_saved_newest_first(
    fake_repo: InMemoryRunRepo, sample_claims: list[Claim], sample_events: list[RunEvent]
) -> None:
    await fake_repo.save_run(_summary("run-older", 1))
    await fake_repo.save_run(_summary("run-newer", 2))
    for event in sample_events:
        await fake_repo.append_event(event)
    card = Battlecard(
        run_id=RunId("run-newer"),
        subject="Acme Widgets",
        rival="Zeta Gadgets",
        claims=tuple(sample_claims),
        verified_count=2,
        total_count=3,
        started_at=T0,
        finished_at=T0.replace(minute=3),
    )
    await fake_repo.save_battlecard(card)

    assert await fake_repo.get_run(RunId("run-newer")) == card
    assert await fake_repo.get_run(RunId("run-missing")) is None
    assert [s.run_id for s in await fake_repo.list_runs()] == ["run-newer", "run-older"]
    assert fake_repo.events[sample_events[0].run_id] == sample_events


async def test_fake_run_service_replays_the_script_in_order(
    fake_run_service: FakeRunService, sample_events: list[RunEvent]
) -> None:
    run_id = await fake_run_service.start(
        RunRequest(subject="Acme Widgets", rival="Zeta Gadgets", category="widgets")
    )
    seen = [event async for event in fake_run_service.events(run_id)]
    assert seen == sample_events
    assert isinstance(seen[-1], DoneEvent)
    assert [s.run_id for s in await fake_run_service.list()] == [run_id]
    card = await fake_run_service.get(run_id)
    assert card is not None and (card.verified_count, card.total_count) == (2, 3)


def test_fake_keenable_serves_fixtures_and_fails_unknown_urls(fake_keenable: FakeKeenable) -> None:
    hits = fake_keenable.search("acme widgets pricing")
    assert [hit.url for hit in hits] == ["https://acme-widgets.example/pricing"]
    assert fake_keenable.search("nothing matches this").__len__() == 0
    assert fake_keenable.fetch("https://acme-widgets.example/pricing").ok is True
    missing = fake_keenable.fetch("https://unknown.example/")
    assert missing.ok is False and missing.url == "https://unknown.example/"


def test_fake_llm_returns_the_scripted_responses() -> None:
    llm = fake_llm(["hi", "there"])
    assert llm.invoke("x").content == "hi"
    assert llm.invoke("y").content == "there"
