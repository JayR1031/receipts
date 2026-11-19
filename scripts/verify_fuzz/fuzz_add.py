"""Judge r5: fuzz_skip.py's pages (2-4 plans, some prices words or another currency), but the quote
ADDS a = 1 or 2 short words the page does not have ("just", "only", "now", "single", "all",
"the", "very", "really") at random word boundaries inside plan i's segment, before its price.
  MIS: plan i is given plan i+1's price (oracle: must not verify; a verified one is a wrong price
       shown as verified, and a claim repeating the quote's price passes the claim rule);
  TRUE: the same insertions with plan i's own numeric price (oracle: must verify when the score
       reaches 90; a 'numbers differ' miss is a true quote rejected for numbers).
Usage: fuzz_add.py <seed> <n> [all [a_max]]  (all: print every example; a_max: most words added,
default 2)"""

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
ADD = ["just", "only", "now", "single", "all", "the", "very", "really"]


@dataclass
class Page:
    names: list[str]
    descs: list[str]
    prices: list[str]
    sep: str
    colon: str
    segs: list[str]
    body: str


@dataclass
class Case:
    pg: Page
    i: int
    new: str
    pre: str
    gap: str


@dataclass
class Tally:
    lim: int
    a_max: int
    mis: list[int] = field(default_factory=lambda: [0, 0, 0])
    tru: list[int] = field(default_factory=lambda: [0, 0, 0])
    ex: list[tuple[object, ...]] = field(default_factory=list)
    exr: list[tuple[object, ...]] = field(default_factory=list)
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


def insert(rng: random.Random, seg: str, a: int) -> str:
    words = seg.split(" ")
    for _ in range(a):
        words.insert(rng.randint(1, len(words)), rng.choice(ADD))
    return " ".join(words)


def new_page(rng: random.Random) -> Page:
    k = rng.randint(2, 4)
    names = rng.sample(NAMES, k)
    descs = [rng.choice(DESCS) for _ in range(k)]
    prices = [rng.choice(WORDS) if rng.random() < 0.35 else rng.choice(NUMS) for _ in range(k)]
    tails = [rng.choice(TAILS) if prices[j] not in WORDS else "" for j in range(k)]
    sep = rng.choice(SEPS)
    colon = rng.choice([": ", " is ", " costs ", " "])
    segs = [f"{names[j]}{descs[j]}{colon}{prices[j]}{tails[j]}" for j in range(k)]
    return Page(names, descs, prices, sep, colon, segs, sep.join(segs) + ".")


def numeric_clash(old: str, new: str) -> bool:
    return rules._canonical_number(old) == rules._canonical_number(new)


def skip_case(pg: Page, i: int, start: int, new: str) -> bool:
    if new in WORDS or new == pg.prices[i]:
        return True
    if pg.prices[i] not in WORDS and numeric_clash(pg.prices[i], new):
        return True
    return any(numeric_clash(p, new) for p in pg.prices[start:i] if p not in WORDS)


def kind_of(old: str, new: str) -> str:
    if old in WORDS:
        return "word"
    return "shares-char" if set(old) & set(new) else "no-shared-char"


def score_mis(tally: Tally, case: Case) -> None:
    pg = case.pg
    misq = f"{case.pre}{case.gap}{case.new}"
    kind = kind_of(pg.prices[case.i], case.new)
    tally.mis[0] += 1
    tally.by_kind.setdefault(kind, [0, 0, 0])
    tally.by_kind[kind][0] += 1
    v, _m, note = verify(misq, pg.body)
    if v or (note and "numbers differ" in note):
        tally.mis[2] += 1
        tally.by_kind[kind][2] += 1
    if v:
        tally.mis[1] += 1
        tally.by_kind[kind][1] += 1
        if len(tally.ex) < tally.lim:
            tally.ex.append((kind, pg.body, misq, note))


def score_true(tally: Tally, case: Case) -> None:
    pg = case.pg
    trueq = f"{case.pre}{case.gap}{pg.prices[case.i]}"
    tally.tru[0] += 1
    v, _m, note = verify(trueq, pg.body)
    if v:
        tally.tru[2] += 1
    elif note and "numbers differ" in note:
        tally.tru[1] += 1
        if len(tally.exr) < tally.lim:
            tally.exr.append((pg.body, trueq, note))


def make_case(rng: random.Random, tally: Tally) -> Case | None:
    pg = new_page(rng)
    i = rng.randrange(len(pg.names) - 1)
    new = pg.prices[i + 1]
    start = rng.randrange(i + 1)
    a = rng.randint(1, tally.a_max)
    lead = insert(rng, f"{pg.names[i]}{pg.descs[i]}{pg.colon}".rstrip(" "), a)
    gap = " " if pg.colon.endswith(" ") else ""
    if skip_case(pg, i, start, new):
        return None
    return Case(pg, i, new, pg.sep.join(pg.segs[start:i] + [lead]), gap)


def step(rng: random.Random, tally: Tally) -> None:
    case = make_case(rng, tally)
    if case is None:
        return
    score_mis(tally, case)
    if case.pg.prices[case.i] not in WORDS:
        score_true(tally, case)


def report(seed: int, tally: Tally) -> None:
    mis, tru, by_kind = tally.mis, tally.tru, tally.by_kind
    print(f"seed={seed} MIS tried={mis[0]} scored>=90={mis[2]} verified={mis[1]}")
    for kd in sorted(by_kind):
        t, ver, s90 = by_kind[kd][0], by_kind[kd][1], by_kind[kd][2]
        print(f"  kind={kd} tried={t} scored>=90={s90} verified={ver}")
    print(f"seed={seed} TRUE tried={tru[0]} verified={tru[2]} rejected-for-numbers={tru[1]}")
    for x in tally.ex:
        print("EXMIS", x)
    for x in tally.exr:
        print("EXTRUE", x)


def main(seed: int, n: int, args: list[str]) -> None:
    print("RULES", rules.__file__)
    lim = 10**9 if len(args) > 0 and args[0] == "all" else 8
    a_max = int(args[1]) if len(args) > 1 else 2
    rng = random.Random(seed)
    tally = Tally(lim, a_max)
    for _ in range(n):
        step(rng, tally)
    report(seed, tally)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3:])
