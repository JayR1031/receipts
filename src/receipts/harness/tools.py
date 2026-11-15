"""LangChain tools `keenable_search` and `keenable_fetch` over the `SearchClient`/`FetchClient`
protocols. The names are exact because `ToolCallLimitMiddleware` budgets bind to them.

Every result is recorded in a `ToolLog` for the run: the Verifier may only accept a claim that
cites a page fetched in this run or a search row logged in this run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from langchain_core.tools import BaseTool, StructuredTool

from receipts.contracts import FetchClient, FetchedPage, SearchClient, SearchResult

PAGE_TEXT_LIMIT = 6000
"""Agents see a truncated copy of a page; the Verifier reads the full text from the log."""


@dataclass(frozen=True)
class SearchCall:
    query: str
    rows: tuple[SearchResult, ...]


@dataclass(frozen=True)
class FetchCall:
    page: FetchedPage


@dataclass
class ToolLog:
    """What the tools returned during one specialist's run.

    `calls` holds every search and fetch in the order the agent made them, and the runner
    replays events from it. `searches` and `fetches` are per-kind views kept in step with it.
    """

    calls: list[SearchCall | FetchCall] = field(default_factory=list[SearchCall | FetchCall])
    searches: list[tuple[str, tuple[SearchResult, ...]]] = field(
        default_factory=list[tuple[str, tuple[SearchResult, ...]]]
    )
    fetches: list[FetchedPage] = field(default_factory=list[FetchedPage])

    @property
    def search_rows(self) -> list[SearchResult]:
        return [row for _query, rows in self.searches for row in rows]

    @property
    def pages(self) -> dict[str, FetchedPage]:
        """Pages by URL; a later fetch of the same URL wins."""
        return {page.url: page for page in self.fetches}


def _render_results(rows: tuple[SearchResult, ...]) -> str:
    if not rows:
        return "No results."
    return "\n".join(
        json.dumps({"rank": r.rank, "url": r.url, "title": r.title, "snippet": r.snippet})
        for r in rows
    )


def _render_page(page: FetchedPage) -> str:
    if not page.ok:
        return f"Fetch failed for {page.url}; do not cite this page."
    return page.text[:PAGE_TEXT_LIMIT]


def make_tools(search: SearchClient, fetch: FetchClient, *, log: ToolLog) -> list[BaseTool]:
    """Two tools, `keenable_search` then `keenable_fetch`, that record into `log`."""

    def keenable_search(query: str) -> str:
        rows = tuple(search.search(query))
        log.searches.append((query, rows))
        log.calls.append(SearchCall(query, rows))
        return _render_results(rows)

    def keenable_fetch(url: str) -> str:
        page = fetch.fetch(url)
        log.fetches.append(page)
        log.calls.append(FetchCall(page))
        return _render_page(page)

    return [
        StructuredTool.from_function(
            func=keenable_search,
            name="keenable_search",
            description="Web search. Returns one JSON line per result: rank, url, title, snippet.",
        ),
        StructuredTool.from_function(
            func=keenable_fetch,
            name="keenable_fetch",
            description="Fetch a page by URL and return its text. Quote only from fetched pages.",
        ),
    ]
