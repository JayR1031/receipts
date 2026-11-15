"""Pure rendering helpers for the Gradio UI (lane L5). No browser, no network."""

from __future__ import annotations

from datetime import UTC, datetime

from receipts.contracts import Battlecard, Claim, RunEvent, RunId, RunSummary
from receipts.ui.render import (
    HISTORY_HEADERS,
    render_battlecard,
    render_event_line,
    render_history,
)

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)

# One distinct substring per event kind, so a kind that falls through to a generic line fails.
KIND_MARKERS: dict[str, str] = {
    "started": "Acme Widgets vs Zeta Gadgets",
    "search": "acme widgets pricing",
    "fetch": "https://acme-widgets.example/pricing",
    "claim": "Acme starts at 9 dollars",
    "verified": '<span class="status-verified">[verified]</span> quote_exact',
    "dropped": (
        '<span class="status-dropped">[dropped]</span> dropped (quote not found on fetched page)'
    ),
    "error": "search timed out",
    "done": "2 of 3 verified",
}


def test_render_event_line_is_kind_specific_for_every_kind(sample_events: list[RunEvent]) -> None:
    kinds = {event.kind for event in sample_events}
    assert kinds == set(KIND_MARKERS), "fixture no longer covers every kind"
    for event in sample_events:
        line = render_event_line(event)
        assert line.strip(), f"empty line for {event.kind}"
        assert "\n" not in line.strip(), f"{event.kind} rendered more than one line"
        assert event.kind in line, f"{event.kind!r} not named in {line!r}"
        assert KIND_MARKERS[event.kind] in line, f"{event.kind}: {line!r}"


def _card(claims: list[Claim]) -> Battlecard:
    return Battlecard(
        run_id=RunId("run-sample-0001"),
        subject="Acme Widgets",
        rival="Zeta Gadgets",
        claims=tuple(claims),
        verified_count=2,
        total_count=3,
        started_at=T0,
        finished_at=T0,
    )


def test_render_battlecard_counts_rows_and_receipts(sample_claims: list[Claim]) -> None:
    md = render_battlecard(_card(sample_claims))
    assert "**2 of 3 verified**" in md
    assert "Acme Widgets" in md and "Zeta Gadgets" in md
    rows = [line for line in md.splitlines() if line.startswith("- ")]
    assert len(rows) == len(sample_claims)
    for claim in sample_claims:
        assert claim.text in md
        assert claim.receipt.url in md
    # quote receipts show the quote; search receipts show query and rank
    assert "Plans start at 9 dollars per seat" in md
    assert "zeta gadgets pricing" in md and "#1" in md
    # one verified marker per verified claim, one unverified marker for the rest
    assert md.count('<span class="status-verified">[verified]</span>') == 2
    assert md.count("[unverified]") == 1
    assert "## pricing" in md  # grouped by domain


def test_render_battlecard_with_no_claims_still_shows_the_count() -> None:
    md = render_battlecard(_card([]))
    assert "**2 of 3 verified**" in md
    assert "no claims" in md.lower()


def test_render_history_one_row_per_summary_newest_first_as_given() -> None:
    rows = [
        RunSummary(
            run_id=RunId("run-2"),
            subject="B",
            rival="C",
            status="running",
            verified_count=0,
            total_count=0,
            started_at=T0,
        ),
        RunSummary(
            run_id=RunId("run-1"),
            subject="Acme Widgets",
            rival="Zeta Gadgets",
            status="done",
            verified_count=2,
            total_count=3,
            started_at=T0,
        ),
    ]
    table = render_history(rows)
    assert len(table) == 2
    assert all(len(row) == len(HISTORY_HEADERS) for row in table)
    assert table[0][0] == "B vs C"
    assert table[1] == ["Acme Widgets vs Zeta Gadgets", "done", "2 of 3", "2026-11-14 12:00 UTC"]
    assert render_history([]) == []
