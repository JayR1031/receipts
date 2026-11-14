"""Shared pytest fixtures for Receipts. Frozen after Wave 0 (AGENTS.md section 9).

All text here is invented: no real companies, people, usernames or keys.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import timedelta

import pytest
from langchain_core.messages import AIMessage

from receipts import fakes
from receipts.contracts import (
    Claim,
    ClaimEvent,
    DomainPack,
    DoneEvent,
    DroppedEvent,
    ErrorEvent,
    FetchedPage,
    FetchEvent,
    QuoteReceipt,
    RunEvent,
    RunId,
    SearchEvent,
    SearchReceipt,
    SearchResult,
    StartedEvent,
    VerifiedEvent,
)
from receipts.fakes import data
from receipts.fakes.llm import ToolBindingFakeChatModel

T0 = data.T0
RUN_ID = RunId("run-sample-0001")
SUBJECT_URL = data.SUBJECT_URL
RIVAL_URL = data.RIVAL_URL


@pytest.fixture
def sample_pack() -> DomainPack:
    return DomainPack(
        id="pricing",
        display_name="Pricing",
        model="claude-sonnet-4-5",
        system_prompt="Compare published prices for {subject} and {rival}.",
        query_templates=("{subject} pricing", "{rival} pricing {category}"),
        rubric="Every price carries a quote from the vendor's own page.",
    )


@pytest.fixture
def sample_search_results() -> list[SearchResult]:
    return data.sample_search_results()


@pytest.fixture
def sample_pages() -> dict[str, FetchedPage]:
    return data.sample_pages()


@pytest.fixture
def sample_claims() -> list[Claim]:
    return [
        Claim(
            domain="pricing",
            about="subject",
            text="Acme starts at 9 dollars per seat per month.",
            receipt=QuoteReceipt(url=SUBJECT_URL, quote="Plans start at 9 dollars per seat"),
            verified=True,
            verify_method="quote_exact",
        ),
        Claim(
            domain="pricing",
            about="rival",
            text="Zeta's Team plan is 14 dollars per seat, billed yearly.",
            receipt=SearchReceipt(query="zeta gadgets pricing", rank=1, url=RIVAL_URL, ts=T0),
            verified=True,
            verify_method="search_log",
        ),
        Claim(
            domain="pricing",
            about="rival",
            text="Zeta offers a free tier.",
            receipt=QuoteReceipt(url=RIVAL_URL, quote="free forever"),
        ),
    ]


@pytest.fixture
def sample_events(
    sample_claims: list[Claim], sample_search_results: list[SearchResult]
) -> list[RunEvent]:
    """One event of every kind, in the order a run emits them."""
    t = (T0 + timedelta(seconds=i) for i in range(8))
    return [
        StartedEvent(
            run_id=RUN_ID,
            ts=next(t),
            subject="Acme Widgets",
            rival="Zeta Gadgets",
            category="widgets",
            domains=("pricing",),
        ),
        SearchEvent(
            run_id=RUN_ID,
            ts=next(t),
            domain="pricing",
            query="acme widgets pricing",
            results=tuple(sample_search_results[:1]),
        ),
        FetchEvent(run_id=RUN_ID, ts=next(t), domain="pricing", url=SUBJECT_URL, ok=True),
        ClaimEvent(run_id=RUN_ID, ts=next(t), domain="pricing", claim=sample_claims[0]),
        VerifiedEvent(run_id=RUN_ID, ts=next(t), domain="pricing", claim=sample_claims[0]),
        DroppedEvent(
            run_id=RUN_ID,
            ts=next(t),
            domain="pricing",
            claim=sample_claims[2],
            reason="quote not found on fetched page",
        ),
        ErrorEvent(run_id=RUN_ID, ts=next(t), domain="pricing", message="search timed out"),
        DoneEvent(run_id=RUN_ID, ts=next(t), verified_count=2, total_count=3),
    ]


# --- fakes ------------------------------------------------------------------------


@pytest.fixture
def fake_repo() -> fakes.InMemoryRunRepo:
    return fakes.InMemoryRunRepo()


@pytest.fixture
def fake_run_service(sample_events: list[RunEvent]) -> fakes.FakeRunService:
    return fakes.FakeRunService(sample_events)


@pytest.fixture
def fake_keenable(
    sample_search_results: list[SearchResult], sample_pages: dict[str, FetchedPage]
) -> fakes.FakeKeenable:
    return fakes.FakeKeenable(sample_search_results, sample_pages)


@pytest.fixture
def fake_llm() -> Callable[[Sequence[str | AIMessage]], ToolBindingFakeChatModel]:
    """A factory: `fake_llm(["first reply", "second reply"])`."""
    return fakes.fake_llm
