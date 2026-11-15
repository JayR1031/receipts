"""L1: `make_tools` and `SpecialistRunner` under `fake_llm` + `FakeKeenable`; no network."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage

from receipts.contracts import (
    Claim,
    ClaimEvent,
    DomainPack,
    DroppedEvent,
    ErrorEvent,
    FetchedPage,
    FetchEvent,
    RunId,
    RunRequest,
    SearchEvent,
    SearchResult,
    VerifiedEvent,
)
from receipts.fakes import FakeKeenable, data, fake_llm
from receipts.harness import SpecialistRunner, ToolLog, make_tools

RUN_ID = RunId("run-l1-0001")
REQUEST = RunRequest(subject="Acme Widgets", rival="Zeta Gadgets", category="widgets")
NOW = datetime(2026, 11, 14, 13, 0, tzinfo=UTC)


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


def _fetch_call(i: int, url: str) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[
            {"name": "keenable_fetch", "args": {"url": url}, "id": f"f{i}", "type": "tool_call"}
        ],
    )


def _final(claims: list[dict[str, object]]) -> str:
    return "Here are the claims.\n```json\n" + json.dumps(claims) + "\n```\n"


def _mark_verified(
    claim: Claim, pages: Mapping[str, FetchedPage], rows: Sequence[SearchResult]
) -> Claim:
    del pages, rows
    return claim.model_copy(update={"verified": True, "verify_method": "quote_exact"})


def test_make_tools_are_named_exactly_and_record_rows_and_pages(
    fake_keenable: FakeKeenable,
) -> None:
    log = ToolLog()
    tools = make_tools(fake_keenable, fake_keenable, log=log)
    assert [t.name for t in tools] == ["keenable_search", "keenable_fetch"]
    tools[0].invoke({"query": "acme widgets pricing"})
    tools[1].invoke({"url": data.SUBJECT_URL})
    assert [r.url for r in log.search_rows] == [data.SUBJECT_URL]
    assert log.pages[data.SUBJECT_URL].ok is True


async def test_search_budget_stops_at_max_searches(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    pack = sample_pack.model_copy(update={"max_searches": 2})
    script: list[str | AIMessage] = [_search_call(i, f"query {i}") for i in range(5)]
    script.append(_final([]))
    runner = SpecialistRunner(
        fake_keenable, fake_keenable, model_factory=lambda _pack: fake_llm(script), clock=_clock
    )
    events = [e async for e in runner.run(RUN_ID, REQUEST, pack)]
    assert len(fake_keenable.searches) == 2
    assert len([e for e in events if isinstance(e, SearchEvent)]) == 2


async def test_runner_emits_search_fetch_claim_and_verified_via_the_hook(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    seen_packs: list[DomainPack] = []

    def factory(pack: DomainPack) -> BaseChatModel:
        seen_packs.append(pack)
        return fake_llm(
            [
                _search_call(1, "acme widgets pricing"),
                _fetch_call(2, data.SUBJECT_URL),
                _final(
                    [
                        {
                            "about": "subject",
                            "text": "Acme starts at 9 dollars per seat.",
                            "receipt": {
                                "kind": "quote",
                                "url": data.SUBJECT_URL,
                                "quote": "Plans start at 9 dollars per seat",
                            },
                        },
                        {
                            "about": "subject",
                            "text": "Acme ranks first for its pricing query.",
                            "receipt": {
                                "kind": "search",
                                "query": "acme widgets pricing",
                                "rank": 1,
                                "url": data.SUBJECT_URL,
                            },
                        },
                    ]
                ),
            ]
        )

    runner = SpecialistRunner(
        fake_keenable, fake_keenable, model_factory=factory, verify=_mark_verified, clock=_clock
    )
    events = [e async for e in runner.run(RUN_ID, REQUEST, sample_pack)]

    assert seen_packs == [sample_pack]
    kinds = [e.kind for e in events]
    assert kinds == ["search", "fetch", "claim", "verified", "claim", "verified"]
    assert all(e.run_id == RUN_ID and e.domain == "pricing" and e.ts == NOW for e in events)
    search = events[0]
    assert isinstance(search, SearchEvent) and search.results[0].url == data.SUBJECT_URL
    fetch = events[1]
    assert isinstance(fetch, FetchEvent) and fetch.ok is True
    claim = events[2]
    assert isinstance(claim, ClaimEvent) and claim.claim.verified is False
    verified = events[3]
    assert isinstance(verified, VerifiedEvent) and verified.claim.verified is True
    search_claim = events[4]
    assert isinstance(search_claim, ClaimEvent)
    assert search_claim.claim.receipt.kind == "search"
    # the search receipt's timestamp comes from the logged search row, not the model
    assert search_claim.claim.receipt.ts == data.T0


async def test_unverified_claims_are_dropped_by_the_default_hook(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    final = _final(
        [
            {
                "about": "rival",
                "text": "Zeta offers a free tier.",
                "receipt": {"kind": "quote", "url": data.RIVAL_URL, "quote": "free forever"},
            }
        ]
    )
    runner = SpecialistRunner(
        fake_keenable, fake_keenable, model_factory=lambda _p: fake_llm([final]), clock=_clock
    )
    events = [e async for e in runner.run(RUN_ID, REQUEST, sample_pack)]
    assert [e.kind for e in events] == ["claim", "dropped"]
    dropped = events[1]
    assert isinstance(dropped, DroppedEvent) and dropped.reason


async def test_unparseable_final_message_is_an_error_event_not_a_crash(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    runner = SpecialistRunner(
        fake_keenable,
        fake_keenable,
        model_factory=lambda _p: fake_llm(["I could not find anything."]),
        clock=_clock,
    )
    events = [e async for e in runner.run(RUN_ID, REQUEST, sample_pack)]
    assert len(events) == 1
    error = events[0]
    assert isinstance(error, ErrorEvent) and error.domain == "pricing"


async def test_search_receipt_ts_comes_from_the_logged_row_not_the_model(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    final = _final(
        [
            {
                "about": "subject",
                "text": "Acme ranks first for its pricing query.",
                "receipt": {
                    "kind": "search",
                    "query": "acme widgets pricing",
                    "rank": 1,
                    "url": data.SUBJECT_URL,
                    "ts": "2001-01-01T00:00:00Z",
                },
            }
        ]
    )
    runner = SpecialistRunner(
        fake_keenable,
        fake_keenable,
        model_factory=lambda _p: fake_llm([_search_call(1, "acme widgets pricing"), final]),
        verify=_mark_verified,
        clock=_clock,
    )
    events = [e async for e in runner.run(RUN_ID, REQUEST, sample_pack)]
    claims = [e for e in events if isinstance(e, ClaimEvent)]
    assert len(claims) == 1
    receipt = claims[0].claim.receipt
    assert receipt.kind == "search" and receipt.ts == data.T0


async def test_fetch_budget_stops_at_max_fetches(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    pack = sample_pack.model_copy(update={"max_fetches": 2})
    script: list[str | AIMessage] = [_fetch_call(i, data.SUBJECT_URL) for i in range(5)]
    script.append(_final([]))
    runner = SpecialistRunner(
        fake_keenable, fake_keenable, model_factory=lambda _pack: fake_llm(script), clock=_clock
    )
    events = [e async for e in runner.run(RUN_ID, REQUEST, pack)]
    assert len(fake_keenable.fetches) == 2
    assert len([e for e in events if isinstance(e, FetchEvent)]) == 2


async def test_tool_events_replay_in_call_order(
    fake_keenable: FakeKeenable, sample_pack: DomainPack
) -> None:
    script: list[str | AIMessage] = [
        _search_call(1, "acme widgets pricing"),
        _fetch_call(2, data.SUBJECT_URL),
        _search_call(3, "zeta gadgets pricing"),
        _final([]),
    ]
    runner = SpecialistRunner(
        fake_keenable, fake_keenable, model_factory=lambda _p: fake_llm(script), clock=_clock
    )
    events = [e async for e in runner.run(RUN_ID, REQUEST, sample_pack)]
    assert [e.kind for e in events] == ["search", "fetch", "search"]
