"""Demo mode: the `RunService` the API falls back to when W2 has not wired a real one.

Built once, lazily, from the Wave 0 fakes' canned data (`receipts.fakes.data`): a scripted run
whose claims quote the two sample pages. All text is invented. Nothing here reads a setting.
"""

from __future__ import annotations

from datetime import timedelta

from receipts.contracts import (
    Claim,
    ClaimEvent,
    DoneEvent,
    DroppedEvent,
    FetchEvent,
    QuoteReceipt,
    RunEvent,
    RunId,
    SearchEvent,
    StartedEvent,
    VerifiedEvent,
)
from receipts.fakes import FakeRunService, data

DEMO_RUN_ID = RunId("run-demo-0001")

_demo_service: FakeRunService | None = None


def _claims() -> tuple[Claim, Claim, Claim]:
    subject = Claim(
        domain="pricing",
        about="subject",
        text="Acme starts at 9 dollars per seat per month.",
        receipt=QuoteReceipt(url=data.SUBJECT_URL, quote="Plans start at 9 dollars per seat"),
        verified=True,
        verify_method="quote_exact",
    )
    rival = Claim(
        domain="pricing",
        about="rival",
        text="Zeta's Team plan is 14 dollars per seat, billed yearly.",
        receipt=QuoteReceipt(url=data.RIVAL_URL, quote="14 dollars per seat per month"),
        verified=True,
        verify_method="quote_exact",
    )
    dropped = Claim(
        domain="pricing",
        about="rival",
        text="Zeta offers a free tier.",
        receipt=QuoteReceipt(url=data.RIVAL_URL, quote="free forever"),
    )
    return subject, rival, dropped


def demo_events() -> list[RunEvent]:
    """One scripted pricing run: two verified claims, one dropped."""
    subject, rival, dropped = _claims()
    results = data.sample_search_results()
    ticks = (data.T0 + timedelta(seconds=i) for i in range(12))
    rid = DEMO_RUN_ID
    return [
        StartedEvent(
            run_id=rid,
            ts=next(ticks),
            subject="Acme Widgets",
            rival="Zeta Gadgets",
            category="widgets",
            domains=("pricing",),
        ),
        SearchEvent(
            run_id=rid,
            ts=next(ticks),
            domain="pricing",
            query=results[0].query,
            results=(results[0],),
        ),
        FetchEvent(run_id=rid, ts=next(ticks), domain="pricing", url=data.SUBJECT_URL, ok=True),
        ClaimEvent(run_id=rid, ts=next(ticks), domain="pricing", claim=subject),
        VerifiedEvent(run_id=rid, ts=next(ticks), domain="pricing", claim=subject),
        SearchEvent(
            run_id=rid,
            ts=next(ticks),
            domain="pricing",
            query=results[1].query,
            results=(results[1],),
        ),
        FetchEvent(run_id=rid, ts=next(ticks), domain="pricing", url=data.RIVAL_URL, ok=True),
        ClaimEvent(run_id=rid, ts=next(ticks), domain="pricing", claim=rival),
        VerifiedEvent(run_id=rid, ts=next(ticks), domain="pricing", claim=rival),
        ClaimEvent(run_id=rid, ts=next(ticks), domain="pricing", claim=dropped),
        DroppedEvent(
            run_id=rid,
            ts=next(ticks),
            domain="pricing",
            claim=dropped,
            reason="quote not found on fetched page",
        ),
        DoneEvent(run_id=rid, ts=next(ticks), verified_count=2, total_count=3),
    ]


def demo_service() -> FakeRunService:
    """The process-wide demo service, built on first request (never at import)."""
    global _demo_service
    if _demo_service is None:
        _demo_service = FakeRunService(demo_events())
    return _demo_service
