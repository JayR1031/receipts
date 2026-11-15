"""Pure verification rules: a claim is checked against this run's fetched pages and search log.

No clock, no network, no I/O, no model call. Every function returns a new value; the frozen
`Claim` input is never changed.

Rules (spec "Verifier rules", scope cut 2026-11-14 row 4: no LLM note):

* `QuoteReceipt`: the URL must be a key of `pages` (fetched this run), else the claim is
  **dropped**. A page with `ok=False` is "fetch failed", not "claim false". Otherwise both texts
  pass through `normalize`; an exact substring is `quote_exact`, else
  `rapidfuzz.fuzz.partial_ratio >= FUZZY_THRESHOLD` is `quote_fuzzy`, else a miss.
* `SearchReceipt`: verified (`search_log`) iff a logged `SearchResult` has the same `query`,
  `url` and `rank`. A query that was never logged this run is **dropped**; a logged query whose
  rows do not contain that url/rank is a miss.

Dropped-claim convention (L1 keys `DroppedEvent` off this; W2 relies on it too):
    verified=False, verify_method=None, verify_note=f"{DROPPED_PREFIX}<reason>"
`is_dropped(claim)` tests exactly that, and `dropped_reason(claim)` returns `<reason>` for the
`DroppedEvent.reason` field. A miss or a fetch failure is *not* dropped: it stays in the
battlecard as an unverified claim with a plain note.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence

from rapidfuzz import fuzz

from receipts.contracts import (
    Claim,
    FetchedPage,
    QuoteReceipt,
    SearchReceipt,
    SearchResult,
    VerifyMethod,
)

FUZZY_THRESHOLD = 90
"""Minimum `partial_ratio` (0–100) for a `quote_fuzzy` verification."""

DROPPED_PREFIX = "dropped: "
NOTE_URL_NOT_FETCHED = f"{DROPPED_PREFIX}url not fetched this run"
NOTE_QUERY_NOT_LOGGED = f"{DROPPED_PREFIX}search query not logged this run"
NOTE_FETCH_FAILED = "fetch failed"

# --- normalize ----------------------------------------------------------------------

_CODE_FENCE = re.compile(r"```[^\S\n]*")  # the fence itself; the info string and body stay
_BACKTICK = re.compile(r"`")
_IMAGE_OR_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")  # [text](url) and ![alt](url) -> text
_HEADING = re.compile(r"^[ \t]*#{1,6}[ \t]+", re.MULTILINE)
_BULLET = re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+", re.MULTILINE)
_STAR = re.compile(r"\*")
# strips _em_ and __strong__, keeps snake_case
_UNDERSCORE_EMPHASIS = re.compile(r"(?<!\w)_+|_+(?!\w)")
_WHITESPACE = re.compile(r"\s+")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_DASHES = str.maketrans({"–": "-", "—": "-"})


def normalize(text: str) -> str:
    """Canonical text for matching: markdown stripped, lower-cased, whitespace collapsed.

    Steps, in order: code fences and backticks removed (their contents kept); `[text](url)` and
    `![alt](url)` reduced to the text; heading marks and list bullets at line starts removed;
    `*` removed everywhere and `_` where it wraps a word (`snake_case` survives); curly quotes
    unified to `'` and `"`; en and em dashes unified to `-`; lower-cased; every whitespace run
    collapsed to one space and the ends stripped. Deterministic and idempotent.
    """
    out = _CODE_FENCE.sub("", text)
    out = _BACKTICK.sub("", out)
    out = _IMAGE_OR_LINK.sub(r"\1", out)
    out = _HEADING.sub("", out)
    out = _BULLET.sub("", out)
    out = _STAR.sub("", out)
    out = _UNDERSCORE_EMPHASIS.sub("", out)
    out = out.translate(_QUOTES).translate(_DASHES).lower()
    return _WHITESPACE.sub(" ", out).strip()


# --- dropped convention ---------------------------------------------------------------


def is_dropped(claim: Claim) -> bool:
    """True iff the verifier dropped the claim (see module docstring for the convention)."""
    return dropped_reason(claim) is not None


def dropped_reason(claim: Claim) -> str | None:
    """The reason text after `DROPPED_PREFIX`, or `None` when the claim was not dropped."""
    note = claim.verify_note
    if claim.verified or note is None or not note.startswith(DROPPED_PREFIX):
        return None
    return note[len(DROPPED_PREFIX) :]


# --- rules --------------------------------------------------------------------------


def _outcome(
    claim: Claim, *, verified: bool, method: VerifyMethod | None, note: str | None
) -> Claim:
    return claim.model_copy(
        update={"verified": verified, "verify_method": method, "verify_note": note}
    )


def _verify_quote(claim: Claim, receipt: QuoteReceipt, pages: Mapping[str, FetchedPage]) -> Claim:
    page = pages.get(receipt.url)
    if page is None:
        return _outcome(claim, verified=False, method=None, note=NOTE_URL_NOT_FETCHED)
    if not page.ok:
        return _outcome(claim, verified=False, method=None, note=NOTE_FETCH_FAILED)
    quote, body = normalize(receipt.quote), normalize(page.text)
    if quote and quote in body:
        return _outcome(claim, verified=True, method="quote_exact", note=None)
    score = fuzz.partial_ratio(quote, body)
    if score >= FUZZY_THRESHOLD:
        note = f"fuzzy match: partial_ratio={score:.1f} >= {FUZZY_THRESHOLD}"
        return _outcome(claim, verified=True, method="quote_fuzzy", note=note)
    note = f"quote not found on page: best partial_ratio={score:.1f} < {FUZZY_THRESHOLD}"
    return _outcome(claim, verified=False, method=None, note=note)


def _verify_search(claim: Claim, receipt: SearchReceipt, searches: Sequence[SearchResult]) -> Claim:
    logged = [row for row in searches if row.query == receipt.query]
    if not logged:
        return _outcome(claim, verified=False, method=None, note=NOTE_QUERY_NOT_LOGGED)
    if any(row.url == receipt.url and row.rank == receipt.rank for row in logged):
        return _outcome(claim, verified=True, method="search_log", note=None)
    note = f"no logged row for query at rank {receipt.rank} with that url"
    return _outcome(claim, verified=False, method=None, note=note)


def verify_claim(
    claim: Claim, pages: Mapping[str, FetchedPage], searches: Sequence[SearchResult]
) -> Claim:
    """Apply the receipt's rule and return a new `Claim`; the input is left untouched."""
    receipt = claim.receipt
    if isinstance(receipt, QuoteReceipt):
        return _verify_quote(claim, receipt, pages)
    return _verify_search(claim, receipt, searches)


def verify_all(
    claims: Iterable[Claim], pages: Mapping[str, FetchedPage], searches: Sequence[SearchResult]
) -> tuple[Claim, ...]:
    """`verify_claim` over every claim, order preserved."""
    return tuple(verify_claim(claim, pages, searches) for claim in claims)
