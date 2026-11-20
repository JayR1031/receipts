"""The live progress view (lane L5): `render_progress` over event sequences. No browser."""

from __future__ import annotations

import re
from datetime import timedelta

import gradio as gr

import receipts.ui.app as ui_app
from receipts.contracts import (
    Claim,
    ClaimEvent,
    Domain,
    DoneEvent,
    DroppedEvent,
    ErrorEvent,
    FetchEvent,
    QuoteReceipt,
    RunEvent,
    RunId,
    SearchEvent,
    StartedEvent,
    VerifiedEvent,
)
from receipts.fakes import FakeRunService, data
from receipts.ui.render import (
    PROGRESS_WAITING,
    render_progress,
    render_progress_notice,
)
from receipts.ui.theme import CSS

RID = RunId("run-progress-0001")
CLAIM = Claim(
    domain="pricing",
    about="subject",
    text="Acme starts at 9 dollars per seat per month.",
    receipt=QuoteReceipt(url=data.SUBJECT_URL, quote="Plans start at 9 dollars per seat"),
)


def _at(seconds: int) -> dict:
    return {"run_id": RID, "ts": data.T0 + timedelta(seconds=seconds)}


def _started(domains: tuple[Domain, ...] = ("news_social", "pricing")) -> StartedEvent:
    return StartedEvent(**_at(0), subject="Acme Widgets", rival="Zeta Gadgets", domains=domains)


def _search(seconds: int, domain: Domain = "pricing") -> SearchEvent:
    results = tuple(data.sample_search_results())
    return SearchEvent(**_at(seconds), domain=domain, query="acme widgets pricing", results=results)


def _lane(html: str, title: str) -> str:
    """The markup of the one lane titled `title`, from its class attribute on."""
    lanes = html.split('<li class="rp-lane ')[1:]
    found = [lane for lane in lanes if f'<h3 class="rp-lane-title">{title}</h3>' in lane]
    assert len(found) == 1, f"{len(found)} lanes titled {title!r}"
    return 'class="rp-lane ' + found[0]


def _counts(lane: str) -> dict[str, int]:
    return {
        label: int(num)
        for num, label in re.findall(r'class="rp-count-num[^"]*">(\d+)</span> ([a-z ]+)</li>', lane)
    }


def test_no_events_yet_is_a_waiting_notice() -> None:
    assert render_progress([]) == render_progress_notice(PROGRESS_WAITING)


def test_start_shows_one_queued_lane_per_domain_in_the_battlecard_order() -> None:
    html = render_progress([_started()])
    titles = re.findall(r'<h3 class="rp-lane-title">([^<]+)</h3>', html)
    assert titles == ["Pricing", "News &amp; social"], "lanes not in DOMAIN_TITLES order"
    assert html.count('class="rp-lane rp-lane-queued"') == 2
    assert html.count('class="rp-step rp-step-todo"') == 8
    assert 'Acme Widgets <span class="rp-vs">vs</span> Zeta Gadgets' in html
    assert 'aria-valuenow="0"' in html and 'aria-valuemax="8"' in html
    assert "0 of 8 steps reached" in html and "0s elapsed" in html


def test_mid_run_marks_the_current_step_and_counts_pages() -> None:
    events: list[RunEvent] = [
        _started(),
        _search(2),
        FetchEvent(**_at(5), domain="pricing", url=data.SUBJECT_URL, ok=True),
        FetchEvent(**_at(9), domain="pricing", url=data.RIVAL_URL, ok=False),
    ]
    html = render_progress(events)
    pricing = _lane(html, "Pricing")
    assert 'class="rp-lane rp-lane-active"' in pricing
    assert '<span class="rp-lane-status">Reading pages</span>' in pricing
    assert '<li class="rp-step rp-step-done">Search</li>' in pricing
    assert '<li class="rp-step rp-step-current" aria-current="step">Read</li>' in pricing
    assert _counts(pricing) == {
        "searches": 1,
        "pages read": 1,
        "drafted": 0,
        "verified": 0,
        "dropped": 0,
    }
    assert "Could not read zeta-gadgets.example/plans" in pricing  # the latest activity
    assert 'class="rp-lane rp-lane-queued"' in _lane(html, "News &amp; social")
    # 2 of 8 steps (pricing reached Read), the elapsed time runs from the first to the latest event
    assert "2 of 8 steps reached" in html and 'style="width: 25.0%"' in html
    assert "9s elapsed" in html and "1 page read" in html


def test_a_dropped_claim_counts_in_red_and_names_its_reason() -> None:
    events: list[RunEvent] = [
        _started(("pricing",)),
        _search(1),
        ClaimEvent(**_at(2), domain="pricing", claim=CLAIM),
        VerifiedEvent(**_at(3), domain="pricing", claim=CLAIM),
        ClaimEvent(**_at(4), domain="pricing", claim=CLAIM),
        DroppedEvent(**_at(65), domain="pricing", claim=CLAIM, reason="quote not on the page"),
    ]
    pricing = _lane(render_progress(events), "Pricing")
    assert '<span class="rp-lane-status">Verifying</span>' in pricing
    assert _counts(pricing) == {
        "searches": 1,
        "pages read": 0,
        "drafted": 2,
        "verified": 1,
        "dropped": 1,
    }
    assert 'class="rp-count-num status-dropped">1</span> dropped' in pricing
    assert 'class="rp-count-num status-verified">1</span> verified' in pricing
    assert "Dropped (quote not on the page): Acme starts at 9 dollars" in pricing
    assert "1m 05s elapsed" in render_progress(events)


def test_zero_counts_carry_no_status_colour() -> None:
    html = render_progress([_started(("pricing",))])
    assert "status-verified" not in html and "status-dropped" not in html


def test_a_domain_error_stops_only_that_lane() -> None:
    events: list[RunEvent] = [
        _started(),
        _search(1),
        _search(2, domain="news_social"),
        ErrorEvent(**_at(3), domain="news_social", message="news_social specialist failed"),
    ]
    html = render_progress(events)
    news = _lane(html, "News &amp; social")
    assert 'class="rp-lane rp-lane-error"' in news
    assert '<span class="rp-lane-status status-dropped">Stopped</span>' in news
    assert "Error: news_social specialist failed" in news
    assert 'class="rp-lane rp-lane-active"' in _lane(html, "Pricing")
    assert "Run error" not in html


def test_a_run_error_shows_a_banner_and_survives_the_collapse() -> None:
    events: list[RunEvent] = [
        _started(),
        ErrorEvent(**_at(4), message="run failed: TimeoutError: harness"),
    ]
    banner = '<span class="status-dropped">Run error:</span> run failed: TimeoutError: harness'
    assert banner in render_progress(events)
    done = [*events, DoneEvent(**_at(5), verified_count=0, total_count=0)]
    assert banner in render_progress(done)


def test_done_collapses_to_one_summary_line() -> None:
    events: list[RunEvent] = [
        _started(("pricing",)),
        _search(1),
        FetchEvent(**_at(2), domain="pricing", url=data.SUBJECT_URL, ok=True),
        ClaimEvent(**_at(3), domain="pricing", claim=CLAIM),
        VerifiedEvent(**_at(4), domain="pricing", claim=CLAIM),
        DoneEvent(**_at(72), verified_count=2, total_count=3),
    ]
    html = render_progress(events)
    assert html.startswith('<div class="rp rp-done">')
    assert "rp-lane" not in html, "the lanes did not collapse"
    assert "Run finished" in html and "took 1m 12s" in html
    assert "2 of 3 claims verified · 1 page read from 1 search across 1 domain" in html
    assert 'style="width: 100.0%"' in html and 'aria-valuenow="1"' in html


def test_web_and_visitor_text_is_escaped() -> None:
    hostile = "<script>alert(1)</script>"
    claim = CLAIM.model_copy(update={"text": hostile})
    events: list[RunEvent] = [
        StartedEvent(**_at(0), subject=hostile, rival='"><img src=x>', domains=("pricing",)),
        DroppedEvent(**_at(1), domain="pricing", claim=claim, reason=hostile),
        ErrorEvent(**_at(2), message=hostile),
    ]
    html = render_progress(events) + render_progress_notice(hostile)
    assert "<script>" not in html and "<img" not in html
    assert "&lt;script&gt;" in html


def test_every_progress_class_is_styled() -> None:
    html = render_progress([_started(), _search(1)]) + render_progress_notice("x")
    html += render_progress([_started(), DoneEvent(**_at(1), verified_count=0, total_count=0)])
    classes = {c for attr in re.findall(r'class="([^"]+)"', html) for c in attr.split()}
    unstyled = sorted(c for c in classes if c.startswith("rp-") and f".{c}" not in CSS)
    assert unstyled == ["rp-lane-active", "rp-step-todo"], "only the base-rule states go unstyled"


def test_the_run_panel_streams_into_the_progress_view(fake_run_service: FakeRunService) -> None:
    blocks = ui_app.build_ui(fake_run_service)
    views = [
        b
        for b in blocks.blocks.values()
        if isinstance(b, gr.HTML) and b.elem_id == ui_app.PROGRESS_VIEW_ID
    ]
    assert len(views) == 1
    deps = blocks.get_config_file().get("dependencies", [])
    start = next(dep for dep in deps if dep["api_name"] == "on_start")
    assert start["outputs"][2] == views[0]._id
    assert f"#{ui_app.PROGRESS_VIEW_ID}" in CSS
