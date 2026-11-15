"""Lane L2, GitHub issue #33: every number in a quote-receipt claim's text must be in its quote.

The two regression cases use the claim and quote text as reported for the first live run
(run-0e7ff2b1bb05) in GitHub issue #33 and its task brief; the run's own record is not in this
repository. Both were reported verified although the quote does not carry the claim's prices.
They name products, not people. The pages around those quotes are invented for
the test, and every URL ends in `.example`.
"""

from __future__ import annotations

import pytest

from receipts.contracts import Claim, FetchedPage, QuoteReceipt, SearchResult
from receipts.fakes import data
from receipts.verify import (
    NOTE_FETCH_FAILED,
    NOTE_URL_NOT_FETCHED,
    is_dropped,
    verify_claim,
)

T0 = data.T0


def page(url: str, text: str) -> dict[str, FetchedPage]:
    return {url: FetchedPage(url=url, text=text, fetched_at=T0, ok=True)}


def claim_with_quote(text: str, url: str, quote: str) -> Claim:
    return Claim(
        domain="pricing", about="rival", text=text, receipt=QuoteReceipt(url=url, quote=quote)
    )


# --- the live-run regressions ---------------------------------------------------------


def test_live_run_prices_absent_from_the_quote_are_not_verified() -> None:
    # The page lists both prices, but not inside the quote: the rule is claim against quote.
    url = "https://pricing-one.example/plans"
    text = (
        "Max is $180/month billed annually or $200 billed monthly. "
        "Pro with the biggest bucket — 18,000 credits a month."
    )
    claim = claim_with_quote(
        "Mel Max: $180/month billed annually ($200 monthly), 18,000 credits per month.",
        url,
        "Pro with the biggest bucket — 18,000 credits a month.",
    )
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == "claim numbers not in quote: $180, $200"
    assert not is_dropped(out)


def test_live_run_plan_price_absent_from_the_quote_is_not_verified() -> None:
    url = "https://pricing-two.example/plans"
    text = "Build plan. $20 of agent usage included each month at API rates. Cancel any time."
    claim = claim_with_quote(
        "Warp Build is $18/month on the annual plan and includes $20 of agent usage per month "
        "at API rates",
        url,
        "$20 of agent usage included each month at API rates",
    )
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == "claim numbers not in quote: $18"
    assert not is_dropped(out)


# --- the rule on both match paths -------------------------------------------------------


def test_fuzzy_match_also_needs_the_claim_numbers_in_the_quote() -> None:
    # The quote fuzzy-matches the page (exact substring fails on the missing comma), so this
    # case proves the claim check runs after a fuzzy pass too, not only after an exact one.
    url = "https://tokens.example/"
    text = "Basic is $19.99 per seat per month, billed yearly, with audit logs."
    quote = "Basic is $19.99 per seat per month billed yearly"
    claim = claim_with_quote("Basic is $19.99 per seat, or $24.99 billed monthly.", url, quote)
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == "claim numbers not in quote: $24.99"


def test_claim_whose_numbers_are_all_in_the_quote_stays_verified() -> None:
    url = "https://tokens.example/"
    text = "Basic is $19.99 per seat per month, billed yearly, with 30 days of history."
    claim = claim_with_quote(
        "Basic costs $19.99 per seat and keeps 30 days of history.",
        url,
        "Basic is $19.99 per seat per month, billed yearly, with 30 days of history.",
    )
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


def test_fuzzy_claim_whose_numbers_are_all_in_the_quote_keeps_its_fuzzy_note() -> None:
    url = "https://tokens.example/"
    text = "Basic is $19.99 per seat per month, billed yearly, with audit logs."
    claim = claim_with_quote(
        "Basic is $19.99 per seat.", url, "Basic is $19.99 per seat per month billed yearly"
    )
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method) == (True, "quote_fuzzy")
    assert out.verify_note is not None and out.verify_note.startswith("fuzzy match:")


def test_claim_without_numbers_is_unaffected() -> None:
    # The quote carries numbers the claim does not repeat; only claim -> quote is checked.
    claim = claim_with_quote(
        "Zeta bills the Team plan yearly.",
        data.RIVAL_URL,
        "The Team plan is 14 dollars per seat per month, billed yearly.",
    )
    out = verify_claim(claim, data.sample_pages(), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


@pytest.mark.parametrize(
    ("claim_text", "quote"),
    [
        ("The team plan includes 1,000 seats.", "includes 1000 seats"),
        ("The team plan includes 1000 seats.", "includes 1,000 seats"),
    ],
    ids=["comma-in-claim", "comma-in-quote"],
)
def test_thousands_comma_in_claim_or_quote_still_verifies(claim_text: str, quote: str) -> None:
    url = "https://tokens.example/"
    text = "The team plan includes 1000 seats and audit logs."
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, text), [])
    assert out.verified is True
    assert out.verify_method in ("quote_exact", "quote_fuzzy")


def test_claim_text_is_normalized_before_its_numbers_are_read() -> None:
    # Same `normalize()` as quote and page: a markdown link keeps its text and loses its URL, so
    # the `2` in `/v2/` is not a claim number.
    url = "https://tokens.example/"
    text = "Basic is $19.99 per seat per month, billed yearly."
    claim = claim_with_quote(
        "Basic is [$19.99 per seat](https://tokens.example/v2/plans).",
        url,
        "Basic is $19.99 per seat per month",
    )
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


# --- precedence and scope ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("pages", "expected_note"),
    [
        ({}, NOTE_URL_NOT_FETCHED),
        (
            {
                "https://gone.example/": FetchedPage(
                    url="https://gone.example/", text="", fetched_at=T0, ok=False
                )
            },
            NOTE_FETCH_FAILED,
        ),
        (page("https://gone.example/", "Nothing about prices here."), None),
    ],
    ids=["url-not-fetched-stays-dropped", "fetch-failed-stays-fetch-failed", "quote-miss"],
)
def test_page_check_outcome_wins_over_the_claim_number_check(
    pages: dict[str, FetchedPage], expected_note: str | None
) -> None:
    claim = claim_with_quote("Pro is $49 a month.", "https://gone.example/", "Pro is $29 a month.")
    out = verify_claim(claim, pages, [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note is not None
    if expected_note is None:
        assert out.verify_note.startswith("quote not found on page")
    else:
        assert out.verify_note == expected_note


def test_search_receipt_claims_are_out_of_scope(
    sample_claims: list[Claim], sample_search_results: list[SearchResult]
) -> None:
    # sample_claims[1] says "14 dollars" and has only a search receipt: no quote to check against.
    claim = sample_claims[1].model_copy(update={"verified": False, "verify_method": None})
    out = verify_claim(claim, {}, sample_search_results)
    assert (out.verified, out.verify_method, out.verify_note) == (True, "search_log", None)
