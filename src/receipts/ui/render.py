# pyright: basic
"""Pure rendering for the UI: contracts in, Markdown or table rows out.

Nothing here touches Gradio, the clock or the network, so every helper is tested without a
browser. `app.py` only glues these onto components.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from itertools import groupby

from receipts.contracts import (
    Battlecard,
    Claim,
    ClaimEvent,
    DoneEvent,
    DroppedEvent,
    ErrorEvent,
    FetchEvent,
    QuoteReceipt,
    Receipt,
    RunEvent,
    RunSummary,
    SearchEvent,
    StartedEvent,
    VerifiedEvent,
)

HISTORY_HEADERS: tuple[str, ...] = ("Run", "Status", "Verified", "Started")


def _ts(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%d %H:%M UTC")


def _clock(ts: datetime) -> str:
    return ts.strftime("%H:%M:%S")


def _describe_claim_step(event: ClaimEvent | VerifiedEvent | DroppedEvent) -> str:
    match event:
        case ClaimEvent(claim=claim):
            return f"{claim.about}: {claim.text}"
        case VerifiedEvent(claim=claim):
            return f"{claim.verify_method or 'verified'}: {claim.text}"
        case DroppedEvent(claim=claim, reason=reason):
            return f"dropped ({reason}): {claim.text}"


def _describe_source_step(event: SearchEvent | FetchEvent) -> str:
    match event:
        case SearchEvent(query=query, results=results):
            return f"{query!r}: {len(results)} result(s)"
        case FetchEvent(url=url, ok=True):
            return f"fetched {url}"
        case FetchEvent(url=url):
            return f"fetch failed {url}"


def _describe(event: RunEvent) -> str:
    """The kind-specific part of the line; the stamp and domain are added by the caller."""
    match event:
        case StartedEvent(subject=subject, rival=rival, domains=domains):
            return f"{subject} vs {rival}: {', '.join(domains)}"
        case ErrorEvent(message=message):
            return message
        case DoneEvent(verified_count=verified, total_count=total):
            return f"{verified} of {total} verified"
        case SearchEvent() | FetchEvent():
            return _describe_source_step(event)
        case _:
            return _describe_claim_step(event)


def render_event_line(event: RunEvent) -> str:
    """One short line per event; the kind is always named so the log reads at a glance."""
    where = f" ({event.domain})" if event.domain else ""
    return f"{_clock(event.ts)} [{event.kind}]{where} {_describe(event)}"


def _render_receipt(receipt: Receipt) -> str:
    if isinstance(receipt, QuoteReceipt):
        return f'quote: "{receipt.quote}" — <{receipt.url}>'
    return f"search {receipt.query!r} #{receipt.rank} — <{receipt.url}>"


def _render_claim(claim: Claim) -> str:
    marker = "[verified]" if claim.verified else "[unverified]"
    note = f" ({claim.verify_note})" if claim.verify_note else ""
    return f"- {marker} **{claim.about}**: {claim.text}{note}  \n  {_render_receipt(claim.receipt)}"


def render_battlecard(card: Battlecard) -> str:
    """Markdown: the verified count, then one row per claim grouped by domain."""
    head = [
        f"# {card.subject} vs {card.rival}",
        f"**{card.verified_count} of {card.total_count} verified**"
        f" · started {_ts(card.started_at)} · finished {_ts(card.finished_at)}",
        "",
    ]
    if not card.claims:
        return "\n".join([*head, "_No claims survived verification._"])
    body: list[str] = []
    for domain, claims in groupby(
        sorted(card.claims, key=lambda c: c.domain), key=lambda c: c.domain
    ):
        body.append(f"## {domain}")
        body.extend(_render_claim(claim) for claim in claims)
        body.append("")
    return "\n".join(head + body).rstrip() + "\n"


def render_history(rows: Sequence[RunSummary]) -> list[list[str]]:
    """Table rows in the order given (the service lists newest first)."""
    return [
        [
            f"{row.subject} vs {row.rival}",
            row.status,
            f"{row.verified_count} of {row.total_count}",
            _ts(row.started_at),
        ]
        for row in rows
    ]
