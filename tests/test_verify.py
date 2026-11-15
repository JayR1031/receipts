"""Lane L2: `receipts.verify` is pure and rule-based; every case here runs against invented text.

No real companies, people, sites or quotes: every URL ends in `.example`.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from receipts.contracts import Claim, FetchedPage, QuoteReceipt, SearchReceipt, SearchResult
from receipts.fakes import data
from receipts.verify import (
    DROPPED_PREFIX,
    FUZZY_THRESHOLD,
    NOTE_FETCH_FAILED,
    NOTE_QUERY_NOT_LOGGED,
    NOTE_URL_NOT_FETCHED,
    dropped_reason,
    is_dropped,
    normalize,
    verify_all,
    verify_claim,
)

T0 = data.T0
RIVAL_URL = data.RIVAL_URL
MD_URL = "https://markdown-corp.example/plans"
MD_PAGE = (
    "# Plans\n\n"
    "- The **Team** plan is [14 dollars](https://markdown-corp.example/plans#team) per seat "
    "per month — billed yearly.\n"
    "- Cancel “any time”.\n"
    "```\ncode block\n```\n"
)


def quote_claim(url: str, quote: str) -> Claim:
    return Claim(
        domain="pricing",
        about="rival",
        text="invented claim",
        receipt=QuoteReceipt(url=url, quote=quote),
    )


def search_claim(query: str, rank: int, url: str, ts: datetime = T0) -> Claim:
    return Claim(
        domain="pricing",
        about="rival",
        text="invented claim",
        receipt=SearchReceipt(query=query, rank=rank, url=url, ts=ts),
    )


# --- normalize ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("**bold** and *em* and __under__ and _em_", "bold and em and under and em"),
        ("[link text](https://x.example/a) tail", "link text tail"),
        ("![alt text](https://x.example/i.png)", "alt text"),
        ("[![Logo alt](https://x.example/l.png)](https://x.example/) tail", "logo alt tail"),
        ("# Heading\n## Sub\ntext", "heading sub text"),
        ("- one\n* two\n+ three\n1. four", "one two three four"),
        ("```py\nx = 1\n```\nand `inline`", "py x = 1 and inline"),
        ("Mixed  CASE\t\twith\n\nspace", "mixed case with space"),
        ("‘single’ “double”", "'single' \"double\""),
        ("en – dash em — dash", "en - dash em - dash"),
        ("snake_case stays", "snake_case stays"),
        ("Save 20 % or 20 Percent or 20%", "save 20% or 20% or 20%"),
        ("20 percentage points, 100 % sure, % off", "20 percentage points, 100% sure, % off"),
    ],
)
def test_normalize_rules(raw: str, expected: str) -> None:
    assert normalize(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        MD_PAGE,
        data.RIVAL_PAGE,
        "**a** [b](c) — ‘d’",
        "[![Logo alt](https://x.example/l.png)](https://x.example/)",
        "Save 20 percent, or 20 % on annual",
        "",
        "   ",
    ],
)
def test_normalize_idempotent(raw: str) -> None:
    once = normalize(raw)
    assert normalize(once) == once


# --- quote receipts -----------------------------------------------------------------


def test_exact_quote_verifies(
    sample_claims: list[Claim], sample_pages: dict[str, FetchedPage]
) -> None:
    claim = sample_claims[0].model_copy(update={"verified": False, "verify_method": None})
    out = verify_claim(claim, sample_pages, [])
    assert out.verified is True
    assert out.verify_method == "quote_exact"
    assert out.verify_note is None
    assert not is_dropped(out)


def test_dash_and_whitespace_differences_still_exact(sample_pages: dict[str, FetchedPage]) -> None:
    # Page text: "The Team plan is 14 dollars per seat per month, billed yearly."
    claim = quote_claim(RIVAL_URL, "Team  plan is 14 dollars per\nseat per month, billed yearly")
    out = verify_claim(claim, sample_pages, [])
    assert (out.verified, out.verify_method) == (True, "quote_exact")


def test_fuzzy_quote_at_or_above_threshold(sample_pages: dict[str, FetchedPage]) -> None:
    claim = quote_claim(RIVAL_URL, "the team plan costs 14 dollars per seat per month")
    out = verify_claim(claim, sample_pages, [])
    assert out.verified is True
    assert out.verify_method == "quote_fuzzy"
    assert out.verify_note is not None
    assert "partial_ratio=9" in out.verify_note  # score 91.8 on this pair
    assert not is_dropped(out)


def test_missed_quote_below_threshold(
    sample_claims: list[Claim], sample_pages: dict[str, FetchedPage]
) -> None:
    out = verify_claim(sample_claims[2], sample_pages, [])  # "free forever" is not on the page
    assert out.verified is False
    assert out.verify_method is None
    assert out.verify_note is not None
    assert "partial_ratio=4" in out.verify_note  # score 41.7
    assert f"< {FUZZY_THRESHOLD}" in out.verify_note
    assert not is_dropped(out)


def test_short_page_does_not_verify_a_longer_quote() -> None:
    # partial_ratio slides the *shorter* string along the longer one; a 7-char page must not
    # "verify" a 42-char quote just because the page text appears inside the quote.
    url = "https://short.example/"
    pages = {url: FetchedPage(url=url, text="Pricing", fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "Our pricing is free forever for every team"), pages, [])
    assert out.verified is False
    assert out.verify_method is None
    assert out.verify_note is not None and out.verify_note.startswith("quote not found on page")
    assert not is_dropped(out)


def test_page_that_is_a_substring_of_the_quote_is_a_miss() -> None:
    # The whole page is the quote's tail: the tail scores 100, but the aligned span covers only
    # part of the quote, so the quote is not on the page.
    url = "https://tail.example/"
    pages = {
        url: FetchedPage(url=url, text="every team gets unlimited seats", fetched_at=T0, ok=True)
    }
    quote = "Zeta charges nothing: every team gets unlimited seats"
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note is not None and "cover" in out.verify_note


def test_quote_missing_one_word_still_fuzzy_verifies() -> None:
    # Regression guard for the legitimate fuzzy case: the page has the quote minus one word.
    url = "https://one-word.example/"
    text = "The Team plan is 14 dollars per seat per month, billed yearly. Cancel any time."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    quote = "The Team plan is 14 dollars per seat per month, billed yearly or monthly."
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method) == (True, "quote_fuzzy")


def test_fuzzy_quote_with_a_changed_number_is_a_miss() -> None:
    # Deliberate tightening of the spec's partial_ratio >= 90 rule: a one-digit price change
    # scores 97.4, but a battlecard must never show a wrong number as verified.
    url = "https://numbers.example/"
    text = "Basic is 14 dollars per seat per month, billed yearly."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "Basic is 19 dollars per seat per month"), pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note is not None
    assert out.verify_note.startswith("quote not found on page")
    assert "19" in out.verify_note
    assert not is_dropped(out)


def test_fuzzy_quote_with_matching_numbers_still_verifies() -> None:
    url = "https://numbers.example/"
    text = "Basic is 14 dollars per seat per month, billed yearly."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    exact = verify_claim(quote_claim(url, "Basic is 14 dollars per seat"), pages, [])
    assert (exact.verified, exact.verify_method) == (True, "quote_exact")
    fuzzy = verify_claim(quote_claim(url, "Basic costs 14 dollars per seat per month"), pages, [])
    assert (fuzzy.verified, fuzzy.verify_method) == (True, "quote_fuzzy")


@pytest.mark.parametrize(
    ("text", "quote", "missing", "page_has"),
    [
        ("Churn fell to 19 per month", "Churn fell to 19% per month", "19%", "19"),
        (
            "Basic is $19.49 per seat per month, billed yearly. Enterprise is $99 per seat.",
            "Basic is $19.99 per seat per month, billed yearly",
            "$19.99",
            "$19.49",
        ),
        ("Trials convert at 10% and 19 teams signed up", "Trials convert at 19%", "19%", "10%"),
        ("Basic is \u20ac19 per seat", "Basic is $19 per seat", "$19", "\u20ac19"),
    ],
    ids=["percent-sign", "decimal-price-digit-runs-present", "percent-vs-bare-19", "currency-sign"],
)
def test_fuzzy_quote_number_token_must_match_verbatim(
    text: str, quote: str, missing: str, page_has: str
) -> None:
    # Owner ruling 2026-11-15: every number token (digits with currency sign, decimal point
    # or %) in a fuzzy quote must be on the page verbatim; bare digit runs are not enough.
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note is not None
    assert f"numbers differ (quote has {missing}; page has {page_has} there;" in out.verify_note
    assert not is_dropped(out)


@pytest.mark.parametrize(
    ("text", "quote", "missing", "page_has"),
    [
        ("Basic is $199 per seat per month.", "Basic is $19", "$19", "$199"),
        ("Basic is $119 per seat per month.", "19 per seat per month", "19", "$119"),
        ("Basic is $19.99 per seat per month.", "Basic is $19.9", "$19.9", "$19.99"),
        ("Basic is $19.99 per seat per month.", "Basic is $19.", "$19", "$19.99"),
        # The cut-off token also appears elsewhere on the page: only the match position counts.
        ("Basic is $19.99 per seat. Pro is $19.", "Basic is $19.", "$19", "$19.99"),
        ("Basic is $19.99 per seat, up to 99 seats.", "99 per seat", "99", "$19.99"),
        ("Save 20% on annual plans. Teams of 20 get support.", "Save 20", "20", "20%"),
    ],
    ids=[
        "digits-after-quote-end",
        "digits-before-quote-start",
        "decimal-cut",
        "trailing-dot",
        "trailing-dot-19-elsewhere",
        "decimal-before-quote-start-99-elsewhere",
        "percent-after-quote-end-20-elsewhere",
    ],
)
def test_exact_substring_cutting_a_number_is_a_miss(
    text: str, quote: str, missing: str, page_has: str
) -> None:
    # GitHub issue #33 (L2 judge LOW 7): a quote that ends or starts inside a page number is a
    # plain substring, so the exact path needs the same whole-token number check as fuzzy. The
    # note names the page's whole token at the match.
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note is not None
    assert f"numbers differ (quote has {missing}; page has {page_has} there;" in out.verify_note
    assert not is_dropped(out)


JUDGE_199_PAGE = "Pro yearly: $199. Pro monthly: $19."


@pytest.mark.parametrize(
    ("quote", "verified", "method", "note"),
    [
        (
            "Pro yearly: $19",
            False,
            None,
            "quote not found on page: numbers differ (quote has $19; page has $199 there; "
            "partial_ratio=100.0)",
        ),
        ("Pro monthly: $19", True, "quote_exact", None),
    ],
    ids=["cut-199-with-19-elsewhere", "whole-19"],
)
def test_number_cut_at_the_match_is_a_miss_even_when_the_token_is_elsewhere(
    quote: str, verified: bool, method: str | None, note: str | None
) -> None:
    # gh-33 judge HIGH #1: a pricing page that lists $199 yearly and $19 monthly. "$19" is on the
    # page, but not where "Pro yearly: $19" matches; there the page says "$199", and the note
    # must not claim "$19 not on page".
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text=JUDGE_199_PAGE, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method, out.verify_note) == (verified, method, note)


def test_exact_match_accepts_a_later_occurrence_with_whole_numbers() -> None:
    # The first occurrence of the quote cuts "$199"; the second is followed by a space, so the
    # quote is on the page as written.
    url = "https://tokens.example/"
    text = "Basic: $199 per seat yearly. Basic: $19 per seat monthly."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "Basic: $19"), pages, [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


def test_fuzzy_number_check_reads_the_page_text_at_the_match() -> None:
    # Not a substring (the page says "$199 billed"), so this is the fuzzy path. "$19" is on the
    # page in the monthly line, but the matched page text holds "$199".
    url = "https://tokens.example/"
    text = "Pro yearly: $199 billed. Pro monthly: $19 billed."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "Pro yearly: $19 billed"), pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note is not None and out.verify_note.startswith(
        "quote not found on page: numbers differ (quote has $19; page has $199 there;"
    )


TEAM_PAGE = (
    "Starter plan $8 per seat billed monthly with email support. Team plan $12 per seat billed "
    "monthly with chat support. Business plan $15 per seat billed monthly."
)
PRO_PAGE = (
    "Pro is billed monthly at $19 per month for every seat on the team, or $199 per year for "
    "every seat."
)


@pytest.mark.parametrize(
    ("text", "quote"),
    [
        (JUDGE_199_PAGE, "Pro yearly: $19. Pro monthly: $199."),
        (JUDGE_199_PAGE, "Pro yearly: $19. Pro monthly: $19."),
        ("Pro: $19/month or $199/year.", "Pro: $199/month or $19/year"),
        (
            "Starter $8 per seat, Team $12 per seat, Business $15 per seat.",
            "Starter $8 per seat, Team $15 per seat, Business $12 per seat",
        ),
        (
            TEAM_PAGE,
            "Starter plan per seat billed monthly with email support. Team plan $15 per seat "
            "billed monthly with chat support. Business plan per seat billed monthly",
        ),
    ],
    ids=[
        "swapped",
        "repeated",
        "monthly-yearly-swapped",
        "table-row-swapped",
        "price-left-out-then-another-plans-price",
    ],
)
def test_fuzzy_quote_number_must_match_the_page_number_at_the_same_place(
    text: str, quote: str
) -> None:
    # gh-33 round-2 judge HIGH #1: the window check compared sets, so a quote that swaps or
    # repeats the page's prices, or leaves one out so the next lines up with another plan's,
    # still verified. Each quote number is now compared with the page number aligned to it.
    # The last id is a case an in-order (subsequence) check would still pass: the quote's one
    # price, $15, is the window's last price, but the page has $12 where the quote puts it.
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note is not None
    assert out.verify_note.startswith("quote not found on page: numbers differ (quote has ")
    assert not is_dropped(out)


@pytest.mark.parametrize(
    ("quote", "note"),
    [
        (
            "Pro yearly: $19. Pro monthly: $199.",
            "quote not found on page: numbers differ (quote has $19, $199; page has $199, $19 "
            "there; partial_ratio=97.1)",
        ),
        (
            "Pro yearly: $19. Pro monthly: $19.",
            "quote not found on page: numbers differ (quote has $19; page has $199 there; "
            "partial_ratio=97.1)",
        ),
    ],
    ids=["swapped", "repeated"],
)
def test_numbers_differ_note_pairs_each_quote_number_with_the_page_number_there(
    quote: str, note: str
) -> None:
    # gh-33 round-2 judge LOW #3: the note's page side is what the page says at each differing
    # quote number, in quote order. "repeated" has a matching $19 at the second place, and the
    # note leaves it out.
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text=JUDGE_199_PAGE, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method, out.verify_note) == (False, None, note)


@pytest.mark.parametrize(
    ("text", "quote", "note"),
    [
        (
            "Basic is 14 per seat per month, billed yearly.",
            "Basic is 9 per seat per month, billed yearly",
            "quote not found on page: numbers differ (quote has 9; page has 14 there; "
            "partial_ratio=95.5)",
        ),
        (
            "Basic: $199 per seat yearly. Team: $199 per seat yearly.",
            "Basic: $19 per seat yearly. Team: $19 per seat yearly",
            "quote not found on page: numbers differ (quote has $19; page has $199 there; "
            "partial_ratio=96.2)",
        ),
    ],
    ids=["no-character-of-the-number-matched", "same-difference-twice"],
)
def test_numbers_differ_note_reads_the_gap_and_lists_a_difference_once(
    text: str, quote: str, note: str
) -> None:
    # "9" shares no character with the page's "14", so the alignment matches none of it; the
    # page side is read from the gap between its matched neighbours. A difference that repeats
    # at two places is listed once.
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method, out.verify_note) == (False, None, note)


@pytest.mark.parametrize(
    ("text", "quote"),
    [
        (JUDGE_199_PAGE, "Pro yearly: $199, Pro monthly: $19"),
        (
            TEAM_PAGE,
            "Starter plan per seat billed monthly with email support. Team plan $12 per seat "
            "billed monthly with chat support. Business plan per seat billed monthly",
        ),
        (
            PRO_PAGE,
            "Pro is billed monthly at per month for every seat on the team, or $199 per year for "
            "every seat",
        ),
    ],
    ids=["two-prices-in-place", "price-left-out-the-rest-in-place", "first-price-left-out"],
)
def test_fuzzy_quote_whose_numbers_sit_where_the_page_has_them_verifies(
    text: str, quote: str
) -> None:
    # Regression guard for the aligned check: a quote may leave a page number out; the numbers
    # it does carry verify when each sits where the page has it.
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, quote), pages, [])
    assert (out.verified, out.verify_method) == (True, "quote_fuzzy")


def test_quote_that_drops_the_page_currency_sign_is_a_miss_with_an_accurate_note() -> None:
    # gh-33 judge MEDIUM #4. The page says "$20"; the quote says "20". The currency sign is part
    # of the number token (owner ruling 2026-11-15, `currency-sign` case above), so "20" cuts the
    # page's "$20" and the quote is a miss. The note says what the page has, not "20 not on page".
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text="Pro costs $20 per month.", fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "20 per month"), pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == (
        "quote not found on page: numbers differ (quote has 20; page has $20 there; "
        "partial_ratio=100.0)"
    )
    assert not is_dropped(out)


def test_numbers_differ_note_says_when_the_page_has_no_number_at_the_match() -> None:
    url = "https://tokens.example/"
    text = "Basic is free per seat per month, billed yearly."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "Basic is $9 per seat per month, billed yearly"), pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note is not None and out.verify_note.startswith(
        "quote not found on page: numbers differ (quote has $9; page has no number there;"
    )


def test_fuzzy_quote_with_matching_number_tokens_verifies() -> None:
    url = "https://tokens.example/"
    text = "Basic is $19.99 per seat per month, billed yearly, with audit logs."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(
        quote_claim(url, "Basic is $19.99 per seat per month billed yearly"), pages, []
    )
    assert (out.verified, out.verify_method) == (True, "quote_fuzzy")


def test_fuzzy_quote_price_per_month_verifies() -> None:
    url = "https://tokens.example/"
    text = "Basic is $19.99 per month, billed yearly, with audit logs."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "Basic is $19.99 per month billed yearly"), pages, [])
    assert (out.verified, out.verify_method) == (True, "quote_fuzzy")


def test_thousands_comma_equals_plain_number() -> None:
    url = "https://tokens.example/"
    text = "The team plan includes 1000 seats and audit logs."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "1,000 seats"), pages, [])
    assert out.verified is True
    assert out.verify_method in ("quote_exact", "quote_fuzzy")
    assert out.verify_note is None or "numbers differ" not in out.verify_note


def test_thousands_comma_fuzzy_verifies() -> None:
    url = "https://tokens.example/"
    text = "The team plan includes 1000 seats and audit logs."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    quote = quote_claim(url, "The team plan includes 1,000 seats and audit log")
    out = verify_claim(quote, pages, [])
    assert (out.verified, out.verify_method) == (True, "quote_fuzzy")


def test_decimal_comma_is_not_a_thousands_separator() -> None:
    url = "https://tokens.example/"
    text = "Basic is 1999 per seat per month, billed yearly, with audit logs."
    pages = {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}
    quote = quote_claim(url, "Basic is 19,99 per seat per month billed yearly")
    out = verify_claim(quote, pages, [])
    assert out.verified is False
    assert out.verify_note is not None
    assert "19,99" in out.verify_note


def test_yen_sign_must_match() -> None:
    url = "https://tokens.example/"
    pages = {url: FetchedPage(url=url, text="$1900", fetched_at=T0, ok=True)}
    out = verify_claim(quote_claim(url, "\u00a51900"), pages, [])
    assert out.verified is False


def test_markdown_wrapped_page_still_matches() -> None:
    pages = {MD_URL: FetchedPage(url=MD_URL, text=MD_PAGE, fetched_at=T0, ok=True)}
    claim = quote_claim(MD_URL, "The Team plan is 14 dollars per seat per month - billed yearly.")
    out = verify_claim(claim, pages, [])
    assert (out.verified, out.verify_method) == (True, "quote_exact")


def test_fetch_failed_page_is_not_false() -> None:
    url = "https://down.example/pricing"
    pages = {url: FetchedPage(url=url, text="", fetched_at=T0, ok=False)}
    out = verify_claim(quote_claim(url, "anything"), pages, [])
    assert out.verified is False
    assert out.verify_method is None
    assert out.verify_note == NOTE_FETCH_FAILED
    assert not is_dropped(out)


def test_url_not_fetched_this_run_is_dropped(sample_pages: dict[str, FetchedPage]) -> None:
    claim = quote_claim("https://never-fetched.example/x", "Plans start at 9 dollars per seat")
    out = verify_claim(claim, sample_pages, [])
    assert out.verified is False
    assert out.verify_method is None
    assert out.verify_note == NOTE_URL_NOT_FETCHED
    assert out.verify_note is not None and out.verify_note.startswith(DROPPED_PREFIX)
    assert is_dropped(out)
    assert dropped_reason(out) == "url not fetched this run"


# --- search receipts ----------------------------------------------------------------


def test_search_receipt_matching_logged_row(
    sample_claims: list[Claim], sample_search_results: list[SearchResult]
) -> None:
    claim = sample_claims[1].model_copy(update={"verified": False, "verify_method": None})
    out = verify_claim(claim, {}, sample_search_results)
    assert (out.verified, out.verify_method, out.verify_note) == (True, "search_log", None)


def test_search_receipt_unlogged_query_is_dropped(
    sample_search_results: list[SearchResult],
) -> None:
    out = verify_claim(search_claim("never searched", 1, RIVAL_URL), {}, sample_search_results)
    assert out.verified is False
    assert out.verify_method is None
    assert out.verify_note == NOTE_QUERY_NOT_LOGGED
    assert is_dropped(out)
    assert dropped_reason(out) == "search query not logged this run"


def test_search_receipt_logged_query_wrong_url_or_rank_is_a_miss(
    sample_search_results: list[SearchResult],
) -> None:
    wrong_url = verify_claim(
        search_claim("zeta gadgets pricing", 1, "https://other.example/"), {}, sample_search_results
    )
    wrong_rank = verify_claim(
        search_claim("zeta gadgets pricing", 2, RIVAL_URL), {}, sample_search_results
    )
    for out in (wrong_url, wrong_rank):
        assert (out.verified, out.verify_method) == (False, None)
        assert out.verify_note is not None and "no logged row" in out.verify_note
        assert not is_dropped(out)


# --- purity, immutability, round-trip --------------------------------------------------


def test_verify_claim_does_not_mutate_input(
    sample_claims: list[Claim], sample_pages: dict[str, FetchedPage]
) -> None:
    claim = sample_claims[2]
    before = claim.model_dump()
    pages_before = dict(sample_pages)
    out = verify_claim(claim, sample_pages, [])
    assert claim.model_dump() == before
    assert sample_pages == pages_before
    assert out is not claim


def test_result_round_trips_through_pydantic(
    sample_claims: list[Claim], sample_pages: dict[str, FetchedPage]
) -> None:
    for claim in sample_claims:
        out = verify_claim(claim, sample_pages, [])
        assert Claim.model_validate_json(out.model_dump_json()) == out
        assert Claim.model_validate(out.model_dump()) == out


def test_verify_all_preserves_order_and_length(
    sample_claims: list[Claim],
    sample_pages: dict[str, FetchedPage],
    sample_search_results: list[SearchResult],
) -> None:
    outs = verify_all(sample_claims, sample_pages, sample_search_results)
    assert isinstance(outs, tuple)
    assert [o.text for o in outs] == [c.text for c in sample_claims]
    assert [o.verified for o in outs] == [True, True, False]
    assert [o.verify_method for o in outs] == ["quote_exact", "search_log", None]


def test_is_dropped_requires_the_prefix_not_just_unverified() -> None:
    plain = quote_claim(RIVAL_URL, "x")
    assert not is_dropped(plain)
    assert dropped_reason(plain) is None
    assert not is_dropped(plain.model_copy(update={"verify_note": NOTE_FETCH_FAILED}))
    noted = plain.model_copy(update={"verify_note": f"{DROPPED_PREFIX}custom reason"})
    assert is_dropped(noted) and dropped_reason(noted) == "custom reason"
    # A verified claim is never dropped, whatever its note says.
    odd = noted.model_copy(update={"verified": True, "verify_method": "quote_exact"})
    assert not is_dropped(odd)
