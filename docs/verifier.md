# The verifier

> Moved here from the README on 2026-11-18, unchanged. The README keeps the summary table.

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
| Quote | The quote is on the page, but a value in the claim (a price written with a currency sign, a `%`, a decimal or a thousands number) is not in the quote | not verified | `claim numbers not in quote: …` |
| Quote | Anything else | not verified | `quote not found on page: …` with the reason |
| Search | Same query, rank and URL as a row logged this run | `search_log` | none |
| Search | Query was never searched this run | not verified (dropped) | `dropped: search query not logged this run` |
| Search | Query logged, but no row with that rank and URL | not verified | `no logged row for query at rank N with that url` |

**The number rules, in plain words** (PR #35):
- **Why fuzzy needs a number rule:** a one-digit price change still scores about 97 on fuzzy matching. So each number in the quote, with its currency sign or `%`, must be the page's number at the same place in the match. A quote that swaps or repeats the page's prices fails.
- **The claim has to match its quote:** every value in the claim must also be in its quote: a price written with a currency sign (`$20`, `€5`), a percentage, a decimal, or a number with a thousands separator. A quote proves only what it says.
- **Equivalences:** commas that separate thousands are ignored, so `1,000` equals `1000` (a decimal comma such as `19,99` is kept). `$20.00` equals `$20`, and `20 percent` equals `20%`.

The rules have known limits. Issue #45 tracks all but the last; the last is by design and is
described in `rules.py`'s docstring:
- Plan labels next to a price are not checked.
- Bare-integer counts (`500 credits`) and prices with no sign attached (`25 dollars`, `25 USD`,
  `$ 25`) in the claim are not checked.
- A suffixed or trailing-sign price in the claim (`$20k`, `$1.2M`, `25$`, `$.99`) is read as `$20`,
  `$1.2` or not at all, so it can verify against a quote that lacks it.
- Any standalone "free" in the quote matches a `$0` claim, including "not free".
- A claim that swaps two values its quote carries still verifies.
- A true quote whose page text runs past the score window can be rejected.
- Claims backed by a search receipt skip the claim-number rule: there is no quote to check the claim
  against, so a price in the claim is not compared with the logged search result.

The outputs below come from running `verify_claim` on each case at commit `d719360`; the same
cases, or close variants, are in `tests/test_verify.py` and `tests/test_verify_claim_numbers.py`.

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
