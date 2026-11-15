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
  2026-11-15, a deliberate tightening of the spec's `partial_ratio >= 90` rule): a `quote_fuzzy`
  match also requires every number token in the quote to appear as a whole token in the page's
  token list. A number token is the regex `[$€£¥]?\\d+(?:[.,]\\d+)*%?` on the normalized quote
  and page (same `normalize()` for both); `19.99` is one token, never split. Tokens compare as
  strings after stripping only thousands-separator commas (a comma followed by exactly three
  digits), so `1,000 == 1000` while the decimal comma in `19,99` stays; the currency sign and `%`
  stay part of the token. The **exact** path applies the same number check (GitHub issue #33):
  a substring that cuts a page number, such as `basic is $19` inside `basic is $199`, is not
  `quote_exact` and falls through to the fuzzy rule, which reports the number. A one-digit price
  change scores ~97, and a battlecard must never show a wrong number as verified. `normalize`
  keeps `$ € £ % . ,` next to digits, so the token regex runs on the normalized strings.
* **Claim numbers must be in the quote** (GitHub issue #33): once the quote is on the page
  (`quote_exact` or `quote_fuzzy`), every number token in the normalized `claim.text` must also
  be a number token of the normalized quote, by the same token rule and thousands-comma
  stripping as above. Otherwise the claim is a miss (not dropped) with the note
  `claim numbers not in quote: <tokens>`. A quote on the page proves only what the quote says;
  a price the model added to the claim text is not covered by it. A claim with no number tokens
  is unaffected, and the quote may carry numbers the claim does not repeat.
* `SearchReceipt`: verified (`search_log`) iff a logged `SearchResult` has the same `query`,
  `url` and `rank`. A query that was never logged this run is **dropped**; a logged query whose
  rows do not contain that url/rank is a miss. The claim-number rule above is out of scope for
  search receipts (there is no quote to check the claim text against).

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
_NOTE_CLAIM_NUMBERS = "claim numbers not in quote: "

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
_NUMBER_TOKEN = re.compile(r"[$€£¥]?\d+(?:[.,]\d+)*%?")
_THOUSANDS_COMMA = re.compile(r",(?=\d{3}(?!\d))")
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
    quote = normalize(receipt.quote)
    method, note = _match_quote(quote, normalize(page.text))
    if method is None:
        return _outcome(claim, verified=False, method=None, note=note)
    unsupported = _missing_numbers(normalize(claim.text), quote)
    if unsupported:
        note = f"{_NOTE_CLAIM_NUMBERS}{', '.join(unsupported)}"
        return _outcome(claim, verified=False, method=None, note=note)
    return _outcome(claim, verified=True, method=method, note=note)


def _match_quote(quote: str, body: str) -> tuple[VerifyMethod | None, str | None]:
    """How the normalized `quote` is on the normalized page `body`: `(method, note)`.

    `method` is `None` on a miss, and `note` then says why. A substring that starts or ends inside
    a page number (`$19` in `$199`) is not exact; it falls through to the fuzzy rule, whose
    number check reports it.
    """
    if quote and quote in body and not _missing_numbers(quote, body):
        return "quote_exact", None
    miss = _fuzzy_miss(quote, body)
    if miss is not None:
        return None, miss
    score = fuzz.partial_ratio(quote, body)
    return "quote_fuzzy", f"fuzzy match: partial_ratio={score:.1f} >= {FUZZY_THRESHOLD}"


def _canonical_number(token: str) -> str:
    """Token with thousands-separator commas removed (`1,000` -> `1000`; `19,99` unchanged)."""
    return _THOUSANDS_COMMA.sub("", token)


def _missing_numbers(text: str, reference: str) -> list[str]:
    """Number tokens of `text` that are not number tokens of `reference`, sorted, deduplicated.

    The one number comparison for both rules (quote against page, claim against quote): tokens
    from `_NUMBER_TOKEN`, compared after `_canonical_number`, reported as written in `text`.
    """
    present = {_canonical_number(tok) for tok in _NUMBER_TOKEN.findall(reference)}
    return sorted(
        {tok for tok in _NUMBER_TOKEN.findall(text) if _canonical_number(tok) not in present}
    )


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
    missing = _missing_numbers(quote, body)
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
