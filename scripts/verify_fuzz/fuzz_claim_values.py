"""Issue #45 claim-value shapes: does the claim rule check the value a claim states?

For each kind it builds n cases. A case is a page, a quote that is an exact substring of that page
(so the quote-to-page rule gives `quote_exact`), and two claims that cite the quote:
- a TRUE claim, restating the quote's value in a spelling the brief says is equal after issue #45
  (`18000 credits` for `18,000 credits`, `$25` for `25 dollars`, `$20k` for `$20,000`, `25$` for
  `$25`, `$.99` for `$0.99`, `$0` for an unnegated "free");
- a WRONG claim, stating a different value in a spelling the brief names as a gap on 949741f.

Kinds (brief docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md, rules (a) to (d) and
assumptions 1, 3, 6, 7 and 8):
  count            (a) `500 credits` against `18,000 credits`, in every spacing of assumption 1
  unsigned         (c) `25 dollars`, `USD 25`, `$ 25`, `25 $` against `$20` or `20 dollars`
  suffix           (d) `$20k` against `$20`; `$20` or `$20m` against `$20k`; `$20000k` against
                   `$20,000`
  trailing         (d) `30$` against `$25` or `25$`
  leading_decimal  (d) `$.49` against `$0.99` or `$.99`; `$.99` against `$99`
  free             (b) `$0` against a negated or trial "free" (negation words of assumption 8)
  control          bare non-count integers stay unchecked (a year, `Pro 2`, `GPT-4`, `24/7`), as
                   test_bare_integers_in_the_claim_are_not_checked pins: the WRONG claim changes
                   that integer and verifies by design; the TRUE claim adds one the quote lacks

Two sub-shapes are guards that hold on 949741f too, because one quote serves both claims: in
`free`, a quote with an unnegated "free" gets a WRONG non-zero price, and a quote with a negated
or trial "free" gets a TRUE claim restating its real price. The SHAPE lines count each sub-shape.

Each kind draws from random.Random(f"{seed}:{kind}"), so a kind run alone gives the cases it gives
in a run of every kind. Every case verifies exactly one WRONG and one TRUE claim, with no skip, so
both denominators are n per kind whatever the rules do. Every case's quote is also verified with a
claim that states no number; if any is not `quote_exact`, the script exits 3 after printing, since
it would then measure the quote-to-page rule instead of the claim rule.

Only the public API is called: receipts.verify.verify_claim and the receipts.contracts types.
Usage: fuzz_claim_values.py [seed n [kind]]   (default: 45 300, every kind)
"""

from __future__ import annotations

import inspect
import random
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from receipts.contracts import Claim, FetchedPage, QuoteReceipt
from receipts.verify import verify_claim

SEED, N = 45, 300
EXAMPLES = 2
T0 = datetime(2026, 11, 18, tzinfo=UTC)
URL = "https://fuzz.example/claims"
PROBE = "Probe claim."  # states no number, so its outcome is the quote-to-page rule alone
PLANS = ("Starter", "Basic", "Team", "Pro", "Business", "Max", "Plus", "Growth", "Scale", "Lite")
INTROS = ("", "Compare the plans below. ", "Prices exclude tax. ", "Billing is monthly or yearly. ")
OUTROS = ("", " Cancel any time.", " Taxes are extra.", " Contact sales for volume pricing.")
SIGNS = ("$", "€", "£", "¥")
AMOUNTS = (5, 8, 9, 10, 12, 15, 19, 20, 25, 29, 30, 49, 99, 199)
# No unit word (assumption 1) in a price claim's tail, so a count reading cannot meet a price.
PRICE_TAILS = (" a month", " per month", " a year", " per year")


@dataclass(frozen=True)
class Case:
    quote: str
    true_claim: str
    wrong_claim: str
    true_shape: str
    wrong_shape: str


@dataclass(frozen=True)
class Prices:
    """The quote's price and the two claims' prices, each with its sign or unsigned spelling."""

    quote: str
    true: str
    wrong: str
    true_shape: str
    wrong_shape: str


@dataclass
class Tally:
    cases: int = 0
    exact: int = 0
    wrong_verified: int = 0
    wrong_tried: int = 0
    true_rejected: int = 0
    true_tried: int = 0
    shapes: dict[str, list[int]] = field(default_factory=dict)  # label -> [hits, tried]
    examples: list[str] = field(default_factory=list)


def priced(plan: str, tail: str, p: Prices) -> Case:
    """`<plan> costs <price><tail>` for the quote and both claims."""
    lead = f"{plan} costs "
    return Case(
        f"{lead}{p.quote}{tail}",
        f"{lead}{p.true}{tail}.",
        f"{lead}{p.wrong}{tail}.",
        p.true_shape,
        p.wrong_shape,
    )


# --- count: (a), assumption 1 -------------------------------------------------------------

UNITS = ("credit", "seat", "user", "member", "project", "message", "request", "token")
UNITS += ("minute", "hour")
COUNTS = (5, 10, 25, 50, 100, 250, 500, 1000, 1500, 2500, 5000, 10000, 18000, 50000, 100000)
FILLERS = ("active", "monthly", "extra", "hosted-ai")
JOINS = ("space", "hyphen", "joined", "one-word-between")


def count_phrase(rng: random.Random, number: str, unit: str, join: str) -> str:
    """`includes 500 credits`, `includes 500credits`, `includes 500 active credits` or
    `is a 500-credit plan`; the unit singular or plural."""
    if join == "hyphen":
        return f"is a {number}-{unit} plan"
    word = unit if rng.random() < 0.25 else f"{unit}s"
    if join == "joined":
        return f"includes {number}{word}"
    if join == "one-word-between":
        return f"includes {number} {rng.choice(FILLERS)} {word}"
    return f"includes {number} {word}"


def grouped(value: int, separator: bool) -> str:
    return f"{value:,}" if separator else str(value)


def grouping(value: int, quote_sep: bool, claim_sep: bool) -> str:
    if value < 1000 or quote_sep == claim_sep:
        return "same-spelling"
    return "claim-drops-separator" if quote_sep else "claim-adds-separator"


def count_case(rng: random.Random) -> Case:
    """The quote states a count; WRONG states another count with the same unit, no separator."""
    plan, unit = rng.choice(PLANS), rng.choice(UNITS)
    right, wrong = rng.sample(COUNTS, 2)
    quote_sep, claim_sep = rng.random() < 0.5, rng.random() < 0.5
    quote_join, true_join, wrong_join = rng.choices(JOINS, k=3)
    return Case(
        f"{plan} {count_phrase(rng, grouped(right, quote_sep), unit, quote_join)}",
        f"{plan} {count_phrase(rng, grouped(right, claim_sep), unit, true_join)}.",
        f"{plan} {count_phrase(rng, str(wrong), unit, wrong_join)}.",
        grouping(right, quote_sep, claim_sep),
        f"bare-count:{wrong_join}",
    )


# --- unsigned: (c), assumption 3 ----------------------------------------------------------

UNSIGNED = {  # sign -> (words after the number, words before it)
    "$": (("dollar", "dollars", "USD"), ("USD",)),
    "€": (("euro", "euros", "EUR"), ("EUR",)),
    "£": (("GBP",), ("GBP",)),
    "¥": (("JPY", "yen"), ("JPY",)),
}
FORMS = ("word-after", "word-before", "sign-space", "space-sign")
UNSIGNED_SHAPES = (
    "signed-quote/unsigned-claim",
    "unsigned-quote/signed-claim",
    "unsigned-quote/unsigned-claim",
)


def unsigned(rng: random.Random, sign: str, amount: int) -> tuple[str, str]:
    """`25 dollars`, `USD 25`, `$ 25` or `25 $` (each read as `$25` after (c)), and its form."""
    form = rng.choice(FORMS)
    after, before = UNSIGNED[sign]
    if form == "word-after":
        return f"{amount} {rng.choice(after)}", form
    if form == "word-before":
        return f"{rng.choice(before)} {amount}", form
    return (f"{sign} {amount}" if form == "sign-space" else f"{amount} {sign}"), form


def unsigned_case(rng: random.Random) -> Case:
    """WRONG states another price unsigned; TRUE respells the quote's price, signed or not."""
    plan, sign, tail = rng.choice(PLANS), rng.choice(SIGNS), rng.choice(PRICE_TAILS)
    right, wrong = rng.sample(AMOUNTS, 2)
    shape = rng.choice(UNSIGNED_SHAPES)
    quote_side, true_side = shape.split("/")
    signed = f"{sign}{right}"
    quote = signed if quote_side == "signed-quote" else unsigned(rng, sign, right)[0]
    true = signed if true_side == "signed-claim" else unsigned(rng, sign, right)[0]
    wrong_text, form = unsigned(rng, sign, wrong)
    prices = Prices(quote, true, wrong_text, shape, f"{quote_side}/unsigned-claim:{form}")
    return priced(plan, tail, prices)


# --- suffix: (d), assumption 6 ------------------------------------------------------------

POWERS = {"k": 3, "m": 6, "b": 9}
MANTISSAS = ("2", "5", "10", "12", "20", "25", "50", "150", "1.2", "1.5", "2.5", "7.5")
SUFFIX_TAILS = (" a year", " per year", " per month", " annually", " for the first year")


def suffixed(rng: random.Random, mantissa: str, suffix: str) -> str:
    return mantissa + (suffix.upper() if rng.random() < 0.3 else suffix)


def expanded(rng: random.Random, mantissa: str, suffix: str) -> str:
    """`20` with `k` -> `20,000` or `20000`; `1.2` with `m` -> `1,200,000` or `1200000`."""
    value = int(Decimal(mantissa) * 10 ** POWERS[suffix])
    return f"{value:,}" if rng.random() < 0.7 else str(value)


def plain_quote(rng: random.Random, mantissa: str, suffix: str) -> Prices:
    """Quote `$20`: WRONG `$20k` (the claim side of (d)); TRUE `$20` or `$20.00`."""
    zero = ".00" if "." not in mantissa and rng.random() < 0.5 else ""
    wrong = suffixed(rng, mantissa, suffix)
    return Prices(
        mantissa, mantissa + zero, wrong, "plain-claim/plain-quote", "suffix-claim/plain-quote"
    )


def suffix_quote(rng: random.Random, mantissa: str, suffix: str) -> Prices:
    """Quote `$20k`: WRONG `$20` or `$20m` (the quote side of (d)); TRUE `$20,000` or `$20K`."""
    quote = suffixed(rng, mantissa, suffix)
    if rng.random() < 0.5:
        true, true_shape = expanded(rng, mantissa, suffix), "full-claim/suffix-quote"
    else:
        true, true_shape = suffixed(rng, mantissa, suffix), "suffix-claim/suffix-quote"
    if rng.random() < 0.5:
        return Prices(quote, true, mantissa, true_shape, "plain-claim/suffix-quote")
    other = suffixed(rng, mantissa, rng.choice([s for s in POWERS if s != suffix]))
    return Prices(quote, true, other, true_shape, "other-suffix-claim/suffix-quote")


def full_quote(rng: random.Random, mantissa: str, suffix: str) -> Prices:
    """Quote `$20,000`: TRUE `$20k`; WRONG `$20000k`, the quote's digits with a suffix."""
    quote = expanded(rng, mantissa, suffix)
    true = suffixed(rng, mantissa, suffix)
    wrong = quote.replace(",", "") + "k"
    return Prices(
        quote, true, wrong, "suffix-claim/full-quote", "suffix-on-digits-claim/full-quote"
    )


SUFFIX_QUOTES = (plain_quote, suffix_quote, full_quote)


def suffix_case(rng: random.Random) -> Case:
    plan, sign, tail = rng.choice(PLANS), rng.choice(SIGNS), rng.choice(SUFFIX_TAILS)
    mantissa, suffix = rng.choice(MANTISSAS), rng.choice(tuple(POWERS))
    p = rng.choice(SUFFIX_QUOTES)(rng, mantissa, suffix)
    signed = Prices(sign + p.quote, sign + p.true, sign + p.wrong, p.true_shape, p.wrong_shape)
    return priced(plan, tail, signed)


# --- trailing: (d), assumption 7 ----------------------------------------------------------


def trailing_case(rng: random.Random) -> Case:
    """WRONG `30$` against `$25` or `25$`; TRUE `25$` for `$25`, or `$25` or `25$` for `25$`."""
    plan, sign, tail = rng.choice(PLANS), rng.choice(SIGNS), rng.choice(PRICE_TAILS)
    right, wrong = rng.sample(AMOUNTS, 2)
    lead, trail, wrong_trail = f"{sign}{right}", f"{right}{sign}", f"{wrong}{sign}"
    if rng.random() < 0.5:
        shape = "trailing-claim/leading-quote"
        return priced(plan, tail, Prices(lead, trail, wrong_trail, shape, shape))
    true, shape = rng.choice(
        ((lead, "leading-claim/trailing-quote"), (trail, "trailing-claim/trailing-quote"))
    )
    wrong_shape = "trailing-claim/trailing-quote"
    return priced(plan, tail, Prices(trail, true, wrong_trail, shape, wrong_shape))


# --- leading_decimal: (d), assumption 7 ---------------------------------------------------

CENTS = ("05", "19", "25", "39", "49", "75", "89", "95", "99")
DECIMAL_SIGNS = ("$", "€", "£")


def leading_decimal_prices(rng: random.Random, sign: str) -> Prices:
    right, wrong = rng.sample(CENTS, 2)
    zero, short, wrong_short = f"{sign}0.{right}", f"{sign}.{right}", f"{sign}.{wrong}"
    form = rng.choice(("zero", "short", "whole"))
    if form == "zero":
        shape = "short-claim/zero-quote"
        return Prices(zero, short, wrong_short, shape, shape)
    if form == "whole":  # quote `$99`; WRONG `$.99`, the same digits as a different value
        whole = f"{sign}{int(right)}"
        true = whole + (".00" if rng.random() < 0.5 else "")
        return Prices(whole, true, short, "whole-claim/whole-quote", "short-claim/whole-quote")
    true, shape = rng.choice(((zero, "zero-claim/short-quote"), (short, "short-claim/short-quote")))
    return Prices(short, true, wrong_short, shape, "short-claim/short-quote")


def leading_decimal_case(rng: random.Random) -> Case:
    plan, sign, tail = rng.choice(PLANS), rng.choice(DECIMAL_SIGNS), rng.choice(PRICE_TAILS)
    return priced(plan, tail, leading_decimal_prices(rng, sign))


# --- free: (b), assumption 8 --------------------------------------------------------------

NEGATED = (  # (shape, quote): only a negated or trial "free", beside the plan's real price
    ("not", "{plan} is not free: it costs {price} a month"),
    ("isn't", "{plan} isn't free, it costs {price} a month"),
    ("isnt", "{plan} isnt free and costs {price} a month"),
    ("never", "{plan} is never free and costs {price} a month"),
    ("not-two-words-before", "{plan} is not really free: it costs {price} a month"),
    ("no", "There is no free plan, and {plan} costs {price} a month"),
    ("aren't", "{plan} plans aren't free and cost {price} a month"),
    ("arent", "{plan} plans arent free and cost {price} a month"),
    ("without-two-words-before", "{plan} comes without a free tier and costs {price} a month"),
    ("trial", "Start a free trial, then {plan} costs {price} a month"),
    ("trial", "{plan} has a free trial and then costs {price} a month"),
)
UNNEGATED = (  # (shape, quote): a "free" that is neither negated nor a trial
    ("free", "{plan} is free"),
    ("free", "{plan} is free for small teams"),
    ("free", "The {plan} plan is free forever"),
    ("negation-after", "{plan} is free and shows no ads"),
    ("negation-five-words-before", "No card needed, and {plan} is free"),
    ("trial-elsewhere", "{plan} is free, and {other} has a free trial"),
)
ZEROS = ("$0", "$0.00", "€0", "£0", "¥0")
FREE_PRICES = ("$9", "$12", "$15", "$19", "$29", "€9", "£8")
NONZERO = ("$5", "$9", "$0.50", "€5")


def free_case(rng: random.Random) -> Case:
    """WRONG `$0` against a negated or trial "free"; TRUE `$0` against an unnegated one."""
    plan, other = rng.sample(PLANS, 2)
    zero = rng.choice(ZEROS)
    if rng.random() < 0.5:
        shape, template = rng.choice(NEGATED)
        price = rng.choice(FREE_PRICES)
        quote = template.format(plan=plan, price=price)
        true, wrong = f"{plan} costs {price} a month.", f"{plan} is {zero}."
        return Case(quote, true, wrong, f"price-claim/{shape}-free", f"zero-claim/{shape}-free")
    shape, template = rng.choice(UNNEGATED)
    quote = template.format(plan=plan, other=other)
    true, wrong = f"{plan} is {zero}.", f"{plan} is {rng.choice(NONZERO)}."
    return Case(quote, true, wrong, f"zero-claim/{shape}", "nonzero-claim/unnegated-free")


# --- control: bare non-count integers, test_bare_integers_in_the_claim_are_not_checked -------

YEARS = tuple(range(2019, 2027))
NUMBERS = (2, 3, 4, 5)
MODELS = ("GPT-{}", "Llama {}", "Gemini {}")
SUPPORT = ("24/5", "12/5", "8/5")
CONTROL_PRICES = ("$9", "$12", "$19", "$20", "$29", "$49", "€19", "£15")


def year_control(rng: random.Random, plan: str, price: str) -> Case:
    year, other = rng.sample(YEARS, 2)
    body = f"{plan} costs {price}/month"
    return Case(
        f"As of {year}, {body}",
        f"As of {year}, {body}, with 24/7 support.",
        f"As of {other}, {body}.",
        "same-year+24/7-not-in-quote",
        "other-year",
    )


def plan_control(rng: random.Random, plan: str, price: str) -> Case:
    number, other = rng.sample(NUMBERS, 2)
    year = rng.choice(YEARS)
    return Case(
        f"{plan} {number} costs {price}/month",
        f"As of {year}, {plan} {number} costs {price}/month.",
        f"{plan} {other} costs {price}/month.",
        "same-plan-number+year-not-in-quote",
        "other-plan-number",
    )


def model_control(rng: random.Random, plan: str, price: str) -> Case:
    model, year = rng.choice(MODELS), rng.choice(YEARS)
    number, other = rng.sample(NUMBERS, 2)
    tail = f"for {price}/month"
    return Case(
        f"{plan} includes {model.format(number)} {tail}",
        f"As of {year}, {plan} includes {model.format(number)} {tail}.",
        f"{plan} includes {model.format(other)} {tail}.",
        "same-model+year-not-in-quote",
        "other-model-number",
    )


def support_control(rng: random.Random, plan: str, price: str) -> Case:
    year, other = rng.choice(YEARS), rng.choice(SUPPORT)
    tail = f"support for {price}/month"
    return Case(
        f"{plan} adds 24/7 {tail}",
        f"As of {year}, {plan} adds 24/7 {tail}.",
        f"{plan} adds {other} {tail}.",
        "same-24/7+year-not-in-quote",
        "other-support-hours",
    )


CONTROLS = (year_control, plan_control, model_control, support_control)


def control_case(rng: random.Random) -> Case:
    plan, price = rng.choice(PLANS), rng.choice(CONTROL_PRICES)
    return rng.choice(CONTROLS)(rng, plan, price)


KINDS: dict[str, Callable[[random.Random], Case]] = {
    "count": count_case,
    "unsigned": unsigned_case,
    "suffix": suffix_case,
    "trailing": trailing_case,
    "leading_decimal": leading_decimal_case,
    "free": free_case,
    "control": control_case,
}


# --- measuring ------------------------------------------------------------------------------


def on_page(rng: random.Random, quote: str) -> str:
    """The page: the quote as one sentence, with or without a sentence before and after it."""
    return f"{rng.choice(INTROS)}{quote}.{rng.choice(OUTROS)}"


def verify(text: str, quote: str, page: str) -> Claim:
    receipt = QuoteReceipt(url=URL, quote=quote)
    claim = Claim(domain="pricing", about="rival", text=text, receipt=receipt)
    fetched = FetchedPage(url=URL, text=page, fetched_at=T0, ok=True)
    return verify_claim(claim, {URL: fetched}, [])


def bump(shapes: dict[str, list[int]], label: str, hit: bool) -> None:
    row = shapes.setdefault(label, [0, 0])
    row[0] += int(hit)
    row[1] += 1


def example(case: Case, page: str, probe: Claim, true: Claim, wrong: Claim) -> str:
    return (
        f"method={probe.verify_method} page={page!r} quote={case.quote!r} "
        f"TRUE={case.true_claim!r} verified={true.verified} "
        f"WRONG={case.wrong_claim!r} verified={wrong.verified} note={wrong.verify_note!r}"
    )


def record(tally: Tally, case: Case, page: str) -> None:
    probe = verify(PROBE, case.quote, page)
    true = verify(case.true_claim, case.quote, page)
    wrong = verify(case.wrong_claim, case.quote, page)
    tally.cases += 1
    tally.exact += int(probe.verify_method == "quote_exact")
    tally.true_tried += 1
    tally.true_rejected += int(not true.verified)
    tally.wrong_tried += 1
    tally.wrong_verified += int(wrong.verified)
    bump(tally.shapes, f"TRUE {case.true_shape} rejected", not true.verified)
    bump(tally.shapes, f"WRONG {case.wrong_shape} verified", wrong.verified)
    if len(tally.examples) < EXAMPLES:
        tally.examples.append(example(case, page, probe, true, wrong))


def run_kind(kind: str, seed: int, n: int) -> Tally:
    rng = random.Random(f"{seed}:{kind}")
    tally = Tally()
    for _ in range(n):
        case = KINDS[kind](rng)
        record(tally, case, on_page(rng, case.quote))
    return tally


def report(kind: str, tally: Tally) -> None:
    print(f"kind={kind} quotes quote_exact on their page {tally.exact} of {tally.cases}")
    print(f"kind={kind} WRONG claims verified {tally.wrong_verified} of {tally.wrong_tried}")
    print(f"kind={kind} TRUE claims rejected {tally.true_rejected} of {tally.true_tried}")
    for label, (hits, tried) in sorted(tally.shapes.items()):
        print(f"SHAPE kind={kind} {label} {hits} of {tried}")
    for i, line in enumerate(tally.examples):
        print(f"EX kind={kind} case={i} {line}")


def parse_args(argv: list[str]) -> tuple[int, int, list[str]] | None:
    """`(seed, n, kinds)`, or None when the arguments are not `[seed n [kind]]`."""
    if len(argv) not in (0, 2, 3) or not all(a.isdigit() for a in argv[:2]):
        return None
    seed, n = (int(argv[0]), int(argv[1])) if argv else (SEED, N)
    kinds = argv[2:] or list(KINDS)
    return (seed, n, kinds) if all(k in KINDS for k in kinds) else None


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args is None:
        print(f"usage: fuzz_claim_values.py [seed n [kind]]; kinds: {list(KINDS)}", file=sys.stderr)
        return 2
    seed, n, kinds = args
    print(f"seed={seed} n={n} kinds={','.join(kinds)}")
    print("RULES", inspect.getfile(verify_claim))
    broken = []
    for kind in kinds:
        tally = run_kind(kind, seed, n)
        report(kind, tally)
        if tally.exact != tally.cases:
            broken.append(f"kind={kind} {tally.cases - tally.exact} of {tally.cases}")
    if broken:
        print(f"quotes not quote_exact on their page: {'; '.join(broken)}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
