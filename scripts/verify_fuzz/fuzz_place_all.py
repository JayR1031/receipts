"""Judge r3: random misquotes (one price replaced by another page price, or two swapped,
optionally another price dropped) and random legit edits (no number changed; words dropped,
punctuation/typo edits, a price dropped). Reports verified misquotes (fail-open) and rejected
legit quotes (fail-closed) for the rules copy on sys.path.
Usage: fuzz_place_all.py <seed> <n>"""

from __future__ import annotations

import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

import receipts.verify.rules as rules
from receipts.contracts import Claim, FetchedPage, QuoteReceipt

T0 = datetime(2026, 11, 14, tzinfo=UTC)
URL = "https://fuzz.example/p"
NAMES = ["starter", "basic", "team", "pro", "business", "max", "plus", "growth", "scale", "lite"]
TAILS = [
    "per seat",
    "per month",
    "a month",
    "per user",
    "billed yearly",
    "billed monthly",
    "per year",
    "/mo",
    "/yr",
    "",
]
PRICES = [
    "$8",
    "$12",
    "$15",
    "$19",
    "$199",
    "$20",
    "$200",
    "$29",
    "$9",
    "$99",
    "$1",
    "$10",
    "$100",
    "$18",
    "$180",
    "20%",
    "25%",
    "$19.99",
    "$5",
]


@dataclass
class Page:
    names: list[str]
    prices: list[str]
    tails: list[str]
    sep: str
    prefix: str
    body: str


@dataclass
class Tally:
    tried_bad: int = 0
    tried_good: int = 0
    fuzzy_bad: int = 0
    fuzzy_good: int = 0
    fail_open: list[tuple[object, ...]] = field(default_factory=list)
    fail_closed: list[tuple[object, ...]] = field(default_factory=list)


def page(rng: random.Random) -> tuple[list[str], list[str], list[str]]:
    n = rng.randint(2, 5)
    names = rng.sample(NAMES, n)
    prices = rng.sample(PRICES, n)
    tails = [rng.choice(TAILS) for _ in range(n)]
    return names, prices, tails


def render(
    names: Sequence[str], prices: Sequence[str | None], tails: Sequence[str], sep: str
) -> str:
    parts = []
    for nm, pr, tl in zip(names, prices, tails, strict=False):
        seg = f"{nm} {pr} {tl}".strip() if pr is not None else f"{nm} {tl}".strip()
        parts.append(seg)
    return sep.join(parts)


def verify(quote: str, body: str) -> tuple[bool, str | None, str | None]:
    claim = Claim(
        domain="pricing",
        about="rival",
        text="Probe claim.",
        receipt=QuoteReceipt(url=URL, quote=quote),
    )
    pages = {URL: FetchedPage(url=URL, text=body, fetched_at=T0, ok=True)}
    out = rules.verify_claim(claim, pages, [])
    return out.verified, out.verify_method, out.verify_note


def new_page(rng: random.Random) -> Page:
    names, prices, tails = page(rng)
    sep = rng.choice([". ", ", ", "; ", " · ", " | "])
    prefix = rng.choice(["", "pricing: ", "our plans: ", "compare plans. "])
    body = prefix + render(names, prices, tails, sep) + "."
    return Page(names, prices, tails, sep, prefix, body)


def swapped(rng: random.Random, prices: list[str]) -> list[str | None] | None:
    i, j = rng.sample(range(len(prices)), 2)
    if rules._canonical_number(prices[i]) == rules._canonical_number(prices[j]):
        return None
    out: list[str | None] = list(prices)
    out[i], out[j] = prices[j], prices[i]
    return out


def replaced(rng: random.Random, prices: list[str], kind: str) -> list[str | None]:
    out: list[str | None] = list(prices)
    i = rng.randrange(len(prices))
    pool = [p for p in prices if p != prices[i]] + [p for p in PRICES if p != prices[i]]
    out[i] = rng.choice(pool)
    if kind == "replace-drop" and len(prices) >= 2:
        k = rng.choice([x for x in range(len(prices)) if x != i])
        out[k] = None
    return out


def misquote_prices(rng: random.Random, prices: list[str], kind: str) -> list[str | None] | None:
    if kind == "swap" and len(prices) >= 2:
        return swapped(rng, prices)
    return replaced(rng, prices, kind)


def misquote_step(rng: random.Random, pg: Page, tally: Tally) -> bool:
    kind = rng.choice(["replace", "swap", "replace-drop"])
    q_prices = misquote_prices(rng, pg.prices, kind)
    if q_prices is None:
        return False
    quote = pg.prefix + render(pg.names, q_prices, pg.tails, pg.sep)
    if rules.normalize(quote) in rules.normalize(pg.body):
        return False  # exact elsewhere: not a misquote by construction
    tally.tried_bad += 1
    v, m, note = verify(quote, pg.body)
    if m == "quote_fuzzy":
        tally.fuzzy_bad += 1
    if v:
        tally.fail_open.append((kind, pg.body, quote, m, note))
    return True


def typo(rng: random.Random, names: list[str]) -> None:
    x = rng.randrange(len(names))
    nm = names[x]
    if len(nm) > 3:
        p = rng.randrange(1, len(nm) - 1)
        names[x] = nm[:p] + nm[p + 1 :]


def legit_quote(rng: random.Random, pg: Page) -> tuple[str, str]:
    g_prices: list[str | None] = list(pg.prices)
    gk = rng.choice(["drop-price", "typo", "punct", "drop-word", "none"])
    g_tails = list(pg.tails)
    g_names = list(pg.names)
    if gk == "drop-price" and len(pg.prices) >= 2:
        g_prices[rng.randrange(len(pg.prices))] = None
    elif gk == "typo":
        typo(rng, g_names)
    elif gk == "drop-word":
        g_tails[rng.randrange(len(pg.tails))] = ""
    gsep = pg.sep if gk != "punct" else rng.choice([". ", ", ", "; ", " - "])
    return gk, pg.prefix + render(g_names, g_prices, g_tails, gsep)


def legit_step(rng: random.Random, pg: Page, tally: Tally) -> None:
    gk, good = legit_quote(rng, pg)
    tally.tried_good += 1
    v, m, note = verify(good, pg.body)
    if m == "quote_fuzzy":
        tally.fuzzy_good += 1
    if not v and note and "numbers differ" in note:
        tally.fail_closed.append((gk, pg.body, good, note))


def main(seed: int, n: int) -> None:
    print("RULES", rules.__file__)
    rng = random.Random(seed)
    tally = Tally()
    for _ in range(n):
        pg = new_page(rng)
        if misquote_step(rng, pg, tally):
            legit_step(rng, pg, tally)
    print(
        f"seed={seed} misquotes tried={tally.tried_bad} (fuzzy-verified {tally.fuzzy_bad}) "
        f"verified={len(tally.fail_open)}"
    )
    print(
        f"legit tried={tally.tried_good} (fuzzy {tally.fuzzy_good}) "
        f"rejected-for-numbers={len(tally.fail_closed)}"
    )
    for row in tally.fail_open:
        print("OPEN", row)
    for row in tally.fail_closed:
        print("CLOSED", row)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
