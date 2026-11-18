"""Judge r4: misquotes that give plan i the NEXT plan's price, on pricing pages where some prices
are words ("free", "custom", "contact sales") or another currency. The quote is the page text up
to plan i's price, with that price replaced by plan i+1's, optionally followed by plan i's tail.
Oracle: the quote states a price the page does not give plan i, so it must not verify.
Usage: fuzz_skip.py <seed> <n>"""

from __future__ import annotations

import random
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime

import receipts.verify.rules as rules
from receipts.contracts import Claim, FetchedPage, QuoteReceipt

T0 = datetime(2026, 11, 14, tzinfo=UTC)
URL = "https://fuzz.example/p"
NAMES = ["Hobby", "Starter", "Basic", "Team", "Pro", "Business", "Max", "Plus", "Growth", "Scale"]
DESCS = [
    "",
    " for personal projects",
    " for small teams",
    " with priority support",
    " for every seat on the team",
    " with unlimited projects and SSO",
    " for growing companies",
    " billed per active member",
]
WORDS = ["free", "free forever", "custom", "contact sales", "included", "on request"]
NUMS = [
    "$9",
    "$12",
    "$15",
    "$19",
    "$20",
    "$29",
    "$49",
    "$99",
    "$199",
    "€14",
    "€24",
    "£12",
    "£8",
    "20%",
    "25%",
]
TAILS = ["", " per month", " per seat", " a month", " /mo", " per user per month"]
SEPS = [". ", " · ", "; ", " | ", ", "]


@dataclass
class Page:
    names: list[str]
    descs: list[str]
    prices: list[str]
    tails: list[str]
    sep: str
    colon: str
    segs: list[str]
    body: str


@dataclass
class Tally:
    tried: int = 0
    bad: list[tuple[object, ...]] = field(default_factory=list)
    by_kind: dict[str, list[int]] = field(default_factory=dict)


def verify(quote: str, body: str) -> tuple[bool, str | None, str | None]:
    c = Claim(
        domain="pricing",
        about="rival",
        text="Probe claim.",
        receipt=QuoteReceipt(url=URL, quote=quote),
    )
    pages = {URL: FetchedPage(url=URL, text=body, fetched_at=T0, ok=True)}
    o = rules.verify_claim(c, pages, [])
    return o.verified, o.verify_method, o.verify_note


def new_page(rng: random.Random) -> Page:
    k = rng.randint(2, 4)
    names = rng.sample(NAMES, k)
    descs = [rng.choice(DESCS) for _ in range(k)]
    prices = [rng.choice(WORDS) if rng.random() < 0.35 else rng.choice(NUMS) for _ in range(k)]
    tails = [rng.choice(TAILS) if prices[j] not in WORDS else "" for j in range(k)]
    sep = rng.choice(SEPS)
    colon = rng.choice([": ", " is ", " costs ", " "])
    segs = [f"{names[j]}{descs[j]}{colon}{prices[j]}{tails[j]}" for j in range(k)]
    return Page(names, descs, prices, tails, sep, colon, segs, sep.join(segs) + ".")


def skip_pair(old: str, new: str) -> bool:
    if new in WORDS or new == old:
        return True
    return old not in WORDS and rules._canonical_number(old) == rules._canonical_number(new)


def kind_of(old: str, new: str) -> str:
    if old in WORDS:
        return "word"
    return "shares-char" if set(old) & set(new) else "no-shared-char"


def step(rng: random.Random, tally: Tally) -> None:
    pg = new_page(rng)
    i = rng.randrange(len(pg.names) - 1)
    new = pg.prices[i + 1]
    if skip_pair(pg.prices[i], new):
        return
    start = rng.randrange(i + 1)
    qtail = pg.tails[i] if rng.random() < 0.5 else ""
    last = f"{pg.names[i]}{pg.descs[i]}{pg.colon}{new}{qtail}"
    quote = pg.sep.join(pg.segs[start:i] + [last])
    if rules.normalize(quote) in rules.normalize(pg.body):
        return
    tally.tried += 1
    kind = kind_of(pg.prices[i], new)
    tally.by_kind.setdefault(kind, [0, 0])
    tally.by_kind[kind][0] += 1
    v, m, note = verify(quote, pg.body)
    if v:
        tally.by_kind[kind][1] += 1
        tally.bad.append((kind, pg.body, quote, m, note))


def main(seed: int, n: int) -> None:
    print("RULES", rules.__file__)
    rng = random.Random(seed)
    tally = Tally()
    for _ in range(n):
        step(rng, tally)
    print(f"seed={seed} misquotes tried={tally.tried} verified={len(tally.bad)}")
    for kd, (t, b) in sorted(tally.by_kind.items()):
        print(f"  kind={kd}: tried={t} verified={b}")
    for row in tally.bad:
        print("OPEN", row)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
