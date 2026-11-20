"""Pure rendering helpers for the Gradio UI (lane L5). No browser, no network."""

from __future__ import annotations

from datetime import UTC, datetime
from html import escape

from receipts.contracts import Battlecard, Claim, QuoteReceipt, RunEvent, RunId, RunSummary
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
    "verified": "quote_exact",
    "dropped": "dropped (quote not found on fetched page)",
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
        assert "<span" not in line, f"event line leaked HTML span: {line!r}"
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


def test_render_battlecard_scores_groups_and_shows_every_receipt(
    sample_claims: list[Claim],
) -> None:
    html = render_battlecard(_card(sample_claims))
    assert 'aria-label="2 of 3 claims verified"' in html
    assert 'style="width: 66.7%"' in html
    assert "run-sample-0001" in html
    assert "Acme Widgets" in html and "Zeta Gadgets" in html
    assert html.count('<article class="bc-claim') == len(sample_claims)
    for claim in sample_claims:
        assert escape(claim.text) in html
        assert f'href="{escape(claim.receipt.url, quote=True)}"' in html
    # quote receipts show the quote; search receipts show query and rank
    assert "Plans start at 9 dollars per seat" in html
    assert "zeta gadgets pricing" in html and "result #1" in html
    assert html.count('class="bc-mark status-verified"') == 2
    assert html.count('class="bc-mark status-dropped"') == 1
    assert "Pricing" in html and "2 of 3 verified" in html  # grouped by domain


def test_dropped_claims_fold_under_the_verified_ones_and_say_why(
    sample_claims: list[Claim],
) -> None:
    dropped = next(c for c in sample_claims if not c.verified)
    noted = dropped.model_copy(update={"verify_note": "quote not on the page"})
    claims = [c for c in sample_claims if c.verified] + [noted]
    html = render_battlecard(_card(claims))
    folded = html.split('<details class="bc-dropped">', 1)[1]
    assert "1 dropped claim, and why" in folded
    assert escape(dropped.text) in folded
    assert "quote not on the page" in folded
    assert all(escape(c.text) not in folded for c in claims if c.verified)


def test_render_battlecard_escapes_web_text_and_links_only_http(
    sample_claims: list[Claim],
) -> None:
    claim = next(c for c in sample_claims if isinstance(c.receipt, QuoteReceipt))
    hostile = claim.model_copy(
        update={
            "text": "<script>alert(1)</script>",
            "receipt": claim.receipt.model_copy(
                update={"quote": '"><img src=x onerror=alert(1)>', "url": "javascript:alert(1)"}
            ),
        }
    )
    html = render_battlecard(_card([hostile]))
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html
    assert "href=" not in html and "javascript:" not in html


def test_render_battlecard_with_no_claims_still_shows_the_count() -> None:
    html = render_battlecard(_card([]))
    assert 'aria-label="2 of 3 claims verified"' in html
    assert "no claims" in html.lower()


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
