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
- every failure is logged at WARNING (the exception type, or the tool's error text with the key
  redacted), so a revoked key or a rate limit is visible and not mistaken for "no results".
- a blank or whitespace key is refused: `langchain_keenable` strips it to None and would quietly
  use the keyless public endpoint, which the spec forbids.

Timestamps come from an injected clock defaulting to `datetime.now(UTC)`.

The real model factory is L1's `default_model_factory` (already lazy); it is re-exported here as
`live_model_factory` rather than duplicated.

The claim repairer (GitHub issue #39, ADR-0007) is Mellea over its LiteLLM backend, model
`anthropic/<pack.model>`, so repairs go to Anthropic with the specialist's own model.
`litellm_backend` is called only when a claim needs repairing. Before LiteLLM is first imported it
sets `LITELLM_LOCAL_MODEL_COST_MAP=True` (unless the environment already sets it): otherwise
`import litellm` downloads its model price list from GitHub, a request this app has no reason to
make. LiteLLM reads `ANTHROPIC_API_KEY` from the environment when it sends a request, as
`ChatAnthropic` does in `default_model_factory`; nothing here reads it. Mellea's own logger is set
to WARNING, so its INFO lines and progress bars stay out of the server log.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, SecretStr, TypeAdapter, ValidationError

from receipts.contracts import DomainPack, FetchedPage, SearchResult
from receipts.harness.repair import ClaimRepairer, MelleaClaimRepairer
from receipts.harness.specialist import Clock, default_model_factory, utc_now
from receipts.settings import MissingSettingError

if TYPE_CHECKING:
    from mellea.backends.litellm import LiteLLMBackend

__all__ = [
    "KeenableFetchClient",
    "KeenableSearchClient",
    "litellm_backend",
    "live_model_factory",
    "live_repair_factory",
]

live_model_factory = default_model_factory


def litellm_backend(model: str) -> LiteLLMBackend:
    """Mellea's `LiteLLMBackend` for `anthropic/<model>`; LiteLLM is imported here, not earlier."""
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    from mellea.backends.litellm import LiteLLMBackend
    from mellea.core import MelleaLogger

    MelleaLogger.get_logger().setLevel(logging.WARNING)
    return LiteLLMBackend(model_id=f"anthropic/{model}")


def live_repair_factory(pack: DomainPack) -> ClaimRepairer:
    """The live `RepairFactory`: Mellea, the pack's own model, at most `MAX_REPAIRS` per claim."""
    return MelleaClaimRepairer(lambda: litellm_backend(pack.model))


logger = logging.getLogger(__name__)

_ERROR_TEXT_CHARS = 200


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


def _secret_key(api_key: str) -> SecretStr:
    if not api_key.strip():
        raise MissingSettingError("KEENABLE_API_KEY")
    return SecretStr(api_key)


def _describe(raw: object, key: SecretStr) -> str:
    """What came back instead of a usable body: the tool's error text (key redacted, cut short)
    or just the type name, so the log names the failure without echoing page content."""
    if isinstance(raw, str):
        return repr(raw.replace(key.get_secret_value(), "***")[:_ERROR_TEXT_CHARS])
    return type(raw).__name__


class KeenableSearchClient:
    """`SearchClient` over `langchain_keenable.KeenableSearch`."""

    def __init__(self, api_key: str, *, clock: Clock = utc_now, timeout_s: int = 30) -> None:
        self._api_key = _secret_key(api_key)
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
            raw = self._invoke(query)
        except Exception as exc:
            logger.warning("keenable search raised %s", type(exc).__name__)
            return []
        try:
            items = _SEARCH_ITEMS.validate_python(raw)
        except ValidationError:
            logger.warning(
                "keenable search returned %s, not a result list", _describe(raw, self._api_key)
            )
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
        self._api_key = _secret_key(api_key)
        self._clock = clock
        self._timeout_s = timeout_s

    def _invoke(self, url: str) -> object:
        from langchain_keenable import KeenableFetch

        tool = KeenableFetch(api_key=self._api_key, timeout=self._timeout_s)
        result: object = tool.invoke({"url": url})
        return result

    def fetch(self, url: str) -> FetchedPage:
        fetched_at = self._clock()
        failed = FetchedPage(url=url, text="", fetched_at=fetched_at, ok=False)
        try:
            raw = self._invoke(url)
        except Exception as exc:
            logger.warning("keenable fetch raised %s", type(exc).__name__)
            return failed
        try:
            body = _FETCH_BODY.validate_python(raw)
        except ValidationError:
            logger.warning(
                "keenable fetch returned %s, not a page body", _describe(raw, self._api_key)
            )
            return failed
        return FetchedPage(url=url, text=body.content, fetched_at=fetched_at, ok=True)
