# pyright: basic
"""Pure rendering for the UI: contracts in, HTML, text or table rows out.

Nothing here touches Gradio, the clock or the network, so every helper is tested without a
browser. `app.py` only glues these onto components.

The battlecard is HTML shown in a `gr.HTML`, which does not sanitize. Claim text, quotes, notes,
company names and URLs come from the web or from visitors, so every one goes through
`html.escape`, and a receipt URL becomes a link only when its scheme is http or https.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from html import escape
from itertools import groupby
from urllib.parse import urlsplit

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


DOMAIN_TITLES: dict[str, str] = {
    "pricing": "Pricing",
    "positioning_seo": "Positioning & SEO",
    "news_social": "News & social",
    "product": "Product",
}
METHOD_LABELS: dict[str, str] = {
    "quote_exact": "exact quote on the page",
    "quote_fuzzy": "near-exact quote on the page",
    "search_log": "matched the search log",
}
NO_CARD_HTML = (
    '<div class="bc"><p class="bc-empty">Run finished but no battlecard was stored.</p></div>'
)


def _duration(started: datetime, finished: datetime) -> str:
    seconds = max(0, int((finished - started).total_seconds()))
    minutes, seconds = divmod(seconds, 60)
    return f"{minutes}m {seconds:02d}s" if minutes else f"{seconds}s"


def _link(url: str) -> str:
    """The URL as a short label (host and path); a link only for http and https."""
    parts = urlsplit(url)
    label = escape((parts.netloc + parts.path).removeprefix("www.").rstrip("/") or url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return f'<span class="bc-url">{label}</span>'
    return (
        f'<a class="bc-url" href="{escape(url, quote=True)}" target="_blank" '
        f'rel="noopener noreferrer nofollow">{label}</a>'
    )


def _receipt_html(receipt: Receipt, method: str | None) -> str:
    label = METHOD_LABELS.get(method, method) if method else None
    how = f' · <span class="bc-method">{escape(label)}</span>' if label else ""
    if isinstance(receipt, QuoteReceipt):
        return (
            f'<blockquote class="bc-quote">“{escape(receipt.quote)}”</blockquote>'
            f'<p class="bc-source">{_link(receipt.url)}{how}</p>'
        )
    return (
        f'<p class="bc-source"><span class="bc-search">search “{escape(receipt.query)}”, '
        f"result #{receipt.rank}</span> · {_link(receipt.url)}{how}</p>"
    )


def _claim_html(claim: Claim, card: Battlecard) -> str:
    company = card.subject if claim.about == "subject" else card.rival
    if claim.verified:
        mark = '<span class="bc-mark status-verified" aria-label="verified">✓</span>'
        why = ""
    else:
        mark = '<span class="bc-mark status-dropped" aria-label="not verified">✕</span>'
        note = claim.verify_note or "No receipt matched this run's log."
        why = (
            '<p class="bc-why"><span class="status-dropped">Why it was dropped:</span> '
            f"{escape(note)}</p>"
        )
    state = "verified" if claim.verified else "dropped"
    return (
        f'<article class="bc-claim bc-claim-{state}">'
        f'<div class="bc-claim-row">{mark}<p class="bc-claim-text">{escape(claim.text)}</p>'
        f'<span class="bc-about">{escape(company)}</span></div>'
        f"{why}{_receipt_html(claim.receipt, claim.verify_method)}</article>"
    )


def _domain_html(domain: str, claims: list[Claim], card: Battlecard) -> str:
    kept = [c for c in claims if c.verified]
    dropped = [c for c in claims if not c.verified]
    title = escape(DOMAIN_TITLES.get(domain, domain.replace("_", " ").capitalize()))
    parts = [
        '<section class="bc-domain">',
        f'<h3 class="bc-domain-title">{title}'
        f'<span class="bc-domain-count">{len(kept)} of {len(claims)} verified</span></h3>',
        *(_claim_html(c, card) for c in kept),
    ]
    if dropped:
        noun = "claim" if len(dropped) == 1 else "claims"
        parts += [
            '<details class="bc-dropped">',
            f"<summary>{len(dropped)} dropped {noun}, and why</summary>",
            *(_claim_html(c, card) for c in dropped),
            "</details>",
        ]
    parts.append("</section>")
    return "".join(parts)


def _score_html(card: Battlecard) -> str:
    verified, total = card.verified_count, card.total_count
    share = 100 * verified / total if total else 0
    summary = f"{verified} of {total} claims verified"
    return (
        '<div class="bc-score">'
        f'<span class="bc-score-num">{verified}<span class="bc-score-of"> / {total}</span></span>'
        '<span class="bc-score-label">claims verified</span></div>'
        f'<div class="bc-meter" role="img" aria-label="{summary}">'
        f'<span class="bc-meter-fill" style="width: {share:.1f}%"></span></div>'
    )


def render_battlecard(card: Battlecard) -> str:
    """HTML: a score header, then each domain's verified claims, with its dropped ones folded
    underneath, each showing why it was dropped."""
    head = (
        '<header class="bc-head">'
        f'<p class="bc-eyebrow">Battlecard · {escape(str(card.run_id))}</p>'
        f'<h2 class="bc-title">{escape(card.subject)} <span class="bc-vs">vs</span> '
        f"{escape(card.rival)}</h2>"
        f"{_score_html(card)}"
        f'<p class="bc-meta">Started {_ts(card.started_at)} · '
        f"took {_duration(card.started_at, card.finished_at)}</p></header>"
    )
    if not card.claims:
        return (
            f'<div class="bc">{head}<p class="bc-empty">No claims survived verification.</p></div>'
        )
    order = list(DOMAIN_TITLES)
    domains = groupby(
        sorted(card.claims, key=lambda c: (order.index(c.domain), c.domain)), key=lambda c: c.domain
    )
    body = "".join(_domain_html(domain, list(claims), card) for domain, claims in domains)
    return f'<div class="bc">{head}{body}</div>'


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
