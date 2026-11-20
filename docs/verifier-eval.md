# Verifier evaluation

> Issue #59, 2026-11-20. How often a claim the verifier marks verified is really backed by its
> receipt, measured on 231 labeled claims from real runs. The numbers and the CI floors are in
> [docs/verifier.md](verifier.md#how-accurate-is-it); this page is the labeling guide and the
> method.

## The set

`tests/data/verifier_eval/claims.jsonl` holds one row per claim (`receipts.verify.evaluation.EvalRow`):
the claim as the agent or Mellea wrote it, the verifier's result at the time (`recorded`), the
evidence the run saw, and a label with a one-line reason.

| Stage | Rows | What it is | Evidence |
|---|---|---|---|
| `agent` | 113 | the agent's claims, as shown on the battlecard | page excerpt or search rows |
| `repair` | 17 | Mellea rewrites, as shown | page excerpt or search rows |
| `draft` | 17 | the failing drafts those rewrites replaced (`repaired_by`) | page excerpt or search rows |
| `stored` | 84 | the four finished runs stored on the live site (2026-11-15 to 2026-11-20) | none: the app keeps no page text |

The 147 rows with evidence come from six local runs on 2026-11-20 (Notion vs Coda, Figma vs
Sketch, Vercel vs Netlify, Slack vs Microsoft Teams, Duolingo vs Babbel, Canva vs Adobe Express),
recorded with Mellea repairs on. 92 rows are pricing and 139 positioning and SEO; 173 cite a quote
and 58 a search row.

**Evidence is an excerpt, never a whole page.** A quote row keeps a window of the page's raw text
around the best match for its quote (724 to 1,562 characters), widened until the verifier's
result on the excerpt (verified, method and note) is the same as on the full page. A search row
keeps the rows logged for its query. The CI test fails on an excerpt over 4,000 characters.

**People's names are redacted.** Customer testimonials on three pages named their authors; those
names read `[name]`. The list of names lives only in the gitignored `.eval-raw/redact.txt`, and a
row whose verifier result changes under redaction is left out (none was). This is the one
exception to the rule that test fixtures are synthetic (AGENTS.md, Data).

## The labels

A label says whether the **receipt** backs the claim, not whether the claim is true somewhere on
the web.

- **`supported`**: the receipt backs every part of the claim.
- **`unsupported`**: the quote or search row exists, but the claim says something it does not.
- **`wrong`**: the receipt does not match the page or the search log.

**How to read a quote: in place.** Read the quote where it sits on the page. The plan or section
heading it falls under, and the unit or billing line that completes a price in the quote
(`user/month, paid yearly`), count as context. Nothing else on the page does: not the next
bullet, not another table row, not a sentence before or after.

- Context may supply which plan or section, and the unit or billing term of a value in the quote.
- It may not supply a value the quote lacks: a price, a count, a feature, an audience, a trial.
- Framing words are fine when the quote shows them: "positions itself as", "differentiates on",
  "targets". An added specific is not: "aimed at ambitious companies", "expert-designed".
- A claim that says the quote is the headline must cite the headline.

**How to read a search receipt: one row.** The receipt is one row: its query, rank, URL, title
and snippet. A claim about other results ("neither site is in the top 10", "behind dictionary
pages") is `unsupported`, even when the run's log shows it true; the reason then says whether the
log agrees.

**Stored rows: the quote alone.** No page was kept, so a stored row is judged on its quote and
URL, without the in-place context. A plan name or column header that is not in the quote is not
backed. This is stricter than the rule for recorded rows, so stored rows are reported apart.

**Who labeled.** The labels were drafted by an AI assistant (Claude) with a reason on every row,
under the rules above, and reviewed by the repository owner before merge. One labeler, one pass:
no agreement rate between labelers was measured.

### Worked examples

| Claim | Receipt | Label | Why |
|---|---|---|---|
| Figma Professional Full seat is $16/mo. | `#### Full seat $16/mo` | supported | the quote sits under the Professional heading |
| Figma Starter plan is free with limited access, including unlimited drafts. | `Free limited access to Figma products` | unsupported | "unlimited drafts" is a separate bullet |
| Microsoft Teams Essentials is listed at $4.00 per user per month, paid yearly. | `$4.00` | supported | under Teams Essentials; "user/month, paid yearly" is its unit line |
| Babbel Individual Lifetime plan costs $299.99 as a one-time payment. | `One-time payment!` | unsupported | $299.99 is on the line above, a value the quote lacks |
| Slack Pro costs $7.25 per active user per month billed annually, or $8.75 billed monthly. | `$US7.25 per active user … Or $US8.75 …` | supported | the same prices in US dollars; the verifier rejects it (its one miss) |
| Notion targets ambitious companies and claims enterprise adoption. | `62% of Fortune 100 use Notion` | unsupported | "ambitious companies" is not in the quote |
| For 'Sketch', the Sketch homepage ranks only #4, behind dictionary definitions. | row #4, sketch.com | unsupported | the rank is in the row; the dictionaries are other rows (true in the log) |
| Vercel's own pages hold 7 of the top 10 results for 'Vercel'. | row #3, docs.vercel.com | unsupported | other rows, and false: the log shows 8 of 10 |

## What it found

- **The verifier almost never rejects a backed claim.** Recall is 96 of 97. The miss is the
  `$US7.25` spelling, which the claim-number rule does not read as `$7.25`.
- **About one verified claim in four says more than its receipt.** Precision is 96 of 129.
  - 13 of the 33 are search claims comparing other results that the run's log shows true, and 2
    are comparisons the log shows false (the Vercel count above, and a Coda subdomain called a
    third-party guide). The search rule checks that the row exists, not what the claim says
    about the results around it.
  - 17 of the 18 quote claims add words, not numbers: a feature, an audience, a plan name, a
    headline the quote is not. The number rules cannot see these.
  - 1 is a number: the claim's `$20/mo` price matched the quote's `$20` usage credit.
- **Mellea's rewrites narrow claims to their quotes.** All 17 failing drafts were rewritten, and
  all 17 rewrites are `supported`: a rewrite usually drops the value the quote lacked.
- **The stored runs, from before issue #45's rules, are much weaker:** 41 of 82 verified claims
  are backed by their quote alone. 24 of the 41 misses are from the two Mel vs Warp runs, 15 of
  them prices, as the README's demo section describes.

So the next check to build is one that reads the words, not just the numbers: whether the quote
entails the claim (a natural-language-inference model, or a model judge), and for search claims,
whether the claim asserts anything beyond its one row. This set is the baseline it has to beat.

## Limits

- 147 re-run rows from six pairs and one day; pages as fetched on 2026-11-20.
- Only 18 of the 147 claims were rejected, so recall rests on 97 supported claims and the
  `unsupported`-and-rejected cell on 17.
- One labeler (an AI assistant, reviewed by the owner).
- No `wrong` labels: every recorded quote was on its page and every search row in the log, because
  the verifier drops the others before the battlecard. A `wrong` row would need a recorded claim
  the agent cited from a page it never fetched.

## Rebuild or extend it

```bash
uv run python scripts/verifier_eval/record.py            # live: six pairs, about 4 minutes, needs keys
uv run python scripts/verifier_eval/build_dataset.py --stored https://receipts-h745.onrender.com
uv run python scripts/verifier_eval/report.py            # offline: the tables in docs/verifier.md
uv run pytest tests/test_verify_eval.py                  # the CI gate
```

`record.py` writes full snapshots to the gitignored `.eval-raw/`. `build_dataset.py` keeps the
labels of rows it has seen (by id), so a new row arrives unlabeled and the gate's "every row is
labeled" test fails until it gets a label and a reason.
