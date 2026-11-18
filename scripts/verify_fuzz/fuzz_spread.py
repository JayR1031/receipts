"""Attempt 5: random spread misquotes. Page '<prefix> <l1> $A<sep><l2> $B.'; quote is the prefix
with words dropped, then '<l1> $B' (the wrong price for l1). Counts verified misquotes.
Usage: fuzz_spread.py <seed> <n>"""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime

import receipts.verify.rules as rules
from receipts.contracts import Claim, FetchedPage, QuoteReceipt

T0 = datetime(2026, 11, 14, tzinfo=UTC)
U = "https://fuzz.example/p"
WORDS = (
    "every seat on the plan includes priority support audit logs single sign-on unlimited "
    "projects for each member billed monthly yearly with the whole team and organisation"
).split()
LABELS = ["team", "pro", "basic", "plus", "max", "lite", "scale"]
PRICES = ["$9", "$14", "$19", "$29", "$12", "$15", "$99", "$8", "$5", "$49"]
SEPS = [", ", " / ", " or ", "; ", " · "]


def one_case(rng: random.Random) -> tuple[str, str]:
    pre = rng.sample(WORDS, rng.randint(8, 16))
    l1, l2 = rng.sample(LABELS, 2)
    a, b = rng.sample(PRICES, 2)
    page = " ".join(pre) + f": {l1} {a}{rng.choice(SEPS)}{l2} {b}."
    k = rng.randint(0, 2)
    drop = set(rng.sample(range(len(pre)), k))
    quote = " ".join(w for i, w in enumerate(pre) if i not in drop) + f": {l1} {b}"
    return page, quote


def main(seed: int, n: int) -> None:
    print("RULES", rules.__file__)
    rng = random.Random(seed)
    hits = tried = 0
    ex = []
    for _ in range(n):
        page, quote = one_case(rng)
        c = Claim(
            domain="pricing", about="rival", text="x", receipt=QuoteReceipt(url=U, quote=quote)
        )
        o = rules.verify_claim(c, {U: FetchedPage(url=U, text=page, fetched_at=T0, ok=True)}, [])
        tried += 1
        if o.verified:
            hits += 1
            if len(ex) < 3:
                ex.append((page, quote, o.verify_note))
    print(f"seed={seed} spread misquotes tried={tried} verified={hits}")
    for e in ex:
        print("EX", e)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
