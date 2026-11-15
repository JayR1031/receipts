"""L1: `Coordinator` orders events, caps concurrency and survives a failing specialist."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from datetime import UTC, datetime

from langchain_core.messages import AIMessage

from receipts.contracts import (
    RUN_EVENT_ADAPTER,
    Claim,
    ClaimEvent,
    DomainPack,
    DoneEvent,
    ErrorEvent,
    FetchedPage,
    QuoteReceipt,
    RunEvent,
    RunId,
    RunRequest,
    SearchResult,
    StartedEvent,
    VerifiedEvent,
)
from receipts.fakes import FakeKeenable, data, fake_llm
from receipts.harness import Coordinator, SpecialistRunner

RUN_ID = RunId("run-l1-coord")
REQUEST = RunRequest(subject="Acme Widgets", rival="Zeta Gadgets", category="widgets")
NOW = datetime(2026, 11, 14, 13, 0, tzinfo=UTC)
SEO_CLAIM = Claim(
    domain="positioning_seo",
    about="subject",
    text="Acme says it is simple.",
    receipt=QuoteReceipt(url=data.SUBJECT_URL, quote="simple"),
    verified=True,
)


def _clock() -> datetime:
    return NOW


def _search_call(i: int, query: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {
                "name": "keenable_search",
                "args": {"query": query},
                "id": f"s{i}",
                "type": "tool_call",
            }
        ],
    )


def _final(claims: list[dict[str, object]]) -> str:
    return "Claims:\n```json\n" + json.dumps(claims) + "\n```\n"


def _mark_verified(
    claim: Claim, pages: Mapping[str, FetchedPage], rows: Sequence[SearchResult]
) -> Claim:
    del pages, rows
    return claim.model_copy(update={"verified": True, "verify_method": "quote_exact"})


def _claim_json(url: str) -> dict[str, object]:
    return {
        "about": "subject",
        "text": "Acme starts at 9 dollars per seat.",
        "receipt": {"kind": "quote", "url": url, "quote": "Plans start at 9 dollars per seat"},
    }


async def test_coordinator_yields_started_first_done_last_and_events_round_trip(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    seo = sample_pack.model_copy(update={"id": "positioning_seo", "display_name": "SEO"})
    runner = SpecialistRunner(
        fake_keenable,
        fake_keenable,
        model_factory=lambda _p: fake_llm(
            [_search_call(1, "acme widgets pricing"), _final([_claim_json(data.SUBJECT_URL)])]
        ),
        verify=_mark_verified,
        clock=_clock,
    )
    coordinator = Coordinator([sample_pack, seo], runner, max_concurrent=2, clock=_clock)
    events = [e async for e in coordinator.run(RUN_ID, REQUEST)]

    started = events[0]
    assert isinstance(started, StartedEvent)
    assert started.domains == ("pricing", "positioning_seo")
    assert (started.subject, started.rival, started.category) == (
        "Acme Widgets",
        "Zeta Gadgets",
        "widgets",
    )
    done = events[-1]
    assert isinstance(done, DoneEvent)
    assert (done.verified_count, done.total_count) == (2, 2)
    assert len([e for e in events if isinstance(e, ClaimEvent)]) == 2
    assert len([e for e in events if isinstance(e, VerifiedEvent)]) == 2
    assert not any(isinstance(e, ErrorEvent) for e in events)
    for event in events:
        dumped = RUN_EVENT_ADAPTER.dump_python(event, mode="json")
        assert RUN_EVENT_ADAPTER.validate_python(dumped) == event


class _CountingSpecialist:
    """A slow fake specialist that records how many `run` calls are in flight at once."""

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0
        self.calls = 0

    async def run(
        self, run_id: RunId, request: RunRequest, pack: DomainPack
    ) -> AsyncIterator[RunEvent]:
        del request
        self.calls += 1
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.02)
        self.active -= 1
        yield ErrorEvent(run_id=run_id, ts=NOW, domain=pack.id, message="counted")


async def test_semaphore_caps_concurrency_at_max_concurrent(sample_pack: DomainPack) -> None:
    packs = [
        sample_pack.model_copy(update={"id": domain})
        for domain in ("pricing", "positioning_seo", "news_social", "product")
    ]
    specialist = _CountingSpecialist()
    coordinator = Coordinator(packs, specialist, max_concurrent=2, clock=_clock)
    events = [e async for e in coordinator.run(RUN_ID, REQUEST)]
    assert specialist.peak == 2
    assert specialist.calls == 4
    assert isinstance(events[-1], DoneEvent)


class _ExplodingSpecialist:
    """Fails for `pricing`, emits one verified claim for any other pack."""

    async def run(
        self, run_id: RunId, request: RunRequest, pack: DomainPack
    ) -> AsyncIterator[RunEvent]:
        del request
        if pack.id == "pricing":
            raise RuntimeError("pricing specialist blew up")
        yield ClaimEvent(run_id=run_id, ts=NOW, domain=pack.id, claim=SEO_CLAIM)
        yield VerifiedEvent(run_id=run_id, ts=NOW, domain=pack.id, claim=SEO_CLAIM)


async def test_specialist_failure_is_an_error_event_and_others_finish(
    sample_pack: DomainPack,
) -> None:
    seo = sample_pack.model_copy(update={"id": "positioning_seo"})
    coordinator = Coordinator(
        [sample_pack, seo], _ExplodingSpecialist(), max_concurrent=2, clock=_clock
    )
    events = [e async for e in coordinator.run(RUN_ID, REQUEST)]
    errors = [e for e in events if isinstance(e, ErrorEvent)]
    assert len(errors) == 1 and errors[0].domain == "pricing"
    assert "blew up" in errors[0].message
    done = events[-1]
    assert isinstance(done, DoneEvent) and (done.verified_count, done.total_count) == (1, 1)
