"""One generic specialist: `create_agent` over a `DomainPack`, with tool budgets from the pack.

The model is built by an injectable `model_factory(pack)`; the default constructs
`ChatAnthropic` lazily inside the call, never at import, so the image boots with no key.

Claim extraction (the simplest reliable approach, chosen over provider structured output so the
scripted fake model drives it too): the system prompt asks the model to end with a fenced
```json block holding a list of claim drafts, `[{"about", "text", "receipt": {...}}]`, where a
receipt is `{"kind": "quote", "url", "quote"}` or `{"kind": "search", "query", "rank", "url"}`.
The last such block in the final message is parsed with a Pydantic `TypeAdapter`; a search
receipt's `ts` is always taken from the logged search row (or the clock when no row matches).
A final message with no parseable block is an `ErrorEvent` for the domain, not a crash.

Events are yielded after the agent finishes, in tool-call order: the tools run synchronously
inside the agent loop, so recording into a `ToolLog` and replaying is simpler than threading an
event queue through LangGraph. The Coordinator interleaves domains, so the stream still moves.
"""

from __future__ import annotations

import asyncio
import importlib
import re
from collections.abc import AsyncIterator, Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import Annotated, Literal, Protocol

from langchain.agents.middleware import ToolCallLimitMiddleware
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError

from receipts.contracts import (
    About,
    Claim,
    ClaimEvent,
    DomainPack,
    DroppedEvent,
    ErrorEvent,
    FetchClient,
    FetchedPage,
    FetchEvent,
    QuoteReceipt,
    RunEvent,
    RunId,
    RunRequest,
    SearchClient,
    SearchEvent,
    SearchReceipt,
    SearchResult,
    VerifiedEvent,
)
from receipts.harness.tools import SearchCall, ToolLog, make_tools

Clock = Callable[[], datetime]
ModelFactory = Callable[[DomainPack], BaseChatModel]
Verify = Callable[[Claim, Mapping[str, FetchedPage], Sequence[SearchResult]], Claim]


def utc_now() -> datetime:
    return datetime.now(UTC)


def default_model_factory(pack: DomainPack) -> BaseChatModel:
    """`ChatAnthropic` for the pack's model and effort. Imported and built here, never at import.

    In `langchain_anthropic` the field is `model` and `model_name` is its alias; `effort` is the
    alias of `reasoning_effort`. `model_name=` is the spelling pyright accepts, and
    `populate_by_name=True` makes it equivalent to `ChatAnthropic(model=pack.model,
    effort=pack.effort)` (ADR-0006).
    """
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model_name=pack.model, effort=pack.effort, timeout=None, stop=None)


class _Agent(Protocol):
    """The one method of a compiled `create_agent` graph that the runner calls."""

    async def ainvoke(
        self, input: Mapping[str, Sequence[BaseMessage]]
    ) -> Mapping[str, Sequence[object]]: ...


def build_agent(
    model: BaseChatModel,
    tools: Sequence[BaseTool],
    *,
    system_prompt: str,
    middleware: Sequence[object],
) -> _Agent:
    """`langchain.agents.create_agent`, reached through `importlib` so pyright strict stays clean.

    `create_agent` and the `CompiledStateGraph` it returns carry `Unknown` type parameters in
    langchain 1.5's own signatures, which strict mode reports at the import and at `.ainvoke`.
    A module attribute is typed `Any` by typeshed, so the result is narrowed to `_Agent`, the
    protocol naming the single method used; no ignore comment is needed.
    """
    agents = importlib.import_module("langchain.agents")
    agent: _Agent = agents.create_agent(
        model, tools, system_prompt=system_prompt, middleware=middleware
    )
    return agent


def passthrough_verify(
    claim: Claim, pages: Mapping[str, FetchedPage], rows: Sequence[SearchResult]
) -> Claim:
    """Default hook: returns the claim unchanged. W2 wires `receipts.verify.verify_claim`."""
    del pages, rows
    return claim


# --- claim drafts: what the model writes, before the domain and timestamps are filled in -------


class _QuoteDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["quote"]
    url: str
    quote: str


class _SearchDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    kind: Literal["search"]
    query: str
    rank: int
    url: str


class _ClaimDraft(BaseModel):
    model_config = ConfigDict(extra="ignore")
    about: About
    text: str
    receipt: Annotated[_QuoteDraft | _SearchDraft, Field(discriminator="kind")]


_DRAFTS: TypeAdapter[list[_ClaimDraft]] = TypeAdapter(list[_ClaimDraft])
_JSON_BLOCK = re.compile(r"```(?:json)?\s*(\[.*?\])\s*```", re.DOTALL)

OUTPUT_INSTRUCTIONS = (
    "Use keenable_search to find pages and keenable_fetch to read them. Quote only text you have "
    "fetched. End your final message with a fenced ```json block containing a list of claims: "
    '[{"about": "subject" | "rival", "text": "...", "receipt": {"kind": "quote", "url": "...", '
    '"quote": "exact text from the fetched page"}}] or a search receipt '
    '{"kind": "search", "query": "...", "rank": 1, "url": "..."} for a ranking claim.'
)


def extract_json_block(text: str) -> str | None:
    """The last fenced JSON list in `text`, or the whole text when it is a bare list."""
    matches = _JSON_BLOCK.findall(text)
    if matches:
        return matches[-1]
    stripped = text.strip()
    return stripped if stripped.startswith("[") else None


def _search_ts(draft: _SearchDraft, rows: Sequence[SearchResult], now: datetime) -> datetime:
    """The logged row's `ts` for this receipt; never a model-supplied value.

    `_SearchDraft` has no `ts` field and `extra="ignore"`, so a `ts` the model writes is dropped
    without failing the parse. `now` is only the fallback when no logged row matches the
    receipt's query and url; the verifier then drops that claim.
    """
    for row in rows:
        if row.url == draft.url and row.query.casefold() == draft.query.casefold():
            return row.ts
    return now


def _to_claim(draft: _ClaimDraft, pack: DomainPack, log: ToolLog, now: datetime) -> Claim:
    receipt: QuoteReceipt | SearchReceipt
    if isinstance(draft.receipt, _QuoteDraft):
        receipt = QuoteReceipt(url=draft.receipt.url, quote=draft.receipt.quote)
    else:
        receipt = SearchReceipt(
            query=draft.receipt.query,
            rank=draft.receipt.rank,
            url=draft.receipt.url,
            ts=_search_ts(draft.receipt, log.search_rows, now),
        )
    return Claim(domain=pack.id, about=draft.about, text=draft.text, receipt=receipt)


def parse_claims(text: str, pack: DomainPack, log: ToolLog, now: datetime) -> list[Claim]:
    """Claims from the agent's final message; `ValueError` when there is no parseable block."""
    block = extract_json_block(text)
    if block is None:
        raise ValueError("final message has no JSON claims block")
    try:
        drafts = _DRAFTS.validate_json(block)
    except ValidationError as exc:
        raise ValueError(f"claims block failed validation: {exc}") from exc
    return [_to_claim(d, pack, log, now) for d in drafts]


# --- prompt -------------------------------------------------------------------------------


class _Fields(dict[str, str]):
    def __missing__(self, key: str) -> str:
        return ""


def _fields(request: RunRequest) -> _Fields:
    return _Fields(subject=request.subject, rival=request.rival, category=request.category or "")


def system_prompt(pack: DomainPack, request: RunRequest) -> str:
    budget = f"Budget: at most {pack.max_searches} searches and {pack.max_fetches} fetches."
    rubric = f"Rubric: {pack.rubric}" if pack.rubric else ""
    body = pack.system_prompt.format_map(_fields(request))
    return "\n\n".join(part for part in (body, budget, rubric, OUTPUT_INSTRUCTIONS) if part)


def user_prompt(pack: DomainPack, request: RunRequest) -> str:
    queries = [t.format_map(_fields(request)).strip() for t in pack.query_templates]
    lines = [f"Compare {request.subject} (subject) with {request.rival} (rival)."]
    if request.category:
        lines.append(f"Category: {request.category}.")
    if queries:
        lines.append("Suggested queries: " + "; ".join(q for q in queries if q))
    return "\n".join(lines)


def final_text(messages: Sequence[object]) -> str:
    """Text of the last `AIMessage`; empty when the agent produced none."""
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            return message.text
    return ""


# --- the runner -----------------------------------------------------------------------------


class SpecialistRunner:
    """Runs one `DomainPack` against the search and fetch clients and yields `RunEvent`s."""

    def __init__(
        self,
        search: SearchClient,
        fetch: FetchClient,
        *,
        model_factory: ModelFactory = default_model_factory,
        verify: Verify = passthrough_verify,
        clock: Clock = utc_now,
    ) -> None:
        self._search = search
        self._fetch = fetch
        self._model_factory = model_factory
        self._verify = verify
        self._clock = clock

    async def _invoke(self, pack: DomainPack, request: RunRequest, log: ToolLog) -> str:
        tools = make_tools(self._search, self._fetch, log=log)
        agent = build_agent(
            self._model_factory(pack),
            tools,
            system_prompt=system_prompt(pack, request),
            middleware=[
                ToolCallLimitMiddleware(tool_name="keenable_search", run_limit=pack.max_searches),
                ToolCallLimitMiddleware(tool_name="keenable_fetch", run_limit=pack.max_fetches),
            ],
        )
        result = await asyncio.wait_for(
            agent.ainvoke({"messages": [HumanMessage(user_prompt(pack, request))]}),
            timeout=pack.timeout_s,
        )
        return final_text(result["messages"])

    def _tool_events(self, run_id: RunId, pack: DomainPack, log: ToolLog) -> list[RunEvent]:
        events: list[RunEvent] = []
        for call in log.calls:
            if isinstance(call, SearchCall):
                events.append(
                    SearchEvent(
                        run_id=run_id,
                        ts=self._clock(),
                        domain=pack.id,
                        query=call.query,
                        results=call.rows,
                    )
                )
            else:
                events.append(
                    FetchEvent(
                        run_id=run_id,
                        ts=self._clock(),
                        domain=pack.id,
                        url=call.page.url,
                        ok=call.page.ok,
                    )
                )
        return events

    def _claim_events(
        self, run_id: RunId, pack: DomainPack, log: ToolLog, claims: Sequence[Claim]
    ) -> list[RunEvent]:
        events: list[RunEvent] = []
        pages, rows = log.pages, log.search_rows
        for claim in claims:
            events.append(ClaimEvent(run_id=run_id, ts=self._clock(), domain=pack.id, claim=claim))
            checked = self._verify(claim, pages, rows)
            if checked.verified:
                events.append(
                    VerifiedEvent(run_id=run_id, ts=self._clock(), domain=pack.id, claim=checked)
                )
            else:
                reason = checked.verify_note or "not verified: no receipt matched this run's log"
                events.append(
                    DroppedEvent(
                        run_id=run_id,
                        ts=self._clock(),
                        domain=pack.id,
                        claim=checked,
                        reason=reason,
                    )
                )
        return events

    async def run(
        self, run_id: RunId, request: RunRequest, pack: DomainPack
    ) -> AsyncIterator[RunEvent]:
        log = ToolLog()
        text = await self._invoke(pack, request, log)
        for event in self._tool_events(run_id, pack, log):
            yield event
        try:
            claims = parse_claims(text, pack, log, self._clock())
        except ValueError as exc:
            yield ErrorEvent(run_id=run_id, ts=self._clock(), domain=pack.id, message=str(exc))
            return
        for event in self._claim_events(run_id, pack, log, claims):
            yield event
