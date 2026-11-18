"""Fuzz: a quote built from the page's template with some prices changed, swapped, repeated or
left out, plus small letter edits away from the numbers. Oracle: if a quote slot holds a price
and it differs from the page's price in that slot, the quote must not verify.
Usage: fuzz_place2.py <seed> <n>"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime

import receipts.verify.rules as rules
from receipts.contracts import Claim, FetchedPage, QuoteReceipt

T0 = datetime(2026, 11, 14, tzinfo=UTC)
URL = "https://probe.example/p"
TEMPLATES = [
    "Starter plan {} per seat billed monthly with email support. "
    "Team plan {} per seat billed monthly with chat support. "
    "Business plan {} per seat billed monthly.",
    "Pro yearly: {}. Pro monthly: {}.",
    "Pro: {}/month or {}/year.",
    "Starter {} per seat, Team {} per seat, Business {} per seat.",
    "Basic {} Pro {} Max {}",
    "Plans: {} / {} / {} per month",
    "Pro is {} per month or {} per year, and Team is {} per seat.",
    "Save {} on yearly, {} on two years, {} on three years.",
    "Starter {} Team {} Business {} Enterprise {}",
    "The basic plan costs {} per month and the pro plan costs {} per month",
]
VALUES = [
    "$8",
    "$12",
    "$15",
    "$19",
    "$199",
    "$1,999",
    "$19.99",
    "$9",
    "$29",
    "$290",
    "20%",
    "25%",
    "$20",
    "$200",
    "$2",
    "$1",
    "$18",
    "$180",
]
LETTERS = "abcdefghijklmnopqrstuvwxyz "


@dataclass
class Tally:
    found: list[tuple[object, ...]] = field(default_factory=list)
    tried: int = 0
    verified_fuzzy: int = 0


def quote_values(rng: random.Random, page_vals: list[str]) -> list[str]:
    quote_vals = []
    for pv in page_vals:
        r = rng.random()
        if r < 0.4:
            quote_vals.append(pv)
        elif r < 0.65:
            quote_vals.append(rng.choice(page_vals))
        elif r < 0.8:
            quote_vals.append("")
        else:
            quote_vals.append(rng.choice(VALUES))
    return quote_vals


def mutate(rng: random.Random, s: str, j: int, op: float) -> str:
    if not (s[j].isalpha() or s[j] == " "):
        return s
    if op < 0.4:
        return s[:j] + s[j + 1 :]
    if op < 0.8:
        return s[:j] + rng.choice(LETTERS) + s[j:]
    return s[:j] + rng.choice(LETTERS) + s[j + 1 :]


def letter_edits(rng: random.Random, parts: list[str]) -> None:
    """Letter edits only inside the literal parts."""
    for _e in range(rng.randint(0, 3)):
        i = rng.randrange(len(parts))
        s = parts[i]
        if not s:
            continue
        j = rng.randrange(len(s))
        op = rng.random()
        parts[i] = mutate(rng, s, j, op)


def build_quote(rng: random.Random, tpl: str, quote_vals: list[str]) -> str:
    parts = tpl.split("{}")
    letter_edits(rng, parts)
    quote = parts[0] + "".join(v + p for v, p in zip(quote_vals, parts[1:], strict=False))
    return quote.rstrip(".")


def verify(quote: str, page: str) -> tuple[bool, str | None, str | None]:
    claim = Claim(
        domain="pricing",
        about="rival",
        text="Plan pricing.",
        receipt=QuoteReceipt(url=URL, quote=quote),
    )
    pages = {URL: FetchedPage(url=URL, text=page, fetched_at=T0, ok=True)}
    out = rules.verify_claim(claim, pages, [])
    return out.verified, out.verify_method, out.verify_note


def step(rng: random.Random, tally: Tally) -> None:
    tpl = rng.choice(TEMPLATES)
    n = tpl.count("{}")
    page_vals = rng.sample(VALUES, n)
    quote_vals = quote_values(rng, page_vals)
    page = tpl.format(*page_vals)
    quote = build_quote(rng, tpl, quote_vals)
    wrong = any(q and q != p for q, p in zip(quote_vals, page_vals, strict=False))
    verified, method, note = verify(quote, page)
    tally.tried += 1
    if verified and method == "quote_fuzzy":
        tally.verified_fuzzy += 1
    if verified and wrong:
        tally.found.append((method, page, quote, page_vals, quote_vals, note))


def main(seed: int, n_iter: int) -> None:
    print("RULES", rules.__file__)
    rng = random.Random(seed)
    tally = Tally()
    for _ in range(n_iter):
        step(rng, tally)
    for f in tally.found[:15]:
        print("VERIFIED-WITH-WRONG-SLOT", f)
    print(
        f"seed={seed} tried={tally.tried} verified_fuzzy={tally.verified_fuzzy} "
        f"verified_with_a_wrong_slot={len(tally.found)}"
    )


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
