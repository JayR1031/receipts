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
  "verify" text that is not on the page.
* **Numbers must match where the quote matches.** Sources, all from Claude Code sessions, none an
  owner ruling:
  - Fuzzy path: the coordinating session's ruling of 2026-11-15 01:11 UTC (the plan file's
    "Coordinator rulings"; a deliberate tightening of the spec's `partial_ratio >= 90` rule).
  - The per-place comparison: the gh-33 round-2 judge's HIGH #1 (a set test over the match
    window let swapped prices verify). The widened window: the round-3 judge's HIGH #1, with
    the slack pad the round-3 judge prototyped and the round-4 judge proposed.
  - Exact path: the L2 judge's LOW 7 and the gh-33 judge's HIGH #1, with the edge rule set by
    the coordinating session.

  A number
  token is the regex `[$€£¥]?\\d+(?:[.,]\\d+)*%?` on the normalized text; `19.99` is one token,
  never split, and the currency sign and `%` are part of it. Tokens compare after
  `_canonical_number`: thousands-separator commas removed (a comma followed by exactly three
  digits, so `1,000 == 1000` while the decimal comma in `19,99` stays) and a zero decimal part
  removed (`$20.00 == $20.0 == $20`; `$20.05` and `$20.50` stay). `normalize` writes `20 %` and
  `20 percent` as `20%`. Number words and suffixes are out of scope: `three` is not `3`, `1.5k`
  is not `1,500`, and `20 dollars` or `20 USD` is not `$20`.
  - **Exact path**: an occurrence of the quote counts only if neither of its edges falls inside
    a page number token. `basic is $19` inside `basic is $199`, `basic is $19.` inside
    `$19.99`, `99 per seat` inside `$19.99 per seat`, `save 20` inside `save 20%` and
    `20 per month` inside `$20 per month` are all cuts. Every occurrence is tried, so the same
    text with a whole number elsewhere on the page still counts. A quote with no clean
    occurrence falls through to the fuzzy rule.
  - **Fuzzy path**: each number token of the quote is compared with the page text at its
    aligned place, not with the whole page or the whole match window. The place comes from
    `Indel.opcodes`, the character alignment behind the score. The quote is aligned against the
    score window widened on each side by its *slack* (`_slack`): the quote characters a first
    alignment against the bare window left unmatched, plus the window's shortfall from the
    quote's length. That reaches a first or last number the window cut off. Because it is no
    wider than what the quote left out, a quote price seldom reaches past the page's own price
    at that place (even a word price like `custom`) to the next plan's equal price; the label
    limit below covers what remains. There the page must have exactly one number
    token, read whole even when the alignment cuts it, and it must equal the quote's. So all of
    these are misses:
    - `pro yearly: $19 billed` on `pro yearly: $199 billed. pro monthly: $19 billed.`;
    - quotes that swap the page's prices (`pro yearly: $19. pro monthly: $199.` on
      `pro yearly: $199. pro monthly: $19.`) or repeat one;
    - a quote price whose characters the alignment spreads over two page prices (`plus $49` on
      `plus $29; max $49`);
    - a quote that puts the next plan's price where the page has a word price
      (`plus ... is $20` on `plus ... is custom; team is $20`).

    The note pairs each differing quote number with what the page has there, in quote order:
    `numbers differ (quote has $19, $199; page has $199, $19 there; ...)`.
  - **Known limit, labels are not checked (fail-open; also on `main`):** only numbers are
    compared, so a changed or dropped plan name next to a price can attach another plan's real
    price. Each of these verifies:
    - `tier b: $29` on `tier a: $29 ... tier b: $19`;
    - `basic $200 pro max $1,999` on `basic $200 pro $1,999 max $8`: the alignment drops `max`,
      because pairing the longer `$1,999` matches more characters.

    Rate in PR #35's random tests at attempt 5: 2 of the 109,249 wrong-price quotes among
    160,000 generated on two- to four-price pages (`7363a43`: 22). The scripts are in the review
    records, not in the repository. Tracked in GitHub issue #45.
  - **Known limit, a price carried past the page's own price (fail-open):** the widened
    alignment can carry a quote price past the page's own price at its place, a word or a
    different price, to the next plan's equal price. Example, verified here and a miss on
    `7363a43`: `the starter plan ... is $9 per seat` on
    `the starter plan ... is free. pro $9 per seat`. Rates at attempt 5:
    - 22 of 7,439 misquotes on pages whose own price at that place is a word or a different
      price (`7363a43`: 22; with a fixed quarter pad: 107);
    - 1 of 6,000 that give one plan the next plan's price a short label away, 4,004 of which
      leave words out earlier (`7363a43`: 0).

    Tracked in #45.
  - **Known limit, some true quotes fail closed:** the alignment can leave a quote number with
    no page number, or with two, although the page has it. It is then a miss, and the note can
    say `page has no number there`, although the page has the number further on. This happens:
    - when the quote leaves out more page text than its slack covers (`the max plan is $200` on
      `the max plan with priority support is $200`);
    - when the quote leaves out words right next to one of its prices, such as
      `pro $9, growth $15 a month, lite $1 a month` on
      `pro $9 per month, growth $15 a month, lite $1 a month.`, or `starter 2,500 seats $9` on
      `... starter 2,500 seats for $9.`

    Rates at attempt 5: 10 of 5,998 true quotes, and 3 of 2,931 on pages dense with prices.
    Tracked in #45.

  A one-digit price change scores ~97. The aim is that a battlecard never shows a wrong number
  as verified; the known limits in this docstring are the exceptions. `normalize` keeps
  `$ € £ % . ,` next to digits, so the token regex runs on the normalized strings.
* **Claim numbers must be in the quote** (GitHub issue #33): once the quote is on the page
  (`quote_exact` or `quote_fuzzy`), every **value token** in the normalized `claim.text` must
  also be a number token of the normalized quote, compared as above. A value token is a number
  token with a currency sign, a `%`, a decimal part or a thousands separator (`$20`, `20%`,
  `19.5`, `2,500`). A bare integer is not checked, so a year (`As of 2025`), a plan or model
  name (`Pro 2`, `GPT-4`), `24/7` or a date need not be in the quote. Known limit: a bare
  integer count is not checked either, so `500 credits` or `50 seats` in the claim verifies when
  the quote lacks it, and `18000 credits` is unchecked while `18,000 credits` is checked. Known
  limit: a price without an attached sign is a bare integer too, so a claim's `25 dollars`,
  `25 USD` or `$ 25` is unchecked and verifies against a quote saying `$20` (fail-open on the
  claim side; on the quote side the same spelling fails closed, per the paragraph above). A name
  or date with a decimal point (`GPT-4.5`, `14.11.2026`) is a value token and is checked. The
  word `free` in the quote matches a zero price in the claim (`$0`, `€0`, `£0`, `¥0`, and
  `$0.00` and the like; `0 dollars` is a bare integer and is not checked), and nothing else: not
  `$5`, not `$0.50`, and not `freedom`. Known limit: any standalone `free` anywhere in the
  quote counts, including `not free`, `free trial` and another plan's free tier.
  A miss (not dropped) has the note `claim numbers not in quote: <tokens>`, sorted and
  deduplicated. A quote on the page proves only what the quote says; a price the model added to
  the claim text is not covered by it. The quote may carry numbers the claim does not repeat.
  Known limit: the rule checks that each value is in the quote, not which plan or billing term
  it belongs to, so values swapped inside one quote still verify.
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
from rapidfuzz.distance import Indel

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
_ZERO_DECIMAL = re.compile(r"^([^.]*\d)\.00?(%?)$")  # one dot only: `1.0.0` is not `1.0`
_VALUE_MARK = re.compile(r"[$€£¥%.,]")
_PERCENT = re.compile(r"(?<=\d) ?(?:%|percent\b)")  # `20 %`, `20 percent` -> `20%`
_FREE = re.compile(r"\bfree\b")
_ZERO_PRICES = ("$0", "€0", "£0", "¥0")
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})
_DASHES = str.maketrans({"–": "-", "—": "-"})


def normalize(text: str) -> str:
    """Canonical text for matching: markdown stripped, lower-cased, whitespace collapsed.

    Steps, in order: code fences and backticks removed (their contents kept); `![alt](src)` then
    `[text](url)` reduced to the text (image first, so a linked image `[![alt](src)](url)`
    becomes `alt` in one pass); heading marks and list bullets at line starts removed;
    `*` removed everywhere and `_` where it wraps a word (`snake_case` survives); curly quotes
    unified to `'` and `"`; en and em dashes unified to `-`; lower-cased; every whitespace run
    collapsed to one space and the ends stripped; a digit's `%` or `percent` (with or without one
    space) written as `%`, so `20 %` and `20 percent` read `20%`. Deterministic and idempotent.
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
    out = _WHITESPACE.sub(" ", out).strip()
    return _PERCENT.sub("%", out)


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
    unsupported = _missing_numbers(_claim_values(claim.text), _quote_values(quote))
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
    spans = [match.span() for match in _NUMBER_TOKEN.finditer(body)]
    if quote and _occurs_with_whole_numbers(quote, body, spans):
        return "quote_exact", None
    miss = _fuzzy_miss(quote, body, spans)
    if miss is not None:
        return None, miss
    score = fuzz.partial_ratio(quote, body)
    return "quote_fuzzy", f"fuzzy match: partial_ratio={score:.1f} >= {FUZZY_THRESHOLD}"


def _occurs_with_whole_numbers(quote: str, body: str, spans: Sequence[tuple[int, int]]) -> bool:
    """True iff some occurrence of `quote` in `body` cuts no page number token at either edge.

    `spans` are the `(start, end)` of every number token in `body`. Every occurrence is tried:
    a page can cut `$199` in one line and hold the same text with a whole `$19` in the next.
    """
    start = body.find(quote)
    while start != -1:
        end = start + len(quote)
        if not any(s < start < e or s < end < e for s, e in spans):
            return True
        start = body.find(quote, start + 1)
    return False


def _numbers_at(body: str, spans: Sequence[tuple[int, int]], start: int, end: int) -> list[str]:
    """The page number tokens that overlap `body[start:end]`, each read whole.

    A token cut by either edge counts in full, so a match window ending inside `$199` reads
    `$199`, not `$19`.
    """
    return [body[s:e] for s, e in spans if s < end and e > start]


def _canonical_number(token: str) -> str:
    """One spelling per value: thousands commas and a zero decimal part removed.

    `1,000` -> `1000` (`19,99` unchanged: a comma before two digits is a decimal comma), then
    `$20.00` and `$20.0` -> `$20` and `20.0%` -> `20%` (`$20.05`, `$20.50` and `1.0.0`
    unchanged). The currency sign and `%` stay.
    """
    return _ZERO_DECIMAL.sub(r"\1\2", _THOUSANDS_COMMA.sub("", token))


def _claim_values(text: str) -> list[str]:
    """The value tokens of the normalized claim `text`: number tokens with `$ € £ ¥ % . ,`.

    A bare integer (`2025`, `Pro 2`, `24/7`, `GPT-4`) is left out (module docstring).
    """
    return [tok for tok in _NUMBER_TOKEN.findall(normalize(text)) if _VALUE_MARK.search(tok)]


def _quote_values(quote: str) -> list[str]:
    """The number tokens of the normalized `quote`, plus a zero price when it says `free`.

    For the claim rule only: a claim's `$0` or `$0.00` is the quote's "free" (live run
    run-6a5fe9499c4d). The word must stand alone, so "freedom" does not count.
    """
    tokens = _NUMBER_TOKEN.findall(quote)
    return [*tokens, *_ZERO_PRICES] if _FREE.search(quote) else tokens


def _missing_numbers(tokens: Iterable[str], reference: Iterable[str]) -> list[str]:
    """`tokens` whose canonical form is no `reference` token's: sorted, deduplicated, as written.

    The one number comparison for every rule (quote against the page text at the match, claim
    against quote): `_NUMBER_TOKEN` tokens compared after `_canonical_number`.
    """
    present = {_canonical_number(tok) for tok in reference}
    return sorted({tok for tok in tokens if _canonical_number(tok) not in present})


def _char_map(quote: str, window: str) -> list[int | None]:
    """For each character of `quote`, its index in `window` when the alignment matched it.

    The alignment is `Indel.opcodes`, the edit script behind `partial_ratio`'s score. A quote
    character that the alignment deletes or replaces maps to `None`.
    """
    out: list[int | None] = [None] * len(quote)
    for op in Indel.opcodes(quote, window):
        if op.tag == "equal":
            for i in range(op.src_start, op.src_end):
                out[i] = op.dest_start + i - op.src_start
    return out


def _aligned_range(
    char_map: Sequence[int | None], start: int, end: int, size: int
) -> tuple[int, int]:
    """The range of the `size`-character window aligned to `quote[start:end]`.

    It runs from the first matched character to the last. When none matched (`$9` where the page
    says `free`), it is the gap between the matched neighbours, and it reaches the window's ends
    when a side has none.
    """
    hits = [d for d in char_map[start:end] if d is not None]
    if hits:
        return min(hits), max(hits) + 1
    before = [d for d in char_map[:start] if d is not None]
    after = [d for d in char_map[end:] if d is not None]
    return (before[-1] + 1 if before else 0), (after[0] if after else size)


def _slack(char_map: Sequence[int | None], window_size: int) -> int:
    """How far the score window may be widened on each side: the quote's characters it left out.

    That is the quote characters the first alignment matched to nothing (`None` in `char_map`),
    plus the window's shortfall from the quote's length (`partial_ratio`'s window is at most
    `len(quote)` long, and is sometimes shorter). The page text the quote matches runs past the
    window by about that much. A fixed pad (a quarter of the quote) let a quote price reach past
    the page's own price slot, even a word price like `custom`, to the next plan's equal price
    (gh-33 round-4 judge HIGH #1).
    """
    return sum(1 for dest in char_map if dest is None) + max(0, len(char_map) - window_size)


def _widened(start: int, end: int, pad: int, limit: int) -> tuple[int, int]:
    """`[start, end)` widened by `pad` on each side, clipped to the page `[0, limit)`."""
    return max(0, start - pad), min(limit, end + pad)


def _number_mismatches(
    quote: str, body: str, spans: Sequence[tuple[int, int]], window: tuple[int, int]
) -> list[tuple[str, str]]:
    """`(quote token, page tokens there)` for each quote number the page lacks at that place.

    `window` is the alignment's score window in `body`. The quote is aligned against it once to
    find the characters it left out (`_slack`), then against the window widened by that much
    (`_widened`). Each quote number token must meet exactly one page number token at its aligned
    place (read whole by `_numbers_at`), and that token must be equal. So a quote that swaps,
    repeats or shifts the page's prices is a miss even though every price is in the window, and
    so is a quote price whose characters the alignment spread over two page prices (`$9` across
    `$14, pro $9`).
    Pairs are in quote order and deduplicated; the page side is `no number` when there is none.
    """
    offset, stop = window
    pad = _slack(_char_map(quote, body[offset:stop]), stop - offset)
    offset, stop = _widened(offset, stop, pad, len(body))
    char_map = _char_map(quote, body[offset:stop])
    pairs: list[tuple[str, str]] = []
    for match in _NUMBER_TOKEN.finditer(quote):
        lo, hi = _aligned_range(char_map, *match.span(), stop - offset)
        there = _numbers_at(body, spans, offset + lo, offset + hi)
        if len(there) != 1 or _missing_numbers([match.group()], there):
            pair = (match.group(), ", ".join(there) or "no number")
            if pair not in pairs:
                pairs.append(pair)
    return pairs


def _fuzzy_miss(quote: str, body: str, spans: Sequence[tuple[int, int]]) -> str | None:
    """Why the normalized `quote` is *not* a fuzzy match for `body`, or `None` when it is.

    `partial_ratio` slides the *shorter* string along the longer one. When the page is the
    shorter one, the page is matched inside the quote, so a 7-char page scores 100 against a
    made-up 42-char quote. The alignment's `src_*` span is the part of the quote (first
    argument) that matched; it must be the whole quote. Then every number token in the quote must
    be the page's number at the same place in the match (`_number_mismatches`), not just
    somewhere on the page or in the match window (module docstring: numbers must match).
    """
    alignment = fuzz.partial_ratio_alignment(quote, body)
    score = 0.0 if alignment is None else alignment.score
    if alignment is None or score < FUZZY_THRESHOLD:
        return f"quote not found on page: best partial_ratio={score:.1f} < {FUZZY_THRESHOLD}"
    window = (alignment.dest_start, alignment.dest_end)
    mismatches = _number_mismatches(quote, body, spans, window)
    if mismatches:
        # Name what the page says there: "$19 not on page" is false when "$19" is on the page
        # elsewhere, or when the page writes "$20" where the quote writes "20".
        quote_side = ", ".join(token for token, _ in mismatches)
        page_side = ", ".join(there for _, there in mismatches)
        return (
            f"quote not found on page: numbers differ (quote has {quote_side}; "
            f"page has {page_side} there; partial_ratio={score:.1f})"
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
