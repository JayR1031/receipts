# The verifier

> Moved here from the README on 2026-11-18 (PR #53). Updated on 2026-11-19 for issue #45: the
> number rules (a) to (d), the repair rule (i), the known limits and the measurement. The README
> keeps the summary table.

`src/receipts/verify/rules.py` is pure: no clock, no network, no model call. Before matching it
*normalizes* both the quote and the page: markdown stripped, curly quotes and dashes unified,
lower-cased, whitespace collapsed.

| Receipt | Check | Outcome | Note on the claim |
|---|---|---|---|
| Quote | URL was not fetched this run | not verified (dropped) | `dropped: url not fetched this run` |
| Quote | Page fetch failed | not verified | `fetch failed` (not "false") |
| Quote | Quote is an exact substring of the page | `quote_exact` | none |
| Quote | Exact substring, but an edge of the match cuts a page number (`$19` inside `$199`) | falls through to the fuzzy check | |
| Quote | Fuzzy match: `rapidfuzz` `partial_ratio` at least 90, the match covers the whole quote, and each number in the quote is the page's number at the same place in the match | `quote_fuzzy` | `fuzzy match: partial_ratio=… >= 90` |
| Quote | The quote is on the page, but a value in the claim (a price with a currency sign or written out as `25 dollars` or `$ 25`, a `%`, a decimal, a thousands number, or a count such as `500 credits`) is not in the quote | not verified | `claim numbers not in quote: …` |
| Quote | Anything else | not verified | `quote not found on page: …` with the reason |
| Search | Same query, rank and URL as a row logged this run | `search_log` | none |
| Search | Query was never searched this run | not verified (dropped) | `dropped: search query not logged this run` |
| Search | Query logged, but no row with that rank and URL | not verified | `no logged row for query at rank N with that url` |

**The number rules, in plain words** (PR #35, and issue #45 for (a) to (d)):
- **Why fuzzy needs a number rule:** a one-digit price change still scores about 97 on fuzzy matching. So each number in the quote, with its currency sign or `%`, must be the page's number at the same place in the match. A quote that swaps or repeats the page's prices fails.
- **The claim has to match its quote:** every value in the claim must also be in its quote. A value is a price written with a currency sign (`$20`, `€5`), a percentage, a decimal, a number with a thousands separator, an unsigned price or a count (both below). A quote proves only what it says. Any other whole number, such as a year (`As of 2025`), a plan or model name (`Pro 2`, `GPT-4`) or `24/7`, is not checked.
- **(a) Counts with units:** a whole number followed by one of ten units is a value: credit, seat, user, member, project, message, request, token, minute or hour, singular or plural. Nothing, a space or a hyphen may sit between them, or one other word (`500 credits`, `50-seat`, `5 active users`). So "Max includes 500 credits." is not verified by the quote "Max includes 18,000 credits", and "18000 credits" is.
- **(b) "free":** the word *free* in the quote matches a zero price in the claim (`$0`, `$0.00`, `0 dollars`) and nothing else. A negated free does not count: `not`, `no`, `never`, `isn't`, `isnt`, `aren't`, `arent`, `without` or `non` among the two words before it ("not free", "no free plan", "non-free"). Nor does a trial: `trial` or `trials` directly after it ("free trial", "free-trials"). So "Starter is $0." is not verified by "Starter is not free" or "Start a free trial", and it still is by "Starter is free".
- **(c) Unsigned prices, in the claim rule only:** `25 dollars`, `25 USD`, `USD 25`, `$ 25` and `25 €` are read as `$25` or `€25`, in the claim and, for this rule, in the quote. The other spellings read are `dollar`, `euro`, `euros`, `eur`, `gbp`, `jpy` and `yen` after the number, and `eur`, `gbp` and `jpy` before it. So "Pro costs 25 dollars." is not verified by the quote "Pro costs $20", and "Pro costs $25." is verified by "Pro costs 25 dollars". In the quote the reading is added to the quote's own numbers, so a quote "25 dollars" also backs a claim's count `25 seats`. The quote-to-page match does not use this reading (a limit, below).
- **(d) Suffixes, trailing signs and leading decimals, in both rules:** `$20k`, `$1.2M`, `25$` and `$.99` are one number each, equal to `$20,000`, `$1,200,000`, `$25` and `$0.99`. The suffix is `k`, `m` or `b`, in either case, directly after a number with a currency sign in front, and no letter or digit may follow it, so `$5/mo` and `$5 max` stay `$5`. A sign that a number follows leads that number: `5$20` is `5` and `$20`. This also closes a gap on the quote side: before issue #45 (at `949741f`), the quote "Enterprise $20" was an exact match on the page "Enterprise $20k a year.", so the claim "Enterprise is $20 a year." verified. Now that quote is a miss: `numbers differ (quote has $20; page has $20k there; …)`.
- **Equivalences:** commas that separate thousands are ignored, so `1,000` equals `1000` (a decimal comma such as `19,99` is kept). `$20.00` equals `$20`, and `20 percent` equals `20%`.
- **The note:** a claim that misses gets `claim numbers not in quote: …`, its values sorted and each named once. Every value is named in its signed reading: `25 dollars`, `$ 25` and `25$` are named `$25`, and `$.99` is `$0.99`. A count is named as written (`500`), and other values as the claim writes them (`$1.2m`, `2,500`).
- **(i) Repairs may not copy a receipt:** within one specialist's claims, a Mellea repair whose receipt is identical to another claim's receipt is not accepted, and the original claim goes to the Verifier unchanged. A repair that keeps its own claim's receipt is accepted, and claims the agent wrote on one receipt all count ([ADR-0007](adr/0007-mellea.md)).

**Known limits.** *Fail-open* means a wrong claim can show as verified; *fail-closed* means a true
claim can show as unverified. The repository owner accepted (e) to (h) on 2026-11-18 (issue #45).
The others follow from how issue #45's rules were drawn: the issue's brief
(`docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md`, its assumptions) and the
owner's answers of 2026-11-19. A rate is given where one was measured, by the random tests below
or a live run. `rules.py`'s module docstring lists the same limits.
- **(e) Plan labels are not checked** (fail-open). Only numbers are compared, so a changed or
  dropped plan name next to a price can attach another plan's real price: the quote "Tier B: $29
  per seat per month" verifies on the page "Tier A: $29 per seat per month. Tier B: $19 per seat
  per month." The same goes for "free": one that is not negated or a trial counts wherever it is,
  so the quote "Starter is free, Pro is $20" backs the claim "Pro is $0." Rates, from PR #35's
  random tests of the quote-to-page rule:
  - 22 of 160,000 quotes generated on two- to four-price pages verified with a price that is not
    its plan's (`fuzz_place2.py`). PR #35's `count_sets.py`, which is not committed, put 109,249
    of the 160,000 as holding a wrong price.
  - 22 of 7,439 misquotes on pages whose own price at the quote's place is a word or a different
    price (`fuzz_skip.py`).
  - 2 of 3,678 add-a-word misquotes that score at least 90, of 10,994 generated (`fuzz_add.py`).
- **(f) True quotes past the score window fail closed.** The fuzzy score's window is at most as
  long as the quote. When the page text a quote matches is longer, the quote's first or last
  number can fall outside it, and the note usually says `page has no number there` although the
  page has it just past the window. Rates: 195 of 5,998 true quotes (`fuzz_place_all.py`) and
  35 of 2,931 on pages dense with prices (`fuzz_dense.py`). A different cause rejects 2 of 6,941
  true quotes that add a word (`fuzz_add.py`). PR #35 tried two wider windows: they rejected
  fewer true quotes that leave text out (5 and 10 of 5,998) but more that add a word (450 and
  333 of 6,941), and let more wrong prices verify. Wrong prices that verify, shipped rules, then
  window A, then window B: `fuzz_place2` 22, 2, 2 of 160,000; `fuzz_skip` 22, 107, 22 of 7,439;
  `fuzz_spread` 0, 67, 1 of 6,000; `fuzz_add` 2, 173, 85 of 3,678. Summed over the four shapes,
  which have different denominators, that is 46, 349 and 110 (issue #45, comment of 2026-11-15
  07:55 UTC).
- **(g) Values swapped inside one quote still verify** (fail-open). The claim rule checks that
  each value is in the quote, not which plan or billing term it belongs to: the claim "Pro is $19
  a year and $199 a month." verifies on the quote "Pro yearly: $199. Pro monthly: $19."
- **(h) A repair can carry a plan name its quote lacks** (fail-open). Mellea rewrites a failing
  claim, at most twice, aiming for one the verifier accepts, and (e) lets the rewrite name a
  plan its quote does not. In the live run `run-a7be7a53cba9` (Mel vs Warp, repairs on,
  2026-11-15), at least 6 of the 8 verified pricing claims did.
- **A count compares its value, not its unit** (fail-open): `500 seats` in the quote backs
  `500 credits` in the claim. Only the ten units count, with at most one word before them, so
  `30 days` and `5 very active users` are not checked.
- **A bare number before a unit is read as a count** (fail-closed): "Pro costs 25 per seat." (no
  sign) has the count `25`, which the quote "Pro costs $25 per seat" does not back; "In 2025
  users" and "GPT-4 tokens" make `2025` and `4` values the quote must carry.
- **A whole number with no unit is not checked** (fail-open, by design): a changed year, plan
  number, model number or `24/7` verifies. 300 of 300 such wrong claims verify in the `control`
  shape below.
- **Unsigned spellings outside rule (c)'s lists are not prices:** "pounds" (often a weight),
  "bucks" and number words. In the claim they are not checked (fail-open: "Pro costs 25 pounds."
  verifies on the quote "Pro costs £20"); in the quote "25 pounds" does not back a claim's `£25`
  (fail-closed).
- **The quote-to-page match reads no unsigned price** (fail-closed; the owner's choice of
  2026-11-18): the quote "Pro costs 20 dollars" on the page "Pro costs $20." is a miss.
- **Suffix forms out of scope:** `bn`, `mm`, `million` and `thousand`, a space before the
  suffix, a suffix on a number with no sign, and a decimal comma before a suffix. `$20bn`,
  `$20 million` and `$20 k` read `$20`, so the claim "Enterprise is $20 million." verifies on the
  quote "Enterprise $20 per seat", and the quote "Enterprise $20" is an exact match on the page
  "Enterprise $20 million a year." (fail-open). `$1,5k` is compared as written and misses
  `$1,500` (fail-closed).
- **A quote cut mid-word at a suffix letter** (both ways; the owner's decision of 2026-11-19):
  the quote "Pro costs $5m", cut from the page "Pro costs $5mo for every seat.", is an exact
  match, and its `$5m` reads five million while the page's reads `$5`. So the true claim "Pro
  costs $5." is rejected (fail-closed) and the wrong claim "Pro costs $5,000,000." verifies
  (fail-open).
- **A trial "free" not directly before "trial", and a negation across punctuation:** "Start your
  free 14-day trial" and "Starter is free: trial included" still match a `$0` claim, so a wrong
  `$0` verifies (fail-open; the owner's decision of 2026-11-19). The two-word window runs across
  punctuation, so "No ads, free forever" does not match `$0` and a true `$0` is rejected
  (fail-closed).
- **A copied receipt is caught only exactly, and only within one specialist** (rule (i);
  fail-open): a repair whose quote differs from another claim's only in case or spacing counts
  as a second claim on one piece of evidence, and a copy across domains is not caught, because
  `Coordinator` cannot tell a repair from an original without a contract change.
- **Search receipts skip the claim-number rule** (by design): there is no quote to check the
  claim against, so a price in the claim is not compared with the logged search result.

## The measurement

`scripts/verify_fuzz/` holds the random tests that guarded PR #35 and the claim shapes added for
issue #45. `run_baseline.py` runs them all and compares every count with `expected.txt`, which
names each count's set and denominator.

```bash
uv run python scripts/verify_fuzz/run_baseline.py                     # everything: about 11 s, no network
uv run python scripts/verify_fuzz/run_baseline.py --kinds quote,count # only those groups
```

- **Exit 0:** no count of wrong quotes or claims verified (fail-open) and no count of true ones
  rejected (fail-closed) is above its "at most" value. A count that fell prints `FELL` and does
  not fail; it is reported case by case, and `expected.txt` is not edited to absorb it.
- **Exit 1:** a count rose (`ROSE`) or is missing. Or, checked before anything runs: one of the
  six PR #35 scripts no longer matches its SHA-256 in `pinned.sha256`, a command's seed or sample
  size is not the one `expected.txt` names, or a denominator that no rule can move changed.
- **Exit 2:** an unknown or empty `--kinds` list.

No CI workflow runs it; run it after any change to `src/receipts/verify/`.

**PR #35's six scripts, twelve runs** (the group `quote`). They call `verify_claim` with a claim
that states no number, so they measure only the quote-to-page rule. Their counts are the same on
`949741f`, before issue #45's rules, and on this branch: issue #45 moved none of the 20 counts
(16 per run, 4 totals).

| Command | What it generates | Count |
|---|---|---|
| `fuzz_place_all.py 2 6000` | misquotes (a page price replaced by another, or two swapped, maybe one dropped) and true quotes (words dropped, typos, a price dropped; no number changed) | 0 of 5,998 misquotes verified; 195 of 5,998 true quotes rejected |
| `fuzz_dense.py 9 8000` | true quotes on pages with numbers close together (ranges, "x/mo or y/yr", counts next to prices) | 35 of 2,931 true quotes rejected |
| `fuzz_add.py 51 6000`, `52 6000`, `53 6000 all 1` | quotes that add one or two short words before a plan's price; the misquotes give the plan the next plan's price | 2 of 3,678 misquotes scoring at least 90 verified (10,994 generated); 2 of 6,941 true quotes rejected |
| `fuzz_place2.py 7 40000`, and seeds 11, 12, 13 | quotes from the page's template with prices changed, swapped, repeated or left out, plus letter edits | 22 of 160,000 verified with a wrong price in a plan's place |
| `fuzz_skip.py 5 6000`, `6 6000` | misquotes that give a plan the next plan's price, on pages where some prices are words or another currency | 22 of 7,439 misquotes verified |
| `fuzz_spread.py 1 6000` | misquotes that drop words and then give a label the next label's price | 0 of 6,000 misquotes verified |

Underneath those counts, rule (d) moved 45 of the 160,000 `fuzz_place2.py` quotes from
`quote_fuzzy` to a miss, each a `k`, `m` or `b` letter edit right after a page price, and none
from a miss to verified.

**Issue #45's seven claim shapes** (`fuzz_claim_values.py 45 300 <kind>`). For each kind, 300
cases: a page, a quote that is an exact substring of it (checked for every case), a TRUE claim
that restates the quote's value in an equal spelling and a WRONG claim with a different value.
They measure the claim-against-quote rule. Each count is of 300.

| Kind | WRONG claim | TRUE claim | WRONG verified / TRUE rejected, `949741f` | This branch |
|---|---|---|---|---|
| `count` | `500 credits` against `18,000 credits` | `18000 credits` for `18,000 credits` | 300 / 0 | 0 / 0 |
| `unsigned` | `25 dollars`, `USD 25`, `$ 25`, `25 $` against `$20` or `20 dollars` | `$25` for `25 dollars`, and back | 300 / 104 | 0 / 0 |
| `suffix` | `$20k` against `$20`; `$20` or `$20m` against `$20k`; `$20000k` against `$20,000` | `$20k` for `$20,000`, and back | 300 / 138 | 0 / 0 |
| `trailing` | `30$` against `$25` or `25$` | `25$` for `$25` | 300 / 82 | 0 / 0 |
| `leading_decimal` | `$.49` against `$0.99` or `$.99`; `$.99` against `$99` | `$.99` for `$0.99`, and back | 300 / 55 | 0 / 0 |
| `free` | `$0` against a negated or trial "free" | `$0` for a "free" that is neither | 147 / 0 | 0 / 0 |
| `control` | a changed year, plan number, model number or `24/7` | the quote plus a year or `24/7` it lacks | 300 / 0 | 300 / 0, by design |

On `949741f`'s rules the full run exits 1 with ten `ROSE` lines, every kind but `control` above
its target; on this branch it exits 0 with all 34 lines `ok`. In `free`, 147 of the 300 cases
put a `$0` claim against a negated or trial "free"; the other 153 put a non-zero WRONG price
against a "free" that is neither, which both revisions reject. So its WRONG count on `949741f`
is 147 of 300.

## Worked examples

The outputs below come from running `verify_claim` on each case at commit `d5b02fc`, whose rules
are the ones this page describes. An example that shows no claim used one that states no number,
so only the quote-to-page rule applies. All seven print the same on `949741f`, before issue #45's
rules. The same cases, or close variants, are in `tests/test_verify.py` and
`tests/test_verify_claim_numbers.py`.

<details>
<summary><code>$19.99</code> quoted, page says <code>$19.49</code>: not verified</summary>

```text
page:  Basic is $19.49 per seat per month, billed yearly. Enterprise is $99 per seat.
quote: Basic is $19.99 per seat per month, billed yearly
-> verified=False
   note: quote not found on page: numbers differ (quote has $19.99; page has $19.49 there; partial_ratio=98.0)
```

</details>

<details>
<summary><code>1,000 seats</code> quoted, page says <code>1000 seats</code>: verified</summary>

```text
page:  The team plan includes 1000 seats and audit logs.
quote: 1,000 seats
-> verified=True, method=quote_fuzzy
   note: fuzzy match: partial_ratio=90.9 >= 90
```

</details>

<details>
<summary>Quote longer than the page: not verified</summary>

`partial_ratio` slides the shorter string along the longer one, so a short page can score 100
*inside* a long quote. The match must cover the whole quote.

```text
page:  Pricing
quote: Our pricing is free forever for every team
-> verified=False
   note: quote not found on page: fuzzy match does not cover the whole quote (partial_ratio=100.0 on 7/42 chars)
```

</details>

<details>
<summary>Fetch failed: "fetch failed", not "false"</summary>

```text
page:  (fetch returned ok=False)
quote: anything
-> verified=False
   note: fetch failed
```

A page the run could not read says nothing about whether the claim is true, so the note says so.

</details>

<details>
<summary>Markdown on the page: still an exact match</summary>

```text
page:  # Plans
       - The **Team** plan is [14 dollars](https://md.example/#t) per seat per month — billed yearly.
quote: The Team plan is 14 dollars per seat per month - billed yearly.
-> verified=True, method=quote_exact
```

</details>

<details>
<summary>Claim price not in its quote: not verified</summary>

```text
page:  Build plan. $20 of agent usage included each month at API rates. Cancel any time.
quote: $20 of agent usage included each month at API rates
claim: Warp Build is $18/month on the annual plan and includes $20 of agent usage per month at API rates
-> verified=False
   note: claim numbers not in quote: $18
```

The quote is on the page, but it does not carry the claim's `$18`. The claim and quote come from the run issue #33
reported (`run-0e7ff2b1bb05`); the page text is invented for the test.

</details>

<details>
<summary>Prices swapped inside the quote: not verified</summary>

```text
page:  Pro yearly: $199. Pro monthly: $19.
quote: Pro yearly: $19. Pro monthly: $199.
-> verified=False
   note: quote not found on page: numbers differ (quote has $19, $199; page has $199, $19 there; partial_ratio=97.1)
```

</details>
