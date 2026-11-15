"""Pure verification rules: a claim is checked against this run's fetched pages and search log.

No clock, no network, no I/O, no model call. Every function returns a new value; the frozen
`Claim` input is never changed.

Rules (spec "Verifier rules", scope cut 2026-11-14 row 4: no LLM note):

* `QuoteReceipt`: the URL must be a key of `pages` (fetched this run), else the claim is
  **dropped**. A page with `ok=False` is "fetch failed", not "claim false". Otherwise both texts
  pass through `normalize`; an exact substring is `quote_exact`, else
  `rapidfuzz.fuzz.partial_ratio >= FUZZY_THRESHOLD` is `quote_fuzzy`, else a miss. The fuzzy
  match must cover the *whole quote* (`partial_ratio_alignment`'s span over the quote is
  `[0, len(quote))`); otherwise a page shorter than the quote would match inside the quote and
  "verify" text that is not on the page. **Numbers must match** (project owner's ruling,
  2026-11-15, a deliberate tightening of the spec's `partial_ratio >= 90` rule): "a
  `quote_fuzzy` match also requires every number token in the quote (digits, with any currency
  sign, decimal point or %) to appear verbatim in the normalized page text; otherwise the claim
  is not verified. Exact-substring matches are unaffected." A one-digit price change scores
  ~97, and a battlecard must never show a wrong number as verified. `normalize` keeps `$ € £ %
  . ,` next to digits, so the token regex runs on the normalized strings.
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
_IMAGE = re.compile(r"!\[([^\]]*)\]\([^)]*\)")  # ![alt](src) -> alt; runs before _LINK so that
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")  # [![alt](src)](url) -> [alt](url) -> alt in one pass
_HEADING = re.compile(r"^[ \t]*#{1,6}[ \t]+", re.MULTILINE)
_BULLET = re.compile(r"^[ \t]*(?:[-*+]|\d+\.)[ \t]+", re.MULTILINE)
_STAR = re.compile(r"\*")
# strips _em_ and __strong__, keeps snake_case
_UNDERSCORE_EMPHASIS = re.compile(r"(?<!\w)_+|_+(?!\w)")
_WHITESPACE = re.compile(r"\s+")
_NUMBER_TOKEN = re.compile(r"[$€£]?\d+(?:[.,]\d+)?%?")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_DASHES = str.maketrans({"–": "-", "—": "-"})


def normalize(text: str) -> str:
    """Canonical text for matching: markdown stripped, lower-cased, whitespace collapsed.

    Steps, in order: code fences and backticks removed (their contents kept); `![alt](src)` then
    `[text](url)` reduced to the text (image first, so a linked image `[![alt](src)](url)`
    becomes `alt` in one pass); heading marks and list bullets at line starts removed;
    `*` removed everywhere and `_` where it wraps a word (`snake_case` survives); curly quotes
    unified to `'` and `"`; en and em dashes unified to `-`; lower-cased; every whitespace run
    collapsed to one space and the ends stripped. Deterministic and idempotent.
    """
    out = _CODE_FENCE.sub("", text)
    out = _BACKTICK.sub("", out)
    out = _IMAGE.sub(r"\1", out)
    out = _LINK.sub(r"\1", out)
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
    miss = _fuzzy_miss(quote, body)
    if miss is not None:
        return _outcome(claim, verified=False, method=None, note=miss)
    score = fuzz.partial_ratio(quote, body)
    note = f"fuzzy match: partial_ratio={score:.1f} >= {FUZZY_THRESHOLD}"
    return _outcome(claim, verified=True, method="quote_fuzzy", note=note)


def _fuzzy_miss(quote: str, body: str) -> str | None:
    """Why the normalized `quote` is *not* a fuzzy match for `body`, or `None` when it is.

    `partial_ratio` slides the *shorter* string along the longer one. When the page is the
    shorter one, the page is matched inside the quote, so a 7-char page scores 100 against a
    made-up 42-char quote. The alignment's `src_*` span is the part of the quote (first
    argument) that matched; it must be the whole quote. Then every number token in the quote must
    be on the page verbatim (module docstring: numbers must match).
    """
    alignment = fuzz.partial_ratio_alignment(quote, body)
    score = 0.0 if alignment is None else alignment.score
    if alignment is None or score < FUZZY_THRESHOLD:
        return f"quote not found on page: best partial_ratio={score:.1f} < {FUZZY_THRESHOLD}"
    missing = sorted(set(_NUMBER_TOKEN.findall(quote)) - set(_NUMBER_TOKEN.findall(body)))
    if missing:
        return (
            f"quote not found on page: numbers differ ({', '.join(missing)} not on page; "
            f"partial_ratio={score:.1f})"
        )
    if not (alignment.src_start == 0 and alignment.src_end == len(quote)):
        covered = alignment.src_end - alignment.src_start
        return (
            "quote not found on page: fuzzy match does not cover the whole quote "
            f"(partial_ratio={score:.1f} on {covered}/{len(quote)} chars)"
        )
    return None


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
