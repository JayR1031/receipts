"""Judge r4: TRUE quotes (no number changed) on pages with numbers close together (ranges,
'x/mo or y/yr', counts next to prices). Edits: drop a word, a typo, a punctuation change, drop a
tail. Reports quotes rejected with 'numbers differ' for the rules copy on sys.path.
Usage: fuzz_dense.py <seed> <n>"""

from __future__ import annotations

import random
import sys
from datetime import UTC, datetime

import receipts.verify.rules as rules
from receipts.contracts import Claim, FetchedPage, QuoteReceipt

T0 = datetime(2026, 11, 14, tzinfo=UTC)
URL = "https://fuzz.example/p"
NAMES = ["starter", "basic", "team", "pro", "business", "max", "plus", "growth"]
P = [
    "$9",
    "$12",
    "$15",
    "$19",
    "$20",
    "$29",
    "$49",
    "$99",
    "$190",
    "$199",
    "$290",
    "$1,999",
    "$19.99",
    "€14",
    "20%",
]
SHAPES = [
    "{n} {a}/mo or {b}/yr",
    "{n} {a} per month, {b} per year",
    "{n} {a}-{b} per seat",
    "{n} from {a} to {b} a month",
    "{n} up to {c} users at {a} each",
    "{n} {c} seats for {a}",
    "{n} {a} ({b} billed yearly)",
    "{n} {a} / {b}",
]
COUNTS = ["5", "10", "25", "100", "1,000", "2,500"]


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


def segs_for(rng: random.Random, k: int) -> list[str]:
    out = []
    for nm in rng.sample(NAMES, k):
        a, b = rng.sample(P, 2)
        out.append(rng.choice(SHAPES).format(n=nm, a=a, b=b, c=rng.choice(COUNTS)))
    return out


def drop_word(rng: random.Random, words: list[str], nonnum: list[int]) -> None:
    if len(nonnum) > 1:
        del words[rng.choice(nonnum)]


def typo(rng: random.Random, words: list[str], nonnum: list[int]) -> None:
    if nonnum:
        i = rng.choice(nonnum)
        w = words[i]
        if len(w) > 3:
            j = rng.randrange(1, len(w) - 1)
            words[i] = w[:j] + w[j + 1 :]


def drop_tail(words: list[str]) -> list[str]:
    if len(words) > 3 and not any(ch.isdigit() for ch in words[-1]):
        return words[:-1]
    return words


def edit(rng: random.Random, s: str) -> tuple[str, str]:
    words = s.split(" ")
    kind = rng.choice(["drop-word", "typo", "punct", "drop-tail"])
    nonnum = [i for i, w in enumerate(words) if not any(ch.isdigit() for ch in w)]
    if kind == "punct":
        return kind, s.replace(", ", "; ").replace(". ", "; ")
    if kind == "drop-word":
        drop_word(rng, words, nonnum)
    elif kind == "typo":
        typo(rng, words, nonnum)
    else:
        words = drop_tail(words)
    return kind, " ".join(words)


def main(seed: int, n: int) -> None:
    print("RULES", rules.__file__)
    rng = random.Random(seed)
    tried = fuzzy = 0
    closed = []
    for _ in range(n):
        k = rng.randint(2, 4)
        sep = rng.choice([". ", "; ", " · ", ", "])
        segs = segs_for(rng, k)
        body = rng.choice(["", "pricing: ", "compare plans. "]) + sep.join(segs) + "."
        lo = rng.randrange(k)
        hi = rng.randint(lo + 1, k)
        kind, quote = edit(rng, sep.join(segs[lo:hi]))
        if rules.normalize(quote) in rules.normalize(body):
            continue
        tried += 1
        v, m, note = verify(quote, body)
        if m == "quote_fuzzy":
            fuzzy += 1
        if not v and note and "numbers differ" in note:
            closed.append((kind, body, quote, note))
    print(
        f"seed={seed} true quotes tried={tried} (fuzzy-verified {fuzzy}) "
        f"rejected-for-numbers={len(closed)}"
    )
    for row in closed:
        print("CLOSED", row)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
