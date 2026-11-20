"""The public share page (lane L5): pure rendering, no browser, no network. Invented text only."""

from __future__ import annotations

from datetime import UTC, datetime

from receipts.contracts import Battlecard, Claim, RunId
from receipts.ui.render import render_battlecard, share_path
from receipts.ui.share import origin, render_missing_page, render_share_page, share_title

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


def _card(claims: list[Claim], **names: str) -> Battlecard:
    return Battlecard(
        run_id=RunId("run-sample-0001"),
        subject=names.get("subject", "Acme Widgets"),
        rival=names.get("rival", "Zeta Gadgets"),
        claims=tuple(claims),
        verified_count=2,
        total_count=3,
        started_at=T0,
        finished_at=T0,
    )


def test_the_title_states_the_score() -> None:
    assert share_title(_card([])) == "Acme Widgets vs Zeta Gadgets: 2 of 3 claims verified"


def test_the_app_card_links_to_its_share_page_and_the_share_page_does_not() -> None:
    card = _card([])
    assert share_path(card) == "/share/run-sample-0001"
    assert 'href="/share/run-sample-0001"' in render_battlecard(card, share=True)
    assert 'class="bc-share"' not in render_battlecard(card)
    assert 'class="bc-share"' not in render_share_page(card, host="app.example")


def test_previews_use_https_except_on_a_local_host() -> None:
    assert origin("app.example") == "https://app.example"
    assert origin("localhost:8000") == "http://localhost:8000"
    assert origin("127.0.0.1") == "http://127.0.0.1"


def test_names_and_host_are_escaped_in_meta_tags(sample_claims: list[Claim]) -> None:
    card = _card(sample_claims, subject='Acme"><script>alert(1)</script>', rival="Zeta & Co")
    page = render_share_page(card, host='evil.example"><script>')
    assert "<script>" not in page
    assert "Zeta &amp; Co" in page
    assert 'content="https://evil.example&quot;&gt;&lt;script&gt;/share/run-sample-0001"' in page


def test_the_missing_page_says_so_and_is_not_indexed() -> None:
    page = render_missing_page(host="app.example")
    assert "Battlecard not found" in page
    assert '<meta name="robots" content="noindex">' in page
