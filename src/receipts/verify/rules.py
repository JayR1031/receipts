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
    window let swapped prices verify).
  - Exact path: the L2 judge's LOW 7 and the gh-33 judge's HIGH #1, with the edge rule set by
    the coordinating session.

  The owner chose these rules over two widened-window variants (gh-33 attempts 4 and 5), which
  let wrong prices verify in other quote shapes. A number
  token is `_NUMBER_TOKEN` on the normalized text: digits with `.` or `,` groups (`19.99` is one
  token, never split), with a currency sign or `%` as part of it. The sign leads (`$20`), leads
  a decimal point (`$.99`), or directly follows the digits (`25$`), unless a number follows the
  sign, which then leads that number (`5$20` is `5` and `$20`); after a leading sign, a `k`,
  `m` or `b` that no letter or digit follows is part of the token (`$20k`, `$1.2m`; GitHub
  issue #45, rule (d)), so `$5 max` and `$5/mo` stay `$5`. Tokens compare after
  `_canonical_number`: a trailing sign moved to the front (`25$ == $25`), a leading point given
  its zero (`$.99 == $0.99`), thousands-separator commas removed (a comma followed by exactly
  three digits, so `1,000 == 1000` while the decimal comma in `19,99` stays), a suffix written
  out (`$20k == $20,000`, `$1.2m == $1,200,000`) and a zero decimal part removed
  (`$20.00 == $20.0 == $20`; `$20.05` and `$20.50` stay). `normalize` writes `20 %` and
  `20 percent` as `20%`. Out of scope (known limits, below): number words (`three` is not `3`);
  `bn`, `mm`, `million` and `thousand`, a space before a suffix, a suffix on an unsigned number
  (`1.5k` is not `1,500`; `$1.5k` is) and a decimal comma before a suffix; and, in the
  quote-to-page match, `20 dollars`, `20 USD` and `$ 20` are not `$20` (the claim rule reads
  them as `$20`; below).
  - **Exact path**: an occurrence of the quote counts only if neither of its edges falls inside
    a page number token. `basic is $19` inside `basic is $199`, `basic is $19.` inside
    `$19.99`, `99 per seat` inside `$19.99 per seat`, `save 20` inside `save 20%` and
    `20 per month` inside `$20 per month` are all cuts. Every occurrence is tried, so the same
    text with a whole number elsewhere on the page still counts. A quote with no clean
    occurrence falls through to the fuzzy rule.
  - **Fuzzy path**: each number token of the quote is compared with the page text at its
    aligned place, not with the whole page or the whole match window. The place comes from
    the character alignment behind the score (`Indel.opcodes` of the quote against the
    alignment's `dest_*` window), and each page token is read whole even when the alignment
    cuts it. So `pro yearly: $19` against `pro yearly: $199. pro monthly: $19.` is a miss, and
    so are quotes that swap the page's prices (`pro yearly: $19. pro monthly: $199.`) or repeat
    one. The note pairs each differing quote number with what the page has there, in quote
    order: `numbers differ (quote has $19, $199; page has $199, $19 there; ...)`.

  A one-digit price change scores ~97. The aim is that a battlecard never shows a wrong number
  as verified; the known limits below are the exceptions. `normalize` keeps
  `$ € £ % . ,` next to digits, so the token regex runs on the normalized strings.
* **Claim numbers must be in the quote** (GitHub issue #33): once the quote is on the page
  (`quote_exact` or `quote_fuzzy`), every **value token** of the normalized `claim.text`, its
  unsigned prices read as signed (below), must also be a value of the normalized quote, compared
  as above: one of its number tokens, or the signed reading of one of its unsigned prices. A
  value token is a number token with a currency sign, a `%`, a decimal part or a thousands
  separator (`$20`, `20%`, `19.5`, `2,500`), or a count (next). Any other bare integer is not
  checked, so a year (`As of 2025`), a plan or model name (`Pro 2`, `GPT-4`), `24/7` or a date
  need not be in the quote.
  **Counts with units** (GitHub issue #45, rule (a)): a bare integer followed by `credit`,
  `seat`, `user`, `member`, `project`, `message`, `request`, `token`, `minute` or `hour`,
  singular or plural, with nothing, one space or one hyphen between (`500credits`, `500
  credits`, `50-seat`) or one other word between (`5 active users`, `1500 hosted-ai credits`),
  is a count. So `500 credits` in the claim misses a quote with `18,000 credits`, which backs
  `18000 credits`. It is read after the unsigned prices (below), so `$ 25 per seat` is the
  price `$25` and not also 25 seats. A count compares its value, not its unit (known limits,
  below).
  **Unsigned prices** (GitHub issue #45, rule (c); the claim rule only): a number followed by
  one space and `dollar`, `dollars`, `usd`, `euro`, `euros`, `eur`, `gbp`, `jpy` or `yen`;
  `usd`, `eur`, `gbp` or `jpy` followed by one space and a number; a sign followed by one space
  and a number (`$ 25`); and a number followed by one space and a sign (`25 €`) are read as the
  signed price (`25 dollars`, `25 USD`, `USD 25` and `$ 25` as `$25`; `25 €` as `€25`). In the
  claim this reading takes the number's place; in the quote it is added to the quote's own
  tokens, so a quote `25 dollars` backs a claim's `$25`, `25 dollars` or bare `25`. `pounds`,
  `bucks` and number words are not read. The quote-to-page match does not use this reading: a
  quote `20 dollars` on a page `$20` is still a miss (fail-closed; that match stays as PR #35
  measured it).
  A name or date with a decimal point (`GPT-4.5`, `14.11.2026`) is a value token and is checked.
  The word `free` in the quote matches a zero price in the claim (`$0`, `€0`, `£0`, `¥0`,
  `$0.00` and the like, and so `0 dollars`), and nothing else: not `$5`, not `$0.50`, and not
  `freedom`. A negated or trial `free` does not count (GitHub issue #45, rule (b)): one with
  `not`, `no`, `never`, `isn't`, `isnt`, `aren't`, `arent`, `without` or `non` among the two
  words before it (`not free`, `no free plan`, `non-free`), or with `trial` or `trials` directly
  after it (`free trial`, `free trials`). Any other standalone `free` anywhere in the quote
  counts, including another plan's free tier (known limit (e), below).
  A miss (not dropped) has the note `claim numbers not in quote: <values>`, sorted and
  deduplicated. Each value is named in its signed reading, the one spelling for rules (c) and
  (d): the sign in front and a leading point given its zero (`25 dollars`, `$ 25` and `25$` are
  named `$25`; `$.99` is `$0.99`), and otherwise as the normalized claim writes it (`$1.2m`,
  `$20.00`, `2,500`). The quote-to-page note names tokens as the quote and page write them.
  A quote on the page proves only what the quote says; a price the model added to
  the claim text is not covered by it. The quote may carry numbers the claim does not repeat.
  The rule checks that each value is in the quote, not which plan or billing term it belongs
  to (known limit (g), below).
* `SearchReceipt`: verified (`search_log`) iff a logged `SearchResult` has the same `query`,
  `url` and `rank`. A query that was never logged this run is **dropped**; a logged query whose
  rows do not contain that url/rank is a miss. The claim-number rule above is out of scope for
  search receipts (there is no quote to check the claim text against).

Known limits. Fail-open: a wrong claim can show as verified. Fail-closed: a true claim can show
as unverified. The repository owner accepted (e) to (h) on 2026-11-18 (GitHub issue #45). The
others follow from how issue #45's rules (a) to (d) and (i) were drawn: the issue's brief
(`docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md`, its assumptions) and the
owner's answers of 2026-11-19. Rates are counts from the random tests in `scripts/verify_fuzz/`
(PR #35's six scripts and issue #45's claim shapes, run by `run_baseline.py`) or from a live
run; a limit with no rate was not measured. (h) and the copied-receipt limit are in the harness
(`receipts.harness`), not in this module; they are listed here with the rest.

* **(e) Plan labels are not checked** (fail-open). Only numbers are compared, so a changed or
  dropped plan name next to a price can attach another plan's real price. `tier b: $29`
  verifies on `tier a: $29 ... tier b: $19`, and `basic $200 pro max $15` verifies on
  `basic $200 pro $15 max $12` (the alignment drops `max`; a test pins it). In the claim rule
  the same goes for `free`: one that is neither negated nor a trial counts wherever it is, so
  the quote `starter is free, pro is $20` backs the claim `Pro is $0`. Rates, from PR #35's
  random tests of the quote-to-page rule:
  - 22 of 160,000 quotes generated on two- to four-price pages verified with a price that is
    not its plan's (`fuzz_place2.py`, seeds 7, 11, 12 and 13); PR #35's `count_sets.py`, which
    is not committed, put 109,249 of the 160,000 as holding a wrong price;
  - 22 of 7,439 misquotes on pages whose own price at the quote's place is a word or a
    different price (`fuzz_skip.py`, seeds 5 and 6);
  - 2 of 3,678 add-a-word misquotes that score at least 90, of 10,994 generated (`fuzz_add.py`,
    seeds 51, 52 and 53).
* **(f) True quotes past the score window fail closed.** `partial_ratio`'s window is at most
  `len(quote)` long. When the page text a quote matches is longer, the quote's first or last
  number can fall outside the window and be aligned with no page number. It is then a miss,
  and the note usually says `page has no number there` (227 of the 230 random-test rejections
  counted next), although the page has the number just past the window (`...; business $10`
  on `... · business $10.`; tests pin five cases). Rates: 195 of 5,998 true quotes
  (`fuzz_place_all.py`), and 35 of 2,931 on pages dense with prices (`fuzz_dense.py`). A
  different cause rejects 2 of 6,941 true quotes that add a word (`fuzz_add.py`): the price is
  inside the window, but the alignment ties the added word's letters to text past the price.
* **(g) Values swapped inside one quote still verify** (fail-open). The claim rule checks that
  each value is in the quote, not which plan or billing term it belongs to: the claim `Pro is
  $19 a year and $199 a month` verifies on the quote `pro yearly: $199. pro monthly: $19.`.
* **(h) A repair can carry a plan name its quote lacks** (fail-open). Mellea rewrites a failing
  claim, at most twice, aiming for one this module accepts, and (e) lets the rewrite name a plan
  its quote does not. In the live run `run-a7be7a53cba9` (Mel vs Warp, repairs on, 2026-11-15),
  at least 6 of the 8 verified pricing claims did, for example `Mel Max is 18,000 hosted-AI
  credits a month.` on `Pro with the biggest bucket — 18,000 credits a month.`.
* **A count compares its value, not its unit** (fail-open; brief assumption 2): `500 seats` in
  the quote backs `500 credits` in the claim. Only the ten units count, after nothing, a space,
  a hyphen or one other word, so `30 days` and `5 very active users` are not checked.
* **A bare number before a unit is read as a count** (fail-closed; brief assumption 1, read
  literally): `25 per seat` with no sign is 25 seats, so the claim `Pro costs 25 per seat`
  misses the quote `pro costs $25 per seat` (note `25`); `In 2025 users` and `GPT-4 tokens`
  make `2025` and `4` values the quote must carry.
* **A bare integer with no unit is not checked** (fail-open, by design): a changed year, plan
  number, model number or `24/7` verifies. 300 of 300 such wrong claims verify in the
  `control` shape (`fuzz_claim_values.py 45 300 control`).
* **Unsigned spellings outside rule (c)'s lists are not prices** (brief assumption 3): `pounds`
  (often a weight), `bucks` and number words (`twenty-five dollars`). In the claim they are not
  checked (fail-open: `Pro costs 25 pounds` verifies on the quote `pro costs £20`); in the quote
  `25 pounds` does not back a claim's `£25` (fail-closed).
* **The quote-to-page match reads no unsigned price** (fail-closed; the owner's choice of
  2026-11-18, rule (c) in the claim rule only): the quote `pro costs 20 dollars` on the page
  `pro costs $20.` is a miss, as before issue #45.
* **Suffix forms out of scope** (brief assumption 6): `bn`, `mm`, `million` and `thousand`, a
  space before the suffix, a suffix on an unsigned number and a decimal comma before a suffix.
  `$20bn`, `$20mm`, `$20 million`, `$20 thousand` and `$20 k` read `$20`, and `1.5k` reads
  `1.5`, so the claim `Enterprise is $20 million` verifies on the quote `enterprise $20 per
  seat`, and the quote `enterprise $20` is `quote_exact` on the page `enterprise $20 million a
  year.` (fail-open). `$1,5k` is compared as written and misses `$1,500` (fail-closed).
* **A quote cut mid-word at a suffix letter** (both ways; the owner's decision of 2026-11-19,
  "Document it as a limit"): the quote `pro costs $5m`, cut from the page `pro costs $5mo for
  every seat.`, is `quote_exact`, and its `$5m` reads `$5,000,000` while the page's reads `$5`.
  So the true claim `Pro costs $5.` is rejected (fail-closed) and the wrong claim `Pro costs
  $5,000,000.` verifies (fail-open).
* **A trial `free` not directly before `trial`, and a negation across punctuation** (rule (b),
  brief assumption 8): `start your free 14-day trial` and `starter is free: trial included`
  still add a zero price, so a wrong `$0` verifies (fail-open; the owner's decision of
  2026-11-19, "Document it as a limit"). The two-word window runs across punctuation, so
  `no ads, free forever` adds no zero price and a true `$0` is rejected (fail-closed).
* **A copied receipt is caught only exactly, and only within one specialist** (rule (i), brief
  assumptions 9 and 10; fail-open): receipts are compared as exact strings, so a repair whose
  quote differs from another claim's only in case or spacing counts as a second claim on one
  piece of evidence; and `SpecialistRunner` sees one domain's claims, so a copy across domains
  is not caught (`Coordinator` cannot tell a repair from an original without a contract change).
* **Search receipts skip the claim-number rule** (by design): there is no quote to check the
  claim text against, so a price in the claim is not compared with the logged search result.

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
# On normalized (lower-case) text. A signed number: `$20`, `$19.99`, `$.99`, `$20k`, `$1.2m`,
# `$20%`; the suffix only when no letter or digit follows (`$5mo` is `$5`). An unsigned one:
# `20`, `1,000`, `20%`, or with its sign directly after the digits, `25$`, unless a number
# follows the sign, which then leads that number (`5$20` is `5` and `$20`, as before).
_NUMBER_TOKEN = re.compile(
    r"[$€£¥](?:\d+(?:[.,]\d+)*|\.\d+)(?:[kmb](?!\w)|%)?"
    r"|\d+(?:[.,]\d+)*(?:[$€£¥](?!\.?\d)|%)?"
)
_TRAILING_SIGN = re.compile(r"^(\d[\d.,]*)([$€£¥])$")  # `25$` -> `$25`
_LEADING_POINT = re.compile(r"^([$€£¥])\.")  # `$.99` -> `$0.99`
_SUFFIXED = re.compile(r"^([$€£¥])(\d+(?:\.\d+)?)([kmb])$")  # once thousands commas are gone
_SUFFIX_SHIFT = {"k": 3, "m": 6, "b": 9}
_THOUSANDS_COMMA = re.compile(r",(?=\d{3}(?!\d))")
_ZERO_DECIMAL = re.compile(r"^([^.]*\d)\.00?(%?)$")  # one dot only: `1.0.0` is not `1.0`
_VALUE_MARK = re.compile(r"[$€£¥%.,]")
_PERCENT = re.compile(r"(?<=\d) ?(?:%|percent\b)")  # `20 %`, `20 percent` -> `20%`
_FREE = re.compile(r"\bfree\b")
_ZERO_PRICES = ("$0", "€0", "£0", "¥0")
# Rule (b), on the normalized quote (brief assumption 8): a `free` that one of these words comes
# within the two words before, or that `trial` or `trials` directly follows, adds no zero price.
# A word is letters and digits with inner apostrophes, so `isn't` is one word and `non-free` is
# `non` and `free`; punctuation between words does not end the window.
_WORD = re.compile(r"\w+(?:'\w+)*")
_NEGATIONS = frozenset({"not", "no", "never", "isn't", "isnt", "aren't", "arent", "without", "non"})
_NEGATION_WINDOW = 2
_TRIAL = re.compile(r"[ -]trials?\b")  # `free trial(s)`, `free-trial`; not `free: trial`
# Rule (a), matched where a bare integer ends, on the text after `_signed_prices` (brief
# assumption 1): a unit from the closed list, singular or plural and ending its word, after
# nothing, one space or one hyphen (`500credits`, `500 credits`, `50-seat`), or after one other
# word with a space or hyphen on each side (`5 active users`, `1500 hosted-ai credits`).
_COUNT_UNITS = "credit|seat|user|member|project|message|request|token|minute|hour"
_GAP_WORD = r"[^\W\d_]+(?:-[^\W\d_]+)*"  # letters only, hyphens inside: `active`, `hosted-ai`
_COUNT_UNIT = re.compile(rf"(?:[ -]{_GAP_WORD}[ -]|[ -]?)(?:{_COUNT_UNITS})s?\b")
# Rule (c), for the claim rule only, on normalized text: an unsigned price. A number, one space
# and a currency word or sign (`25 dollars`, `25 €`); a currency code, one space and a number
# (`usd 25`); or a sign, one space and a number (`$ 25`). No number inside a longer token is read
# (`$25 dollars` stays `$25`, `$.25 usd` stays `$.25`), and a sign that a number follows leads
# that number, as in `_NUMBER_TOKEN` (`5 $20` and `5 $ 20` are `5` and `$20`).
_AMOUNT = r"\d+(?:[.,]\d+)*"
_UNSIGNED_PRICE = re.compile(
    rf"(?<![\w$€£¥.,])(?P<n1>{_AMOUNT}) (?:"
    r"(?P<w1>dollars?|usd|euros?|eur|gbp|jpy|yen)\b(?![.,]\d)|(?P<s1>[$€£¥])(?! ?[.,]?\d))"
    rf"|\b(?P<w2>usd|eur|gbp|jpy) (?P<n2>{_AMOUNT})"
    rf"|(?<![\w.,])(?P<s2>[$€£¥]) (?P<n3>{_AMOUNT})"
)
_CURRENCY_WORD = {
    "dollar": "$",
    "dollars": "$",
    "usd": "$",
    "euro": "€",
    "euros": "€",
    "eur": "€",
    "gbp": "£",
    "jpy": "¥",
    "yen": "¥",
}
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
    """One spelling per value, for a `_NUMBER_TOKEN` token.

    In order: a trailing sign moved to the front (`25$` -> `$25`); a leading decimal point given
    its zero (`$.99` -> `$0.99`); thousands commas removed (`1,000` -> `1000`; `19,99` unchanged:
    a comma before two digits is a decimal comma); a suffix written out (`$20k` -> `$20000`,
    `$1.2m` -> `$1200000`; `$1,5k`, with a decimal comma, unchanged); then a zero decimal part
    removed (`$20.00` and `$20.0` -> `$20`, `20.0%` -> `20%`; `$20.05`, `$20.50` and `1.0.0`
    unchanged). The currency sign and `%` stay.
    """
    out = _TRAILING_SIGN.sub(r"\2\1", token)
    out = _LEADING_POINT.sub(r"\g<1>0.", out)
    out = _THOUSANDS_COMMA.sub("", out)
    out = _SUFFIXED.sub(_expand_suffix, out)
    return _ZERO_DECIMAL.sub(r"\1\2", out)


def _expand_suffix(match: re.Match[str]) -> str:
    """`$1.2` with `m` -> `$1200000`: the decimal point moved 3, 6 or 9 places to the right.

    Done on the digits, not with `float` or `Decimal`, so no amount is rounded. Leading zeros go
    (`$0.5k` -> `$500`); digits left past the point stay (`$1.2345k` -> `$1234.5`).
    """
    sign, amount, suffix = match.groups()
    whole, _, fraction = amount.partition(".")
    point = len(whole) + _SUFFIX_SHIFT[suffix]
    digits = whole + fraction.ljust(_SUFFIX_SHIFT[suffix], "0")
    value = digits[:point].lstrip("0") or "0"
    rest = digits[point:]
    return f"{sign}{value}.{rest}" if rest else f"{sign}{value}"


def _signed(match: re.Match[str]) -> str:
    """The signed spelling of an `_UNSIGNED_PRICE` match: `25 dollars` or `$ 25` -> `$25`."""
    word = match["w1"] or match["w2"]
    sign = _CURRENCY_WORD[word] if word else match["s1"] or match["s2"]
    return f"{sign}{match['n1'] or match['n2'] or match['n3']}"


def _signed_prices(text: str) -> str:
    """The normalized `text` with each unsigned price written signed (rule (c), claim rule only).

    `pro costs 25 dollars` -> `pro costs $25`; `usd 25`, `$ 25` and `25 usd` -> `$25`; `25 €` and
    `25 euros` -> `€25`; `gbp 25` -> `£25`; `25 yen` -> `¥25`. Only these spellings (brief
    assumption 3): `25 pounds`, `25 bucks` and number words are left as they are. The result is
    read with `_NUMBER_TOKEN`, so `$ 20k` reads `$20k`, as `$20k` does.
    """
    return _UNSIGNED_PRICE.sub(_signed, text)


def _signed_reading(token: str) -> str:
    """A `_NUMBER_TOKEN` token with its sign in front and a leading point given its zero.

    `25$` -> `$25`, `$.99` -> `$0.99`; every other token is unchanged (`$1.2m`, `$20.00`, `2,500`).
    These are the first two steps of `_canonical_number`, so the canonical form does not change.
    It is the spelling the claim rule's miss note shows.
    """
    return _LEADING_POINT.sub(r"\g<1>0.", _TRAILING_SIGN.sub(r"\2\1", token))


def _claim_values(text: str) -> list[str]:
    """The value tokens of the claim `text`, each in its signed reading.

    The readings, in this order; each number is read once, by the first reading that takes it:

    1. `normalize`.
    2. Unsigned prices written signed (`_signed_prices`, rule (c)): `25 dollars`, `25 usd`,
       `usd 25`, `$ 25` and `25 €` become `$25` and `€25` in the text. This reading consumes the
       number: it now carries its sign, so no bare `25` is left for a later reading (`$ 25 per
       seat` is the price `$25`, and not also 25 seats).
    3. `_NUMBER_TOKEN` over the text of step 2. A token with `$ € £ ¥ % . ,` is a value.
    4. Counts with units (rule (a), `_is_value`): a bare integer that step 3 leaves out is a
       value when a unit follows it in the text of step 2 (`500 credits`, `50-seat`, `5 active
       users`), so it never sees a number that step 2 read as a price. Any other bare integer
       (`2025`, `Pro 2`, `24/7`, `GPT-4`) is left out (module docstring).
    5. Each value in its signed reading (`_signed_reading`: `25$` -> `$25`, `$.99` -> `$0.99`),
       the spelling the miss note shows. A count has no sign and is named as written (`500`).
    """
    signed = _signed_prices(normalize(text))
    tokens = _NUMBER_TOKEN.finditer(signed)
    return [_signed_reading(tok.group()) for tok in tokens if _is_value(signed, tok)]


def _is_value(text: str, token: re.Match[str]) -> bool:
    """True iff a `_NUMBER_TOKEN` match in the claim `text` is a value the quote must back.

    It is when it carries `$ € £ ¥ % . ,` (`$20`, `20%`, `19.5`, `2,500`), or when it is a bare
    integer that a unit follows (`_COUNT_UNIT`, rule (a)): `500 credits` is checked, `2025` is not.
    A count compares its value only (brief assumption 2), so `500 seats` backs `500 credits`.
    """
    if _VALUE_MARK.search(token.group()):
        return True
    return _COUNT_UNIT.match(text, token.end()) is not None


def _covers_zero(quote: str, free: re.Match[str]) -> bool:
    """True iff this `_FREE` match in the normalized `quote` stands for a zero price (rule (b)).

    It does not when `not`, `no`, `never`, `isn't`, `isnt`, `aren't`, `arent`, `without` or
    `non` is one of the two words before it (`not free`, `no free plan`, `not really free`,
    `non-free`), or when `trial` or `trials` directly follows it (`free trial`). A negation three
    words before does not count (`no card required, free`), nor one after (`free and no ads`).
    """
    before = _WORD.findall(quote, 0, free.start())[-_NEGATION_WINDOW:]
    if _NEGATIONS.intersection(before):
        return False
    return _TRIAL.match(quote, free.end()) is None


def _quote_values(quote: str) -> list[str]:
    """The claim rule's values of the normalized `quote`.

    Its number tokens; the signed readings of its unsigned prices, which are the number tokens of
    `_signed_prices(quote)`; and a zero price when it says `free`. For the claim rule only:
    `_match_quote` reads the quote as written. The signed readings are added to the quote's own
    tokens, not put in their place (brief assumption 4), so a quote `25 dollars` backs a claim's
    `$25` and a claim's count `25 seats`. A claim's `$0` or `$0.00` is the quote's "free" (live
    run run-6a5fe9499c4d). The word must stand alone, so "freedom" does not count, and one `free`
    that is neither negated nor a trial is enough (`_covers_zero`, rule (b)): `not free` and
    `free trial` add no zero price, while `free, and pro has a free trial` does.
    """
    tokens = [*_NUMBER_TOKEN.findall(quote), *_NUMBER_TOKEN.findall(_signed_prices(quote))]
    says_free = any(_covers_zero(quote, free) for free in _FREE.finditer(quote))
    return [*tokens, *_ZERO_PRICES] if says_free else tokens


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


def _number_mismatches(
    quote: str, body: str, spans: Sequence[tuple[int, int]], window: tuple[int, int]
) -> list[tuple[str, str]]:
    """`(quote token, page tokens there)` for each quote number the page lacks at that place.

    `window` is the alignment's `dest_*` span of `body`. Each quote number token is compared with
    the page number tokens aligned to it (read whole by `_numbers_at`), so a quote that swaps,
    repeats or shifts the page's prices is a miss even though every price is in the window.
    Pairs are in quote order and deduplicated; the page side is `no number` when there is none.
    """
    offset, stop = window
    char_map = _char_map(quote, body[offset:stop])
    pairs: list[tuple[str, str]] = []
    for match in _NUMBER_TOKEN.finditer(quote):
        lo, hi = _aligned_range(char_map, *match.span(), stop - offset)
        there = _numbers_at(body, spans, offset + lo, offset + hi)
        if _missing_numbers([match.group()], there):
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
