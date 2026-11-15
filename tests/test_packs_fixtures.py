"""Golden comparison fixture integrity, and that `FakeKeenable` serves it."""

from __future__ import annotations

from fixtures.loader import load_comparison

from receipts.contracts import QuoteReceipt, SearchReceipt
from receipts.fakes import FakeKeenable

NAME = "acme_vs_bolt"


def test_comparison_loads_typed() -> None:
    cmp = load_comparison(NAME)
    assert cmp.subject != cmp.rival
    assert cmp.search_results
    assert cmp.pages
    assert cmp.golden_claims


def test_quote_receipts_point_at_fetched_pages() -> None:
    cmp = load_comparison(NAME)
    pages = {p.url: p for p in cmp.pages}
    quotes = [c for c in cmp.golden_claims if isinstance(c.receipt, QuoteReceipt)]
    assert quotes
    for claim in quotes:
        assert isinstance(claim.receipt, QuoteReceipt)
        assert claim.receipt.url in pages


def test_search_receipts_match_search_results() -> None:
    cmp = load_comparison(NAME)
    rows = {(r.query, r.rank, r.url) for r in cmp.search_results}
    searches = [c for c in cmp.golden_claims if isinstance(c.receipt, SearchReceipt)]
    assert searches
    for claim in searches:
        assert isinstance(claim.receipt, SearchReceipt)
        assert (claim.receipt.query, claim.receipt.rank, claim.receipt.url) in rows


def test_verified_flag_matches_quote_substring() -> None:
    cmp = load_comparison(NAME)
    pages = {p.url: p.text for p in cmp.pages}
    seen_false = 0
    for claim in cmp.golden_claims:
        if not isinstance(claim.receipt, QuoteReceipt):
            continue
        present = claim.receipt.quote in pages[claim.receipt.url]
        assert claim.verified is present
        seen_false += not claim.verified
    assert seen_false == 1


def test_fake_keenable_serves_fixture() -> None:
    cmp = load_comparison(NAME)
    fake = FakeKeenable(cmp.search_results, {p.url: p for p in cmp.pages})
    first = cmp.search_results[0]
    hits = fake.search(first.query)
    assert first in hits
    page = fake.fetch(first.url)
    assert page.ok
    assert not fake.fetch("https://unknown.example/nope").ok
