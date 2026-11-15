"""L1: `InProcessRunService` streams events to subscribers and persists through a `RunRepo`."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from receipts.contracts import (
    Claim,
    ClaimEvent,
    DomainPack,
    DoneEvent,
    DroppedEvent,
    QuoteReceipt,
    RunEvent,
    RunId,
    RunRequest,
    StartedEvent,
    VerifiedEvent,
)
from receipts.fakes import InMemoryRunRepo, data
from receipts.harness import Coordinator, InProcessRunService

REQUEST = RunRequest(subject="Acme Widgets", rival="Zeta Gadgets", category="widgets")
T0 = datetime(2026, 11, 14, 13, 0, tzinfo=UTC)
GOOD = Claim(
    domain="pricing",
    about="subject",
    text="Acme starts at 9 dollars per seat.",
    receipt=QuoteReceipt(url=data.SUBJECT_URL, quote="Plans start at 9 dollars per seat"),
    verified=True,
    verify_method="quote_exact",
)
BAD = Claim(
    domain="pricing",
    about="rival",
    text="Zeta offers a free tier.",
    receipt=QuoteReceipt(url=data.RIVAL_URL, quote="free forever"),
)


class _TickingClock:
    def __init__(self) -> None:
        self.n = 0

    def __call__(self) -> datetime:
        self.n += 1
        return T0 + timedelta(seconds=self.n)


class _ScriptedSpecialist:
    """Two claims, one verified, one dropped; yields slowly so subscribers see a live stream."""

    async def run(
        self, run_id: RunId, request: RunRequest, pack: DomainPack
    ) -> AsyncIterator[RunEvent]:
        del request
        await asyncio.sleep(0.01)
        yield ClaimEvent(run_id=run_id, ts=T0, domain=pack.id, claim=GOOD)
        yield VerifiedEvent(run_id=run_id, ts=T0, domain=pack.id, claim=GOOD)
        yield ClaimEvent(run_id=run_id, ts=T0, domain=pack.id, claim=BAD)
        yield DroppedEvent(run_id=run_id, ts=T0, domain=pack.id, claim=BAD, reason="no quote")


def _service(sample_pack: DomainPack) -> tuple[InProcessRunService, InMemoryRunRepo]:
    clock = _TickingClock()
    coordinator = Coordinator([sample_pack], _ScriptedSpecialist(), max_concurrent=1, clock=clock)
    repo = InMemoryRunRepo()
    ids = iter(["run-svc-0001", "run-svc-0002"])
    service = InProcessRunService(
        coordinator, repo, clock=clock, new_run_id=lambda: RunId(next(ids))
    )
    return service, repo


async def test_events_end_with_done_and_get_returns_a_matching_battlecard(
    sample_pack: DomainPack,
) -> None:
    service, repo = _service(sample_pack)
    run_id = await service.start(REQUEST)
    assert run_id == "run-svc-0001"

    events = [e async for e in service.events(run_id)]
    assert isinstance(events[0], StartedEvent)
    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert (done.verified_count, done.total_count) == (1, 2)

    card = await service.get(run_id)
    assert card is not None
    assert (card.verified_count, card.total_count) == (1, 2)
    assert [c.verified for c in card.claims] == [True, False]
    assert card.started_at == events[0].ts and card.finished_at == done.ts

    summaries = await service.list()
    assert [(s.run_id, s.status, s.verified_count, s.total_count) for s in summaries] == [
        (run_id, "done", 1, 2)
    ]
    assert repo.events[run_id] == events
    assert repo.battlecards[run_id] == card


async def test_a_late_subscriber_replays_the_whole_run(sample_pack: DomainPack) -> None:
    service, _repo = _service(sample_pack)
    run_id = await service.start(REQUEST)
    live = [e async for e in service.events(run_id)]
    late = [e async for e in service.events(run_id)]
    assert late == live
    assert await service.get(RunId("run-missing")) is None
    assert [e async for e in service.events(RunId("run-missing"))] == []


async def test_start_persists_a_running_summary_before_the_run_finishes(
    sample_pack: DomainPack,
) -> None:
    service, repo = _service(sample_pack)
    run_id = await service.start(REQUEST)
    assert repo.runs[run_id].status == "running"
    await asyncio.wait_for(service.wait(run_id), timeout=2)
    assert repo.runs[run_id].status == "done"
