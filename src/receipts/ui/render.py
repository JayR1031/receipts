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
from dataclasses import dataclass, field
from datetime import datetime
from html import escape
from itertools import groupby
from urllib.parse import quote, urlsplit

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


SHARE_PATH = "/share"
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


def _url_label(url: str) -> str:
    parts = urlsplit(url)
    return (parts.netloc + parts.path).removeprefix("www.").rstrip("/") or url


def _link(url: str) -> str:
    """The URL as a short label (host and path); a link only for http and https."""
    parts = urlsplit(url)
    label = escape(_url_label(url))
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


def _domain_title(domain: str) -> str:
    return DOMAIN_TITLES.get(domain, domain.replace("_", " ").capitalize())


def _domain_html(domain: str, claims: list[Claim], card: Battlecard) -> str:
    kept = [c for c in claims if c.verified]
    dropped = [c for c in claims if not c.verified]
    title = escape(_domain_title(domain))
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


def share_path(card: Battlecard) -> str:
    """The battlecard's public, read-only page (`receipts.api.share`)."""
    return f"{SHARE_PATH}/{quote(str(card.run_id), safe='')}"


def render_battlecard(card: Battlecard, *, share: bool = False) -> str:
    """HTML: a score header, then each domain's verified claims, with its dropped ones folded
    underneath, each showing why it was dropped. `share` adds a link to the card's share page."""
    link = (
        f'<a class="bc-share" href="{escape(share_path(card), quote=True)}" target="_blank" '
        'rel="noopener">Share this battlecard ↗</a>'
        if share
        else ""
    )
    head = (
        '<header class="bc-head">'
        f'<p class="bc-eyebrow">Battlecard · {escape(str(card.run_id))}</p>'
        f'<h2 class="bc-title">{escape(card.subject)} <span class="bc-vs">vs</span> '
        f"{escape(card.rival)}</h2>"
        f"{_score_html(card)}"
        f'<p class="bc-meta">Started {_ts(card.started_at)} · '
        f"took {_duration(card.started_at, card.finished_at)}</p>{link}</header>"
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


PROGRESS_STEPS: tuple[str, ...] = ("Search", "Read", "Draft", "Verify")
PROGRESS_WAITING = "Starting the run…"
_STAGE_LABELS = ("Queued", "Searching", "Reading pages", "Drafting claims", "Verifying")
_STAGE_OF: dict[str, int] = {"search": 1, "fetch": 2, "claim": 3, "verified": 4, "dropped": 4}


@dataclass
class _Lane:
    """One domain's tally, folded from its events. `stage` indexes `_STAGE_LABELS`."""

    stage: int = 0
    searches: int = 0
    pages: int = 0
    drafted: int = 0
    verified: int = 0
    dropped: int = 0
    activity: str = "Waiting for its first search"
    error: str | None = None


@dataclass
class _Progress:
    lanes: dict[str, _Lane] = field(default_factory=dict)
    started: StartedEvent | None = None
    last: datetime | None = None
    done: DoneEvent | None = None
    errors: list[str] = field(default_factory=list)


def _source_step(lane: _Lane, event: SearchEvent | FetchEvent) -> None:
    match event:
        case SearchEvent(query=query, results=results):
            lane.searches += 1
            lane.activity = f"Searched “{query}”: {len(results)} result(s)"
        case FetchEvent(url=url, ok=True):
            lane.pages += 1
            lane.activity = f"Read {_url_label(url)}"
        case FetchEvent(url=url):
            lane.activity = f"Could not read {_url_label(url)}"


def _claim_step(lane: _Lane, event: ClaimEvent | VerifiedEvent | DroppedEvent) -> None:
    match event:
        case ClaimEvent(claim=claim):
            lane.drafted += 1
            lane.activity = f"Drafted: {claim.text}"
        case VerifiedEvent(claim=claim):
            lane.verified += 1
            lane.activity = f"Verified: {claim.text}"
        case DroppedEvent(claim=claim, reason=reason):
            lane.dropped += 1
            lane.activity = f"Dropped ({reason}): {claim.text}"


def _lane_step(lane: _Lane, event: RunEvent) -> None:
    lane.stage = max(lane.stage, _STAGE_OF.get(event.kind, 0))
    match event:
        case SearchEvent() | FetchEvent():
            _source_step(lane, event)
        case ClaimEvent() | VerifiedEvent() | DroppedEvent():
            _claim_step(lane, event)
        case ErrorEvent(message=message):
            lane.error = message


def _apply(progress: _Progress, event: RunEvent) -> None:
    progress.last = event.ts
    match event:
        case StartedEvent(domains=domains):
            progress.started = event
            for domain in domains:
                progress.lanes.setdefault(domain, _Lane())
        case DoneEvent():
            progress.done = event
        case ErrorEvent(domain=None, message=message):
            progress.errors.append(message)
        case _ if event.domain is not None:
            _lane_step(progress.lanes.setdefault(event.domain, _Lane()), event)


def _plural(count: int, noun: str, plural: str = "") -> str:
    return f"{count} {noun if count == 1 else plural or noun + 's'}"


def _total(progress: _Progress, name: str) -> int:
    return sum(getattr(lane, name) for lane in progress.lanes.values())


def _meter_html(reached: int, total: int) -> str:
    share = 100 * reached / total if total else 100.0
    return (
        f'<div class="rp-meter" role="progressbar" aria-label="Run progress" aria-valuemin="0" '
        f'aria-valuemax="{total}" aria-valuenow="{reached}" '
        f'aria-valuetext="{reached} of {total} steps reached">'
        f'<span class="rp-meter-fill" style="width: {share:.1f}%"></span></div>'
    )


def _errors_html(progress: _Progress) -> str:
    return "".join(
        f'<p class="rp-error"><span class="status-dropped">Run error:</span> {escape(message)}</p>'
        for message in progress.errors
    )


def _steps_html(lane: _Lane) -> str:
    items = []
    for number, name in enumerate(PROGRESS_STEPS, start=1):
        state = "done" if number < lane.stage else "current" if number == lane.stage else "todo"
        current = ' aria-current="step"' if state == "current" else ""
        items.append(f'<li class="rp-step rp-step-{state}"{current}>{name}</li>')
    return f'<ol class="rp-steps">{"".join(items)}</ol>'


def _counts_html(lane: _Lane) -> str:
    counts = (
        ("searches", lane.searches, ""),
        ("pages read", lane.pages, ""),
        ("drafted", lane.drafted, ""),
        ("verified", lane.verified, " status-verified"),
        ("dropped", lane.dropped, " status-dropped"),
    )
    items = "".join(
        f'<li class="rp-count"><span class="rp-count-num{status if count else ""}">{count}</span>'
        f" {label}</li>"
        for label, count, status in counts
    )
    return f'<ul class="rp-counts">{items}</ul>'


def _lane_html(domain: str, lane: _Lane) -> str:
    if lane.error is not None:
        state, status, activity = "error", "Stopped", f"Error: {lane.error}"
    else:
        state = "active" if lane.stage else "queued"
        status, activity = _STAGE_LABELS[lane.stage], lane.activity
    status_class = " status-dropped" if lane.error is not None else ""
    return (
        f'<li class="rp-lane rp-lane-{state}"><div class="rp-lane-head">'
        f'<h3 class="rp-lane-title">{escape(_domain_title(domain))}</h3>'
        f'<span class="rp-lane-status{status_class}">{status}</span></div>'
        f"{_steps_html(lane)}{_counts_html(lane)}"
        f'<p class="rp-activity" title="{escape(activity, quote=True)}">{escape(activity)}</p>'
        "</li>"
    )


def _top_html(label: str, clock: str) -> str:
    return (
        f'<div class="rp-top"><p class="rp-eyebrow"><span class="rp-dot" aria-hidden="true">'
        f'</span>{label}</p><p class="rp-clock">{clock}</p></div>'
    )


def _running_html(progress: _Progress, started: StartedEvent) -> str:
    total = len(PROGRESS_STEPS) * len(progress.lanes)
    reached = sum(lane.stage for lane in progress.lanes.values())
    order = list(DOMAIN_TITLES)
    lanes = sorted(progress.lanes.items(), key=lambda item: order.index(item[0]))
    tally = (
        f"{_plural(_total(progress, 'pages'), 'page')} read · "
        f"{_plural(_total(progress, 'drafted'), 'claim')} drafted · "
        f"{_total(progress, 'verified')} verified · {_total(progress, 'dropped')} dropped"
    )
    elapsed = _duration(started.ts, progress.last or started.ts)
    return (
        '<div class="rp rp-running"><header class="rp-head">'
        f"{_top_html('Run in progress', f'{elapsed} elapsed')}"
        f'<h2 class="rp-title">{escape(started.subject)} <span class="rp-vs">vs</span> '
        f"{escape(started.rival)}</h2>{_meter_html(reached, total)}"
        f'<p class="rp-meta">{reached} of {total} steps reached · {tally}</p>'
        f"{_errors_html(progress)}</header>"
        f'<ol class="rp-lanes">{"".join(_lane_html(d, lane) for d, lane in lanes)}</ol></div>'
    )


def _done_html(progress: _Progress, done: DoneEvent) -> str:
    took = f"took {_duration(progress.started.ts, done.ts)}" if progress.started else ""
    sources = (
        f"{_plural(_total(progress, 'pages'), 'page')} read from "
        f"{_plural(_total(progress, 'searches'), 'search', 'searches')} across "
        f"{_plural(len(progress.lanes), 'domain')}"
    )
    return (
        f'<div class="rp rp-done">{_top_html("Run finished", took)}{_meter_html(1, 1)}'
        f'<p class="rp-meta">{done.verified_count} of {done.total_count} claims verified · '
        f"{sources}</p>{_errors_html(progress)}</div>"
    )


def render_progress_notice(message: str) -> str:
    """A one-line message in the progress slot: a blank form or a refused start."""
    return f'<div class="rp rp-notice"><p class="rp-notice-text">{escape(message)}</p></div>'


def render_progress(events: Sequence[RunEvent]) -> str:
    """HTML for the live progress view, from the run's events so far: one lane per domain with
    its steps, counts and latest activity, under a meter of steps reached and the elapsed time
    between the first and latest event. Once the run is done it collapses to one summary line."""
    progress = _Progress()
    for event in events:
        _apply(progress, event)
    if progress.done is not None:
        return _done_html(progress, progress.done)
    if progress.started is None:
        return render_progress_notice(PROGRESS_WAITING)
    return _running_html(progress, progress.started)


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
