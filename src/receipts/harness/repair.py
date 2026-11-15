"""Mellea repair loop for specialist claims (GitHub issue #39, ADR-0007).

After the agent's final message is parsed, and before any claim is emitted, `SpecialistRunner`
checks every claim with the Verifier it was given (L2's `verify_claim` in production). A claim
the Verifier would not mark verified goes to a `ClaimRepairer` as a `RepairRequest`: the claim,
the Verifier's reason, the evidence it may cite, and two callables bound to this run, `check`
(the same Verifier over this run's pages and search rows) and `parse` (`parse_claims` for this
pack).

`MelleaClaimRepairer` runs Mellea's instruct-validate-repair loop: `ainstruct` with one
`Requirement` whose `validation_fn` parses the reply and runs `check`, under
`RepairTemplateStrategy(loop_budget=MAX_REPAIRS)`. The agent wrote the first draft, so every
Mellea generation is a repair and `loop_budget` is the repair budget: at most two model calls
per claim. When a reply fails the check, Mellea appends the failure reason to the instruction
and asks again. The reply is a fenced ```json list with one claim in the agent's own format.

What Mellea cannot do:
- decide `verified`. The reply goes through `parse` (`_ClaimDraft` ignores any `verified` key),
  the runner clears the verify fields of whatever a repairer returns, and the Verifier then
  judges the repaired claim like any other;
- change whom the claim is about: `about` is always the original's;
- keep a claim from the Verifier. A claim not repaired within the budget, within the pack's
  time budget, or because the backend raised, goes to the Verifier unchanged and is dropped or
  unverified there, exactly as without Mellea.

Mellea is imported inside `MelleaClaimRepairer.__call__`, never at module import, so importing
the app or calling `create_app()` loads neither Mellea nor LiteLLM.
"""

from __future__ import annotations

import importlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

from receipts.contracts import Claim, DomainPack, FetchedPage, SearchReceipt, SearchResult
from receipts.harness.tools import PAGE_TEXT_LIMIT

if TYPE_CHECKING:
    from mellea.core import (
        Backend,
        Context,
        Requirement,
        SamplingResult,
        SamplingStrategy,
        ValidationResult,
    )

MAX_REPAIRS = 2
"""Model calls per failing claim (each one is a repair; the agent wrote the first draft)."""

RECEIPT_REQUIREMENT = (
    "The claim's receipt passes the receipt check against the pages fetched and the searches "
    "logged in this run."
)

_TASK = (
    "You wrote this claim for a competitive battlecard, but its receipt failed the receipt "
    "check, so the claim would be dropped.\n"
    "Claim: {claim}\n"
    "Why the check failed: {failure}\n"
    "Rewrite the claim so that its receipt passes, using only the evidence above. A quote "
    "receipt needs a url from the evidence and a quote copied character for character from that "
    "page. Every price, percentage or other number in the claim text must also be in the quote, "
    "so narrow the claim rather than state anything the quote does not say. A search receipt "
    "needs a query, rank and url exactly as one row of the search log.\n"
    "Reply with only a fenced ```json block holding a list with exactly one claim, in the same "
    "format as the claim above."
)
_REASON_CHARS = 300

Check = Callable[[Claim], Claim]
"""The Verifier bound to this run's pages and search rows."""
Parse = Callable[[str], list[Claim]]
"""`parse_claims` bound to this pack and run; raises `ValueError` on an unparseable reply."""


@dataclass(frozen=True)
class RepairRequest:
    claim: Claim
    failure: str
    evidence: Mapping[str, str]
    check: Check
    parse: Parse


class ClaimRepairer(Protocol):
    """Proposes a replacement for a failing claim, or `None` when it found none."""

    async def __call__(self, request: RepairRequest) -> Claim | None: ...


RepairFactory = Callable[[DomainPack], ClaimRepairer]


# --- evidence and prompt -----------------------------------------------------------------------


def _render_rows(rows: Sequence[SearchResult]) -> str:
    if not rows:
        return "No searches were logged this run."
    return "\n".join(
        json.dumps({"query": r.query, "rank": r.rank, "url": r.url, "title": r.title}) for r in rows
    )


def evidence_for(
    claim: Claim, pages: Mapping[str, FetchedPage], rows: Sequence[SearchResult]
) -> dict[str, str]:
    """What the repair may cite, by label: the search log for a search receipt; the cited page
    for a quote receipt when it was fetched, else every page fetched this run. Pages are cut to
    `PAGE_TEXT_LIMIT`, the same view the agent had."""
    receipt = claim.receipt
    if isinstance(receipt, SearchReceipt):
        return {"search log": _render_rows(rows)}
    page = pages.get(receipt.url)
    if page is not None and page.ok:
        return {page.url: page.text[:PAGE_TEXT_LIMIT]}
    return {p.url: p.text[:PAGE_TEXT_LIMIT] for p in pages.values() if p.ok}


def _draft_json(claim: Claim) -> str:
    receipt = claim.receipt.model_dump(mode="json", exclude={"ts"})
    return json.dumps({"about": claim.about, "text": claim.text, "receipt": receipt})


def repair_prompt(request: RepairRequest) -> str:
    return _TASK.format(claim=_draft_json(request.claim), failure=request.failure)


def judge(reply: str, request: RepairRequest) -> tuple[Claim | None, str]:
    """The repaired claim and why it passes, or `None` and why not (Mellea's repair feedback).

    The decision is `request.check`, the Verifier itself; the returned claim is the parsed one,
    never the checked copy, so it carries no verification of its own.
    """
    try:
        claims = request.parse(reply)
    except ValueError as exc:
        return None, f"the reply was not one claim in a fenced json block ({exc})"[:_REASON_CHARS]
    if len(claims) != 1:
        return None, f"the reply held {len(claims)} claims; it must hold exactly one"
    claim = claims[0].model_copy(update={"about": request.claim.about})
    checked = request.check(claim)
    if not checked.verified:
        return None, checked.verify_note or "the receipt check failed"
    return claim, "the receipt check passed"


# --- Mellea -------------------------------------------------------------------------------------


class MelleaClaimRepairer:
    """`ClaimRepairer` over Mellea's instruct-validate-repair loop and an injected backend.

    `backend` is called once per repair, so the live factory builds the LiteLLM backend only
    when a claim actually needs repairing.
    """

    def __init__(self, backend: Callable[[], Backend], *, max_repairs: int = MAX_REPAIRS) -> None:
        if max_repairs < 1:
            raise ValueError("max_repairs must be at least 1")
        self._backend = backend
        self._max_repairs = max_repairs

    async def __call__(self, request: RepairRequest) -> Claim | None:
        from mellea.core import Requirement
        from mellea.stdlib.context import SimpleContext
        from mellea.stdlib.sampling import RepairTemplateStrategy

        result = await _ainstruct()(
            repair_prompt(request),
            SimpleContext(),
            self._backend(),
            requirements=[Requirement(RECEIPT_REQUIREMENT, validation_fn=_validator(request))],
            strategy=RepairTemplateStrategy(loop_budget=self._max_repairs),
            grounding_context={**request.evidence},
            return_sampling_results=True,
        )
        if not result.success:
            return None
        claim, _reason = judge(str(result.result.value), request)
        return claim


class _AInstruct(Protocol):
    """The one overload of `mellea.stdlib.functional.ainstruct` this module calls."""

    async def __call__(
        self,
        description: str,
        context: Context,
        backend: Backend,
        *,
        requirements: list[Requirement | str],
        strategy: SamplingStrategy,
        grounding_context: dict[str, str],
        return_sampling_results: Literal[True],
    ) -> SamplingResult[str]: ...


def _ainstruct() -> _AInstruct:
    """`ainstruct`, reached through `importlib` so pyright strict stays clean (as `build_agent`).

    Mellea 0.9.0 types `ainstruct`'s `model_options` as a bare `dict`, which strict mode reports
    as partially unknown at the import. A module attribute is typed `Any`, so the function is
    narrowed to `_AInstruct`, the protocol naming the parameters used; no ignore comment needed.
    """
    functional = importlib.import_module("mellea.stdlib.functional")
    ainstruct: _AInstruct = functional.ainstruct
    return ainstruct


def _validator(request: RepairRequest) -> Callable[[Context], ValidationResult]:
    from mellea.core import ValidationResult

    def receipt_passes(ctx: Context) -> ValidationResult:
        output = ctx.last_output()
        reply = "" if output is None or output.value is None else str(output.value)
        claim, reason = judge(reply, request)
        return ValidationResult(claim is not None, reason=reason)

    return receipt_passes
