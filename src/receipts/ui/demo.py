# pyright: basic
"""Demo mode: the scripted run the UI replays when no `RunService` is wired in.

Mirrors `tests/conftest.py`'s `sample_events` (one event of every kind) so the UI works in a
bare process; all names are invented (see `receipts.fakes.data`). W2 replaces this by setting
`app.state.run_service` before `mount_ui` runs.
"""

from __future__ import annotations

from datetime import timedelta

from receipts.contracts import (
    Claim,
    ClaimEvent,
    DoneEvent,
    DroppedEvent,
    ErrorEvent,
    FetchEvent,
    QuoteReceipt,
    RunEvent,
    RunId,
    SearchEvent,
    SearchReceipt,
    StartedEvent,
    VerifiedEvent,
)
from receipts.fakes import FakeRunService, data

DEMO_RUN_ID = RunId("run-demo-0001")
DEMO_DELAY_S = 0.4


def demo_claims() -> list[Claim]:
    return [
        Claim(
            domain="pricing",
            about="subject",
            text="Acme starts at 9 dollars per seat per month.",
            receipt=QuoteReceipt(url=data.SUBJECT_URL, quote="Plans start at 9 dollars per seat"),
            verified=True,
            verify_method="quote_exact",
        ),
        Claim(
            domain="pricing",
            about="rival",
            text="Zeta's Team plan is 14 dollars per seat, billed yearly.",
            receipt=SearchReceipt(
                query="zeta gadgets pricing", rank=1, url=data.RIVAL_URL, ts=data.T0
            ),
            verified=True,
            verify_method="search_log",
        ),
        Claim(
            domain="pricing",
            about="rival",
            text="Zeta offers a free tier.",
            receipt=QuoteReceipt(url=data.RIVAL_URL, quote="free forever"),
        ),
    ]


def demo_events() -> list[RunEvent]:
    """One event of every kind, in the order a run emits them."""
    claims = demo_claims()
    results = data.sample_search_results()
    t = (data.T0 + timedelta(seconds=i) for i in range(8))
    rid = DEMO_RUN_ID
    return [
        StartedEvent(
            run_id=rid,
            ts=next(t),
            subject="Acme Widgets",
            rival="Zeta Gadgets",
            category="widgets",
            domains=("pricing",),
        ),
        SearchEvent(
            run_id=rid, ts=next(t), domain="pricing", query=results[0].query, results=(results[0],)
        ),
        FetchEvent(run_id=rid, ts=next(t), domain="pricing", url=data.SUBJECT_URL, ok=True),
        ClaimEvent(run_id=rid, ts=next(t), domain="pricing", claim=claims[0]),
        VerifiedEvent(run_id=rid, ts=next(t), domain="pricing", claim=claims[0]),
        DroppedEvent(
            run_id=rid,
            ts=next(t),
            domain="pricing",
            claim=claims[2],
            reason="quote not found on fetched page",
        ),
        ErrorEvent(run_id=rid, ts=next(t), domain="pricing", message="search timed out"),
        DoneEvent(run_id=rid, ts=next(t), verified_count=2, total_count=3),
    ]


def demo_service() -> FakeRunService:
    """A `FakeRunService` that replays the demo script with a visible delay between events."""
    return FakeRunService(demo_events(), delay_s=DEMO_DELAY_S)
