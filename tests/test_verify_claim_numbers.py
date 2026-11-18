"""Lane L2, GitHub issue #33: every value token in a quote-receipt claim must be in its quote.

A value token is a number with a currency sign, a `%`, a decimal part or a thousands separator
(`$20`, `20%`, `19.5`, `2,500`); bare integers are not checked (`rules.py` module docstring).

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
    # the `2.1` in `/v2.1/` (a value token: it has a decimal part) is not a claim number.
    url = "https://tokens.example/"
    text = "Basic is $19.99 per seat per month, billed yearly."
    claim = claim_with_quote(
        "Basic is [$19.99 per seat](https://tokens.example/v2.1/plans).",
        url,
        "Basic is $19.99 per seat per month",
    )
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


def test_claim_number_note_is_sorted_and_deduplicated() -> None:
    # gh-33 judge LOW #5: "$200" twice and "$180" after it; the note lists each once, sorted.
    url = "https://tokens.example/"
    claim = claim_with_quote(
        "Max is $200 a month, $180 billed yearly, or $200 with support.",
        url,
        "Max includes priority support",
    )
    out = verify_claim(claim, page(url, "Max includes priority support and audit logs."), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == "claim numbers not in quote: $180, $200"


# --- which claim numbers the rule reads: value tokens only (gh-33 judge MEDIUM #3) -------------


@pytest.mark.parametrize(
    ("claim_text", "quote", "text"),
    [
        ("As of 2025, Pro costs $20/month.", "Pro costs $20/month", "Pro costs $20/month."),
        ("Pro 2 costs $20/month.", "$20/month", "Pro 2: $20/month."),
        ("Pro includes GPT-4 for $20/month.", "$20/month", "Pro: $20/month with all models."),
        ("Pro adds 24/7 support for $20/month.", "$20/month", "Pro: $20/month."),
    ],
    ids=["year", "plan-name", "model-name", "24-7"],
)
def test_bare_integers_in_the_claim_are_not_checked(claim_text: str, quote: str, text: str) -> None:
    # A bare integer (no currency sign, %, decimal part or thousands separator) is a year, a plan
    # or model name, or "24/7" far more often than a price; the claim rule reads value tokens only.
    url = "https://tokens.example/"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, text), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


@pytest.mark.parametrize(
    ("claim_text", "missing"),
    [
        ("Pro costs $24/month.", "$24"),
        ("Pro costs €24/month.", "€24"),
        ("Pro costs £24/month.", "£24"),
        ("Pro costs ¥24/month.", "¥24"),
        ("Annual billing saves 25%.", "25%"),
        ("Pro includes 19.5 hours of compute.", "19.5"),
        ("Pro includes 2,500 credits.", "2,500"),
    ],
    ids=["dollar", "euro", "pound", "yen", "percent", "decimal", "thousands-separator"],
)
def test_value_tokens_in_the_claim_are_checked(claim_text: str, missing: str) -> None:
    url = "https://tokens.example/"
    text = "Pro costs $20/month and includes 1000 credits."
    claim = claim_with_quote(claim_text, url, "Pro costs $20/month")
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == f"claim numbers not in quote: {missing}"


# --- the same value written differently (gh-33 judge MEDIUM #2) ------------------------------


@pytest.mark.parametrize(
    ("claim_text", "quote", "text"),
    [
        ("Pro costs $20.00 per month.", "Pro costs $20 per month", "Pro costs $20 per month."),
        ("Pro costs $20.0 per month.", "Pro costs $20 per month", "Pro costs $20 per month."),
        ("Pro costs $20 per month.", "Pro costs $20.00 per month", "Pro costs $20.00 per month."),
        ("Save 20% on annual.", "Save 20 percent yearly", "Save 20 percent yearly."),
        ("Save 20% on annual.", "Save 20 % yearly", "Save 20 % yearly."),
        ("Save 20 percent on annual.", "Save 20% yearly", "Save 20% yearly."),
        ("Save 20.0% on annual.", "Save 20% yearly", "Save 20% yearly."),
    ],
    ids=[
        "zero-cents-in-claim",
        "zero-tenths-in-claim",
        "zero-cents-in-quote",
        "percent-word-in-quote",
        "percent-space-in-quote",
        "percent-word-in-claim",
        "zero-tenths-percent-in-claim",
    ],
)
def test_same_value_written_differently_verifies(claim_text: str, quote: str, text: str) -> None:
    url = "https://tokens.example/"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, text), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


def test_percent_word_in_the_claim_is_a_value_token() -> None:
    # "25 percent" normalizes to "25%", so it is checked; read as a bare "25" it would be skipped
    # and a wrong percentage would verify.
    url = "https://tokens.example/"
    claim = claim_with_quote(
        "Annual billing saves 25 percent.", url, "Save 20% when billed annually"
    )
    out = verify_claim(claim, page(url, "Save 20% when billed annually."), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == "claim numbers not in quote: 25%"


@pytest.mark.parametrize(
    "claim_text",
    [
        "Starter is $0 a month.",
        "Starter is $0.00 a month.",
        "Starter is €0 a month.",
        "Starter is £0 a month.",
        "Starter is ¥0 a month.",
        "Starter costs 0 dollars a month.",
    ],
    ids=[
        "dollar-zero",
        "dollar-zero-cents",
        "euro-zero",
        "pound-zero",
        "yen-zero",
        "zero-dollars-words",
    ],
)
def test_zero_price_in_the_claim_is_matched_by_free_in_the_quote(claim_text: str) -> None:
    # Coordinator, from live run run-6a5fe9499c4d: one false positive of 19 quote-receipt claims
    # was a claim saying "$0" against a quote saying "free". A zero price and "free" are the
    # same value written two ways.
    url = "https://tokens.example/"
    quote = "Starter is free for small teams"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, f"{quote}."), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


@pytest.mark.parametrize(
    ("claim_text", "quote", "missing"),
    [
        ("Starter is $0 a month.", "Starter is open to small teams", "$0"),
        ("Starter is $5 a month.", "Starter is free for small teams", "$5"),
        ("Starter is $0 a month.", "Starter gives freedom to small teams", "$0"),
        ("Starter is $0.50 a month.", "Starter is free for small teams", "$0.50"),
    ],
    ids=["no-free-in-quote", "nonzero-price", "free-inside-a-longer-word", "nonzero-cents"],
)
def test_free_in_the_quote_covers_only_a_zero_price(
    claim_text: str, quote: str, missing: str
) -> None:
    url = "https://tokens.example/"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, f"{quote}."), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == f"claim numbers not in quote: {missing}"


def test_zero_cents_quote_fuzzy_matches_a_whole_dollar_page() -> None:
    # Quote "$20.00", page "$20": not a substring, so the fuzzy path's number check needs the
    # same canonical form as the claim rule.
    url = "https://tokens.example/"
    text = "Pro costs $20 per seat per month, billed yearly, with audit logs."
    claim = claim_with_quote(
        "Pro costs $20 per seat.", url, "Pro costs $20.00 per seat per month, billed yearly"
    )
    out = verify_claim(claim, page(url, text), [])
    assert (out.verified, out.verify_method) == (True, "quote_fuzzy")


@pytest.mark.parametrize(
    ("claim_text", "missing"),
    [("Pro costs $20.05 per month.", "$20.05"), ("Pro costs $20.50 per month.", "$20.50")],
    ids=["nonzero-cents", "nonzero-tenths"],
)
def test_nonzero_cents_are_not_dropped(claim_text: str, missing: str) -> None:
    url = "https://tokens.example/"
    claim = claim_with_quote(claim_text, url, "Pro costs $20 per month")
    out = verify_claim(claim, page(url, "Pro costs $20 per month."), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == f"claim numbers not in quote: {missing}"


# --- suffixed, trailing-sign and leading-decimal prices (GitHub issue #45, rule (d)) --------
# The quote-to-page half of test_suffixed_trailing_and_leading_decimal_prices_are_one_number is
# in tests/test_verify.py. A miss note names each claim value in its signed reading, the one
# spelling for rules (c) and (d): the sign in front and a leading point given its zero (`25$` is
# named `$25`, `$.99` is `$0.99`, as `25 dollars` is `$25`); otherwise as the normalized claim
# writes it (`$1.2m`, `$20,000k`, and `$20.00`, not `$20`).


@pytest.mark.parametrize(
    ("claim_text", "quote", "missing"),
    [
        ("$20k a year", "$20 per seat per month", "$20k"),
        ("Enterprise is $1.2M a year.", "Enterprise is $1.2 per hour", "$1.2m"),
        ("Enterprise is $20 a year.", "Enterprise is $20k a year", "$20"),
        ("Enterprise is $20m a year.", "Enterprise is $20k a year", "$20m"),
        ("Enterprise is $20,000k a year.", "Enterprise is $20,000 a year", "$20,000k"),
    ],
    ids=[
        "suffix-in-claim",
        "suffix-after-a-decimal-in-claim",
        "suffix-in-quote",
        "other-suffix",
        "suffix-on-the-quotes-digits",
    ],
)
def test_suffixed_trailing_and_leading_decimal_prices_are_one_number_in_the_claim_rule(
    claim_text: str, quote: str, missing: str
) -> None:
    # Brief case 2: on 949741f the token stopped before the suffix, so `$20k` in the claim (or in
    # the quote) read as `$20` and every one of these verified.
    url = "https://tokens.example/"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, f"{quote}."), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == f"claim numbers not in quote: {missing}"


@pytest.mark.parametrize(
    ("claim_text", "quote"),
    [
        ("Enterprise is $20k a year.", "Enterprise is $20,000 a year"),
        ("Enterprise is $20,000 a year.", "Enterprise is $20K a year"),
        ("Enterprise is $1.2M a year.", "Enterprise is $1,200,000 a year"),
        ("Enterprise is €1200000 a year.", "Enterprise is €1.2m a year"),
        ("Enterprise is £1.5k a month.", "Enterprise is £1,500.00 a month"),
        ("Enterprise is $2B in total.", "Enterprise is $2,000,000,000 in total"),
    ],
    ids=["k-in-claim", "k-in-quote", "m-after-a-decimal", "m-in-quote", "k-zero-cents", "b"],
)
def test_suffixed_trailing_and_leading_decimal_prices_are_one_number_same_amount_verifies(
    claim_text: str, quote: str
) -> None:
    # Brief case 3: `$20k` = `$20,000`, `$1.2m` = `$1,200,000`. On 949741f the suffixed side read
    # as `$20`, `$1.2`, `€1.2`, `£1.5` or `$2`, and each was a miss.
    url = "https://tokens.example/"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, f"{quote}."), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


def price_claim(claim_price: str, quote_price: str) -> tuple[Claim, dict[str, FetchedPage]]:
    """`Pro costs <claim_price> a month.` citing the quote `Pro costs <quote_price> a month`,
    and a page that holds the quote."""
    url = "https://tokens.example/"
    quote = f"Pro costs {quote_price} a month"
    claim = claim_with_quote(f"Pro costs {claim_price} a month.", url, quote)
    return claim, page(url, f"{quote}.")


@pytest.mark.parametrize(
    ("written", "signed", "other"),
    [
        ("25$", "$25", "$30"),
        ("25€", "€25", "€30"),
        ("25£", "£25", "£30"),
        ("25¥", "¥25", "¥30"),
        ("$.99", "$0.99", "$0.49"),
        ("€.50", "€0.50", "€0.75"),
    ],
    ids=[
        "trailing-dollar",
        "trailing-euro",
        "trailing-pound",
        "trailing-yen",
        "dollar-cents",
        "euro",
    ],
)
def test_suffixed_trailing_and_leading_decimal_prices_are_one_number_sign_after_or_point_first(
    written: str, signed: str, other: str
) -> None:
    # Brief case 4: `25$` is extracted and compared as `$25`, and `$.99` as `$0.99`, in the claim
    # and in the quote. On 949741f the claim's `25$` and `$.99` read as the bare integers `25`
    # and `99`, which are not checked, so the wrong price verified; and the quote's read as `25`
    # and `99`, so the signed spelling in the claim was a miss.
    out = verify_claim(*price_claim(written, other), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == f"claim numbers not in quote: {signed}"
    for claim_price, quote_price in ((signed, written), (written, signed), (written, written)):
        out = verify_claim(*price_claim(claim_price, quote_price), [])
        assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


@pytest.mark.parametrize(
    "claim_text",
    ["Pro is $5 max per seat.", "Pro is $5/mo.", "Pro is $5mo.", "Pro is $5 a month, max."],
    ids=["space-then-max", "slash-mo", "mo-joined", "max-later"],
)
def test_a_letter_after_a_signed_number_is_a_suffix_only_when_the_word_ends_there(
    claim_text: str,
) -> None:
    # Guard for rule (d), brief assumption 6: `k`, `m` or `b` is a suffix only directly after a
    # signed number and when no letter or digit follows, so `$5 max`, `$5/mo` and `$5mo` still
    # read `$5`. Green on 949741f by design; it turns red if the suffix swallows the `m` of `mo`.
    url = "https://tokens.example/"
    quote = "Pro is $5 a month"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, f"{quote}."), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


@pytest.mark.parametrize(
    ("claim_price", "quote_price"),
    [("$20", "5$20"), ("$.99", "5$.99")],
    ids=["sign-then-digits", "sign-then-point"],
)
def test_a_sign_between_two_numbers_leads_the_second(claim_price: str, quote_price: str) -> None:
    # Guard for rule (d), brief assumption 7: a scraped table can join one cell's number to the
    # next cell's price (`seats: 5$20`). A sign followed by a number leads that number, as on
    # 949741f, so the quote holds `5` and `$20`, not `5$` and `20`. Green on 949741f by design.
    out = verify_claim(*price_claim(claim_price, f"seats: {quote_price}"), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


@pytest.mark.parametrize(
    ("claim_text", "quote", "outcome"),
    [
        (
            "Enterprise is $1.2345k a year.",
            "Enterprise is $1,234.5 a year",
            (True, "quote_exact", None),
        ),
        (
            "Enterprise is $1.2345k a year.",
            "Enterprise is $1,234 a year",
            (False, None, "claim numbers not in quote: $1.2345k"),
        ),
        ("Starter is $0k a year.", "Starter is $0 a year", (True, "quote_exact", None)),
    ],
    ids=["digits-past-the-point-kept", "digits-past-the-point-not-dropped", "zero-amount"],
)
def test_a_suffix_is_written_out_without_losing_a_digit(
    claim_text: str, quote: str, outcome: tuple[bool, str | None, str | None]
) -> None:
    # The `token` verdict's MEDIUM 2: `_expand_suffix` keeps the digits left past the point
    # (`$1.2345k` is `$1,234.5`, not `$1,234`) and writes a zero amount as `0` (`$0k` is `$0`).
    url = "https://tokens.example/"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, f"{quote}."), [])
    assert (out.verified, out.verify_method, out.verify_note) == outcome


# --- unsigned prices (GitHub issue #45, rule (c)) -------------------------------------------
# The claim rule reads `25 dollars`, `25 USD`, `USD 25`, `$ 25` and `25 €` as `$25` or `€25`, in
# the claim and in the quote's values (brief assumptions 3 to 5). The quote-to-page half, which
# does not use this reading, is in tests/test_verify.py.


@pytest.mark.parametrize(
    ("claim_text", "missing"),
    [
        ("Pro costs 25 dollars.", "$25"),
        ("Pro costs 1 dollar.", "$1"),
        ("Pro costs 25 USD.", "$25"),
        ("Pro costs USD 25.", "$25"),
        ("Pro costs $ 25.", "$25"),
        ("Pro costs 25 $ a month.", "$25"),
        ("Pro costs 25 euro.", "€25"),
        ("Pro costs 25 euros.", "€25"),
        ("Pro costs 25 EUR.", "€25"),
        ("Pro costs EUR 25.", "€25"),
        ("Pro costs € 25.", "€25"),
        ("Pro costs 25 €.", "€25"),
        ("Pro costs 25 GBP.", "£25"),
        ("Pro costs GBP 25.", "£25"),
        ("Pro costs 25 £.", "£25"),
        ("Pro costs 25 JPY.", "¥25"),
        ("Pro costs JPY 25.", "¥25"),
        ("Pro costs 25 yen.", "¥25"),
        ("Pro costs 25 ¥.", "¥25"),
        ("Pro costs 25.50 dollars.", "$25.50"),
        ("Pro costs 2,500 dollars.", "$2,500"),
    ],
    ids=[
        "dollars",
        "dollar",
        "usd-after",
        "usd-before",
        "sign-space",
        "space-sign",
        "euro",
        "euros",
        "eur-after",
        "eur-before",
        "euro-sign-space",
        "space-euro-sign",
        "gbp-after",
        "gbp-before",
        "space-pound-sign",
        "jpy-after",
        "jpy-before",
        "yen",
        "space-yen-sign",
        "decimal",
        "thousands-separator",
    ],
)
def test_unsigned_prices_in_the_claim_are_checked(claim_text: str, missing: str) -> None:
    # Brief (c): on 949741f each of these was a bare integer, unchecked, so the wrong price
    # verified against a quote saying `$20` (the decimal and separator ones were checked, but
    # named as written, `25.50`). The note names the price in its signed reading (assumption 5).
    url = "https://tokens.example/"
    quote = "Pro costs $20"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, f"{quote}."), [])
    assert (out.verified, out.verify_method) == (False, None)
    assert out.verify_note == f"claim numbers not in quote: {missing}"


@pytest.mark.parametrize(
    ("unsigned", "signed"),
    [
        ("25 dollars", "$25"),
        ("25 USD", "$25"),
        ("USD 25", "$25"),
        ("$ 25", "$25"),
        ("25 €", "€25"),
        ("25 euros", "€25"),
        ("GBP 25", "£25"),
        ("25 yen", "¥25"),
    ],
    ids=["dollars", "usd-after", "usd-before", "sign-space", "space-sign", "euros", "gbp", "yen"],
)
def test_unsigned_price_matches_its_signed_spelling_in_the_claim_rule(
    unsigned: str, signed: str
) -> None:
    # Brief (c), assumption 4: the quote's values add the signed reading of its unsigned price,
    # so a claim may restate it either way. Checked in this order so that a defect in the
    # quote-side reading fails on the both-unsigned case first; on 949741f the both-unsigned and
    # unsigned-claim cases verified (the claim's `25` was unchecked) and the signed claim missed.
    url = "https://tokens.example/"
    cases = (
        ("both unsigned", unsigned, unsigned),
        ("unsigned claim, signed quote", unsigned, signed),
        ("signed claim, unsigned quote", signed, unsigned),
    )
    for case, claim_price, quote_price in cases:
        quote = f"Pro costs {quote_price}"
        claim = claim_with_quote(f"Pro costs {claim_price}.", url, quote)
        out = verify_claim(claim, page(url, f"{quote}."), [])
        outcome = (out.verified, out.verify_method, out.verify_note)
        assert outcome == (True, "quote_exact", None), case


@pytest.mark.parametrize(
    "claim_text",
    ["Pro costs 25 pounds.", "Pro costs 25 bucks.", "Pro costs twenty-five dollars."],
    ids=["pounds", "bucks", "number-words"],
)
def test_currency_words_outside_the_list_are_not_prices(claim_text: str) -> None:
    # Brief assumption 3: "pounds" is often a weight, and "bucks" and number words are out of
    # scope, so these stay unchecked and verify against a quote saying `$20`. Green on 949741f
    # by design; it turns red if the word list grows past the brief's.
    url = "https://tokens.example/"
    quote = "Pro costs $20"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, f"{quote}."), [])
    assert (out.verified, out.verify_method, out.verify_note) == (True, "quote_exact", None)


@pytest.mark.parametrize(
    ("claim_text", "quote", "text", "outcome"),
    [
        (
            "Pro costs 25 dollars.",
            "Pro costs $20",
            "Pro costs $20.",
            (False, None, "claim numbers not in quote: $25"),
        ),
        (
            "Pro costs $25.",
            "Pro costs 25 dollars",
            "Pro costs 25 dollars.",
            (True, "quote_exact", None),
        ),
        (
            "Pro costs $20.",
            "Pro costs 20 dollars",
            "Pro costs $20.",
            (
                False,
                None,
                "quote not found on page: numbers differ (quote has 20; page has $20 there; "
                "partial_ratio=92.3)",
            ),
        ),
    ],
    ids=["probe-2", "probe-3", "probe-6"],
)
def test_unsigned_prices_verification_5_probes(
    claim_text: str, quote: str, text: str, outcome: tuple[bool, str | None, str | None]
) -> None:
    # Brief, Verification 5, probes 2, 3 and 6. On 949741f probe 2 verified and probe 3 did not;
    # probe 6 (the narrow rule) was a miss and stays one.
    url = "https://tokens.example/"
    out = verify_claim(claim_with_quote(claim_text, url, quote), page(url, text), [])
    assert (out.verified, out.verify_method, out.verify_note) == outcome


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
    # sample_claims[1] has only a search receipt: no quote to check against. Its text is given a
    # value token ("$14"; on 949741f a bare "14 dollars" was not checked at all), so applying the
    # claim rule here would turn this claim red.
    claim = sample_claims[1].model_copy(
        update={
            "text": "Zeta Team is $14 per seat per month.",
            "verified": False,
            "verify_method": None,
        }
    )
    out = verify_claim(claim, {}, sample_search_results)
    assert (out.verified, out.verify_method, out.verify_note) == (True, "search_log", None)
