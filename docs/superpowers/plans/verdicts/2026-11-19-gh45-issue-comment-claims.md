# Verdict: gh45 issue #45 comment draft, round 1 (claims-judge, fresh context, 2026-11-19)

Draft: scratch `gh45-drafts/issue-45-comment.md` (not durable; its posted form is the record). Head `3b16d84`, base `949741f`. Saved by the orchestrator from the claims-judge's final message; the claims table condensed, findings verbatim.

VERDICT: FAIL

The numbers in the comment are right (every one re-measured on both revisions and holds), but it must change before posting. Three causes: six before-and-after claims ("no longer verifies", "now verifies", "now a miss", "now closed", "moved 45") name no artifact or revision; one count is wrong ("nine task verdicts"; there are twelve); and the (i) rule replaces an owner decision the issue still records, without saying so.

## What the judge re-ran (read-only)
`git diff --stat 923c5af 3b16d84 -- src tests scripts README.md` empty; `git diff --exit-code 641eadd 3b16d84 -- scripts/verify_fuzz` exit 0; `run_baseline.py` on `3b16d84` exit 0, 34 of 34 `ok`, identical to the evidence file; the same with `949741f`'s `src/` first on `PYTHONPATH`: exit 1, exactly the 10 claim-shape `ROSE` lines, the 20 quote lines byte-identical to the head's; only the four `fuzz_place2.py` `verified_fuzzy` lines differ (6568→6557, 6726→6715, 6656→6641, 6537→6529, −45); 32 `verify_claim` probes on head and base; `gh issue view 45` (OPEN; body plus 5 comments on 2026-11-15).

## Claims checked: 23, all numerically true. Results that are not a clean "holds": claims 4, 5, 6, 10, 14 true but with no artifact or revision named; claim 13 ambiguous set; claim 21 false number ("nine"); claim 8 omits the replaced owner decision.

## Findings (verbatim)

### HIGH
**H1 (I1, Rule Zero).** `draft:4`, `draft:5`, `draft:6` say "no longer verifies", "now verifies" and "is still a miss", but name no artifact and no revision pair. Support: whole-PR verdict `docs/superpowers/plans/verdicts/2026-11-19-gh45-records-whole-pr.md` Verification 5, probes 2 to 6, on `923c5af` against `949741f`. `src/` is unchanged from `923c5af` to `3b16d84` (diff exit 0), and my probes agree. **Fix:** after `draft:3`'s heading, add: "Each example is a `verify_claim` probe, run on `3b16d84` and `949741f` (the whole-PR verdict, `docs/superpowers/plans/verdicts/2026-11-19-gh45-records-whole-pr.md`, Verification 5, at `923c5af`, whose `src/` equals `3b16d84`'s). 'No longer' means verified on `949741f`, a miss on `3b16d84`."

**H2 (I1, Rule Zero).** `draft:10` says "now closed" and "Now that quote is a miss", with no artifact and no head revision. Support: `token` verdict gate 4, whole-PR Verification 5 row 1, and my probe P1. **Fix:** "Now, on `3b16d84`, that quote is a miss: `…` (probe 1 in the whole-PR verdict's Verification 5, run on both revisions; pinned by `tests/test_verify.py`'s `test_suffixed_trailing_and_leading_decimal_prices_are_one_number…probe_1`)."

**H3 (I1, I6).** `draft:14`, "rule (d) moved 45 of the 160,000 … none moved the other way", has no source, no revisions, and no way to re-run it. `run_baseline.py` prints only the head's `verified_fuzzy`. Support: `token` verdict gate 7 (per-case replay, 45 of 45 fuzzy→miss, 0 miss→verified, at `3135f12`) and whole-PR Verification 3. **Fix:** "Between `949741f` and `3b16d84`, `fuzz_place2.py`'s `verified_fuzzy` fell from 6,568, 6,726, 6,656 and 6,537 to 6,557, 6,715, 6,641 and 6,529 (seeds 7, 11, 12, 13, each of 40,000): 45 of 160,000 quotes moved from `quote_fuzzy` to a miss and none moved back (`docs/superpowers/plans/verdicts/2026-11-18-gh45-token.md`, gate 7, which lists every case; the PR description repeats them)."

### MEDIUM
**M1 (numbers).** `draft:33` says "the nine task verdicts". Contradicted by `pr-body.md:169-182` (12 rows) and by 12 `2026-11-18/19-gh45-*.md` files on `3b16d84`. **Fix:** "the twelve task verdicts (two FAILs, each followed by a PASS on its repair)". `pr-body.md:9` has the same stale "nine".

**M2 (I5).** `draft:8` (i) replaces a decision the issue still records as the owner's. The comment of 2026-11-15T17:20:57Z says: "The owner's chosen follow-up for 2 (17:16:32 UTC): count claims with identical receipts once." The shipped rule is brief Q3, "A: reject duplicate repairs" (brief:192); brief:178 says "The owner chose to reject duplicate repairs, not to change the count". **Fix:** add to (i): "This replaces the follow-up recorded on 2026-11-15 at 17:16:32 UTC (count identical receipts once): on 2026-11-18 the owner chose to reject duplicate repairs instead. Claims the agent wrote on one receipt still count separately, and `Coordinator`'s verified/total is unchanged." Also put a dated note on the first line of the 17:20 comment's item 2 (the owner or orchestrator does that edit, not this judge).

**M3 (numbers: set).** `draft:13`, "and 2 of 3,678 add-a-word misquotes scoring at least 90", has no verb. It reads as if 2 scored at least 90; in fact 3,678 did, and 2 of them verified (`expected.txt:15`). **Fix:** "2 of the 3,678 add-a-word misquotes that score at least 90 verified (10,994 generated)". Also give each rejected-true-quote count its generator: "195 of 5,998 (`fuzz_place_all.py`), 35 of 2,931 on price-dense pages (`fuzz_dense.py`) and 2 of 6,941 add-a-word (`fuzz_add.py`) true quotes rejected for their numbers".

**M4 (I1, I6).** `draft:13` ("same as on `949741f`") and `draft:15` ("on `949741f`'s rules") name the base but not the run that measured it, or how to repeat it. `run_baseline.py` checks "at most", so `ok` alone does not prove "same". **Fix:** "`949741f`'s counts are `expected.txt`'s quote lines (`expected.txt:1`) and were re-measured by running `run_baseline.py` with `949741f`'s `src/` first on `PYTHONPATH`: exit 1, the 10 `ROSE` lines above, the 20 quote lines identical (whole-PR verdict, Verifications 3 and 4)."

### LOW
1. `draft:1`: "the PR" has no number. Add `#<n>` once it is opened.
2. `draft:15`, "147 of 300 for 'free'": say "147 of 300 (all 147 that cite a negated or trial free; the other 153 state a non-zero price against an unnegated free)". Source: `fuzz-claims` verdict gate 4(d).
3. `draft:18`, "22 of 160,000": the 07:55 UTC comment gave the same 22 as "of the 109,249 wrong-price quotes". Add "(PR #35's uncommitted `count_sets.py` put 109,249 of the 160,000 as holding a wrong price)", as `rules.py:125-126` does.
4. `draft:23`, "each with an example": the copied-receipt limit has a description, not a worked example. Say "each described". 4b: the issue body also asked to "update README.md's verifier table", which this PR did (`README.md:258` on `3b16d84`), but the comment doesn't say so. Add one line.
5. `draft:10`, "this issue did not record": state the scope, "neither the issue body nor its five comments".
6. `draft:7`, "on both sides": define it as "in the quote-to-page match and in the claim rule".
7. Evidence hygiene: `evidence-run_baseline-3b16d84.txt` records neither its commit nor its exit code; only the filename names `3b16d84`.
8. `draft:14`, "right after a page price": the edit is in the quote, after the quote's price, where the page has the same price.

VERDICT: FAIL
