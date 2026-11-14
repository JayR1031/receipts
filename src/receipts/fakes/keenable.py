"""A canned `SearchClient` and `FetchClient`. Stands in for `langchain-keenable` in unit tests."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

from receipts.contracts import FetchedPage, SearchResult

FIXTURE_TIME = datetime(2026, 11, 14, 12, 0, tzinfo=UTC)


class FakeKeenable:
    """Search matches a fixture's `query` exactly (case-insensitive); fetch is by URL.

    An unknown URL returns `FetchedPage(ok=False)` with empty text, the same shape the
    real client produces when a page cannot be fetched.
    """

    def __init__(
        self,
        results: Sequence[SearchResult] = (),
        pages: Mapping[str, FetchedPage] | None = None,
        fetched_at: datetime = FIXTURE_TIME,
    ) -> None:
        self.results: tuple[SearchResult, ...] = tuple(results)
        self.pages: dict[str, FetchedPage] = dict(pages or {})
        self.fetched_at = fetched_at
        self.searches: list[str] = []
        self.fetches: list[str] = []

    def search(self, query: str) -> list[SearchResult]:
        self.searches.append(query)
        wanted = query.casefold()
        return [r for r in self.results if r.query.casefold() == wanted]

    def fetch(self, url: str) -> FetchedPage:
        self.fetches.append(url)
        page = self.pages.get(url)
        if page is not None:
            return page
        return FetchedPage(url=url, text="", fetched_at=self.fetched_at, ok=False)
