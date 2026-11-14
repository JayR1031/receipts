"""Canned search results and pages for `FakeKeenable`, importable outside pytest too.

All text here is invented: no real companies, people, usernames or keys.
"""

from __future__ import annotations

from datetime import UTC, datetime

from receipts.contracts import FetchedPage, SearchResult

T0 = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)
SUBJECT_URL = "https://acme-widgets.example/pricing"
RIVAL_URL = "https://zeta-gadgets.example/plans"
SUBJECT_PAGE = "Acme Widgets. Plans start at 9 dollars per seat per month. Cancel any time."
RIVAL_PAGE = "Zeta Gadgets. The Team plan is 14 dollars per seat per month, billed yearly."


def sample_search_results() -> list[SearchResult]:
    """One hit each for the subject's and the rival's pricing query."""
    return [
        SearchResult(
            query="acme widgets pricing",
            rank=1,
            url=SUBJECT_URL,
            title="Acme Widgets pricing",
            snippet="Plans start at 9 dollars per seat.",
            ts=T0,
        ),
        SearchResult(
            query="zeta gadgets pricing",
            rank=1,
            url=RIVAL_URL,
            title="Zeta Gadgets plans",
            snippet="Team plan is 14 dollars per seat.",
            ts=T0,
        ),
    ]


def sample_pages() -> dict[str, FetchedPage]:
    """The two pages the sample search results point at, keyed by URL."""
    return {
        SUBJECT_URL: FetchedPage(url=SUBJECT_URL, text=SUBJECT_PAGE, fetched_at=T0, ok=True),
        RIVAL_URL: FetchedPage(url=RIVAL_URL, text=RIVAL_PAGE, fetched_at=T0, ok=True),
    }
