"""Real `SearchClient` and `FetchClient` over `langchain-keenable` (W2).

Both take the API key explicitly: the caller passes
`require_keenable_key(settings).get_secret_value()`, so nothing here reads the environment and
nothing is built at import. The Keenable tools are constructed lazily, on first call.

Shape mapping (spec: a failed fetch is not a false claim):
- search: each result dict becomes a `SearchResult` ranked from 1 in the order Keenable returned
  it; a non-list body, a tool error string (the tool has `handle_tool_error=True`) or an
  exception yields `[]`.
- fetch: `{url, title, content, ...}` becomes `FetchedPage(ok=True)` with `content` as the text;
  anything else (error string, missing or non-text `content`, exception) is `FetchedPage(ok=False)`
  with empty text.

Timestamps come from an injected clock defaulting to `datetime.now(UTC)`.

The real model factory is L1's `default_model_factory` (already lazy); it is re-exported here as
`live_model_factory` rather than duplicated.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr, TypeAdapter

from receipts.contracts import FetchedPage, SearchResult
from receipts.harness.specialist import Clock, default_model_factory, utc_now

__all__ = ["KeenableFetchClient", "KeenableSearchClient", "live_model_factory"]

live_model_factory = default_model_factory


class _SearchItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    url: str
    title: str = ""
    description: str = ""


class _FetchBody(BaseModel):
    model_config = ConfigDict(extra="ignore")
    content: str


_SEARCH_ITEMS: TypeAdapter[list[_SearchItem]] = TypeAdapter(list[_SearchItem])
_FETCH_BODY: TypeAdapter[_FetchBody] = TypeAdapter(_FetchBody)


class KeenableSearchClient:
    """`SearchClient` over `langchain_keenable.KeenableSearch`."""

    def __init__(self, api_key: str, *, clock: Clock = utc_now, timeout_s: int = 30) -> None:
        self._api_key = SecretStr(api_key)
        self._clock = clock
        self._timeout_s = timeout_s

    def _invoke(self, query: str) -> object:
        from langchain_keenable import KeenableSearch

        tool = KeenableSearch(api_key=self._api_key, timeout=self._timeout_s)
        result: object = tool.invoke({"query": query})
        return result

    def search(self, query: str) -> list[SearchResult]:
        ts = self._clock()
        try:
            items = _SEARCH_ITEMS.validate_python(self._invoke(query))
        except Exception:
            return []
        return [
            SearchResult(
                query=query,
                rank=rank,
                url=item.url,
                title=item.title,
                snippet=item.description,
                ts=ts,
            )
            for rank, item in enumerate(items, start=1)
            if item.url
        ]


class KeenableFetchClient:
    """`FetchClient` over `langchain_keenable.KeenableFetch`."""

    def __init__(self, api_key: str, *, clock: Clock = utc_now, timeout_s: int = 30) -> None:
        self._api_key = SecretStr(api_key)
        self._clock = clock
        self._timeout_s = timeout_s

    def _invoke(self, url: str) -> object:
        from langchain_keenable import KeenableFetch

        tool = KeenableFetch(api_key=self._api_key, timeout=self._timeout_s)
        result: object = tool.invoke({"url": url})
        return result

    def fetch(self, url: str) -> FetchedPage:
        fetched_at = self._clock()
        try:
            body = _FETCH_BODY.validate_python(self._invoke(url))
        except Exception:
            return FetchedPage(url=url, text="", fetched_at=fetched_at, ok=False)
        return FetchedPage(url=url, text=body.content, fetched_at=fetched_at, ok=True)
