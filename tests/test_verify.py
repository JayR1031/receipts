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
