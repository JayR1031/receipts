## Goal

A claim no longer verifies when its quote lacks the claim's count with a unit, unsigned price, or suffixed, trailing-sign or leading-decimal price, or backs its $0 only with a negated or trial "free"; a Mellea repair that copies another claim's receipt is no longer accepted; and the six PR #35 random-test shapes, committed under `scripts/verify_fuzz/`, show no rise in any count of wrong prices verified or true quotes rejected.

## Why it matters

People reading a battlecard trust the "verified" mark. Today a claim such as "Enterprise is $20k a year", "Max includes 500 credits" or "Starter is $0" verifies against a quote that says "$20 per seat", "18,000 credits" or "not free". The headline "N of M verified" is the app's acceptance metric, and a repair that reuses another claim's receipt adds a second verified claim on one piece of evidence. The random tests that guarded PR #35 live only in a scratch folder, so the next verifier change has nothing to measure regressions against.

## Constraints

**Where this comes from:** the repository owner asked on 2026-11-16: "Okay, go ahead and finish 44 and 45." This brief covers issue #45 only; #44 is handled separately. Scope comes from the owner's answers of 2026-11-18 in Claude Code session `477932e0`, relayed by the coordinating session. Base: `origin/main` at `949741f`. Suggested branch: `jay/gh-45-verifier-follow-ups`.

**Rule semantics, as the owner decided on 2026-11-18:**
- **(a) Counts with units are checked in the claim.** A bare integer directly followed by a unit from a closed list is a value token of the claim. The list: credits, seats, users, members, projects, messages, requests, tokens, minutes and hours. It is compared with the quote's number tokens like every other value (`18000 credits` in the claim is backed by `18,000 credits` in the quote). Every case in `test_bare_integers_in_the_claim_are_not_checked` (`tests/test_verify_claim_numbers.py`) stays green unchanged: years, plan names, model names and `24/7`.
- **(b) A negated or trial "free" no longer covers a zero price.** In `_quote_values`, a `free` that is negated ("not free", "no free plan", "isn't free") or is a trial ("free trial") adds no zero price. A free tier that belongs to another plan stays a label limit, (e).
- **(c) Unsigned prices count, in the claim-against-quote rule only.** "25 dollars", "25 USD" and "$ 25" read as `$25`, both in the claim's values and in the quote's values for that rule. The quote-to-page match stays exactly as PR #35 measured it: `normalize`'s output does not change, and `_match_quote` does not use this reading. A quote "Pro costs 20 dollars" on a page "Pro costs $20." stays a miss.
- **(d) Suffixed, trailing-sign and leading-decimal prices are one number each, on both sides.** `_NUMBER_TOKEN` reads `$20k`, `$1.2M`, `25$` and `$.99` as one token. `_canonical_number` makes equal amounts compare equal: `$20k` = `$20,000`; `$.99` = `$0.99`; `25$` = `$25`. This closes a gap on the quote side that the record does not mention. On `949741f`, the quote "Enterprise $20" is a `quote_exact` match on the page "Enterprise $20k a year.", so the claim "Enterprise is $20 a year." verifies, because the token stops before the `k`. After this change that quote is a miss.
- **(i) A repair that duplicates a receipt is not accepted.** In `SpecialistRunner._repair_failing` (`src/receipts/harness/specialist.py`), a repaired claim whose receipt is identical to another claim's receipt is treated like a repair that found nothing. The original claim goes to the Verifier unchanged. The check is a pure helper (new) applied before `_merge`. Claims the agent wrote that share one quote still count separately. A repair that keeps its own claim's original receipt and changes only the text is accepted. `Coordinator.run`'s counting (`src/receipts/harness/coordinator.py:88-98`) does not change.
- **(e), (f), (g) and (h) stay documented limits**, with their reasons (owner, 2026-11-18):
  - (e) plan labels are not checked;
  - (f) true quotes past the score window fail closed;
  - (g) values swapped inside one quote still verify;
  - (h) repairs can carry plan names their quote lacks.

  `rules.py`'s docstring and the README call them accepted limits and cite the PR #35 rates, with their sets and denominators.

**The standard (`AGENTS.md` sections 0 to 5), where it applies here:**
- Every new or changed rule is a pure function: immutable input in, a value out, no I/O, no clock. Each starts with a failing test, watched failing for the right reason, an assertion and not an import error, before the code that makes it pass.
- Functions stay under 60 lines and within ruff's `mccabe.max-complexity = 6` (`pyproject.toml`). Decompose into pure helpers; never suppress the check.
- Typed boundaries: no `dict[str, Any]` across modules. `RepairRequest` and the receipts stay typed (`QuoteReceipt`, `SearchReceipt` from `src/receipts/contracts.py`).
- Every number in a report, the PR description, an issue comment, the docstring or the README carries its set and denominator, for example "22 of 109,249 wrong-price quotes". A skipped test is named, not counted.
- Three repair attempts per failing gate, each fed the exact stderr. On the third failure, stop and escalate to the owner with the trace. Wipe `__pycache__` before every measured run.
- The PR description and any comment on issue #45 go through `/verify-claims` before they are posted. `/judge` gives a PASS before the owner merges.

**Project overlay (`AGENTS.md` section 9):**
- Frozen, no exception for this issue: `src/receipts/contracts.py`, `src/receipts/settings.py`, `src/receipts/fakes/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`. No new dependency, no per-file ruff ignore.
- **Lanes.** L2 (verifier) owns `src/receipts/verify/**` and `tests/test_verify*.py`. L1 (harness) owns `src/receipts/harness/**` and `tests/test_harness*.py`. Their file sets in this brief are disjoint. `scripts/verify_fuzz/` (new) belongs to L2 for this issue.
- Unit tests use the Wave 0 fakes and no network. Implementers and reviewers start no live run, call no paid model and set no API key. `scripts/mellea/live_*.py`, `scripts/seed_demo_runs.py` and the app's run endpoint are not run.
- `rules.py`'s module docstring, the README's "The verifier" section and ADR-0007 change in the same PR as the rules they describe.
- The owner merges. Merge `origin/main` into the branch to update it; no rebase and no force-push.
- `ruff check .` and `ruff format --check .` cover `scripts/`, so the committed measurement scripts must pass both (ANN annotations, complexity at most 6, line length 100). `pyright` covers only `src` and `tests`.

## File scope

Allowed:
- `src/receipts/verify/rules.py`
- `src/receipts/verify/__init__.py`, only if a new public name is truly needed
- `tests/test_verify.py`, `tests/test_verify_claim_numbers.py`, `tests/test_verify_*.py` (new files)
- `src/receipts/harness/specialist.py`, `src/receipts/harness/repair.py`
- `tests/test_harness_repair.py`
- `scripts/verify_fuzz/**` (new)
- `README.md`: only the "The verifier" section, one line in "Tests and gates" on how to run `scripts/verify_fuzz/`, and the two issue-#45 bullets in "Demo: Mel vs Warp" ("What "repaired" means" and "Duplicates"), rewritten as an owner-accepted limit and a cross-domain-only limit (owner, 2026-11-18 06:16 UTC)
- `docs/verifier.md`: the verifier section's home after PR #53, which merges before this PR (owner, 2026-11-18 06:16 UTC); the same edits as the README's "The verifier" section, under the same rules
- `docs/adr/0007-mellea.md`
- `docs/superpowers/plans/**` (the orchestrator's plan and the judges' verdicts)
- `docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md` (this brief, which ships with the PR)

**Amended 2026-11-18 06:16 UTC** on the owner's answers to the orchestrator's plan questions, relayed by the coordinating session (Claude Code session `477932e0`): PR #53 merges first, so `docs/verifier.md` is added; the two Demo bullets are added; the brief's own path is listed.

Forbidden:
- `src/receipts/contracts.py`, `src/receipts/settings.py`, `src/receipts/fakes/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`
- `src/receipts/harness/coordinator.py`, `src/receipts/harness/service.py`, `src/receipts/harness/live.py`, `src/receipts/harness/tools.py`, `src/receipts/harness/packs.py`
- `src/receipts/api/**`, `src/receipts/db/**`, `src/receipts/ui/**`, `src/receipts/auth/**`, `src/receipts/packs/**`
- `tests/fixtures/**` (L3's golden set), and every test file not listed under Allowed
- `scripts/mellea/**`, `scripts/leak_gate/**`, `scripts/seed_demo_runs.py`, `scripts/export_openapi.py`, `docs/api/**`
- `.github/**`, `bin/**`, `.gitleaksignore`, `AGENTS.md`, `CLAUDE.md`, every other ADR

## Acceptance tests

Run from the worktree root. Each must exit 0 at the PR head.

```bash
uv run pytest -q tests/test_verify_claim_numbers.py   # (a), (b), (c) and (d) in the claim rule; year, plan-name, model-name and 24/7 cases still unchecked
uv run pytest -q tests/test_verify.py                  # (d) on the quote side; the quote-to-page rule unchanged for unsigned spellings
uv run pytest -q tests/test_harness_repair.py          # (i): a duplicate repair is rejected, its original reaches the Verifier, the counts are honest
uv run python scripts/verify_fuzz/run_baseline.py      # all eleven PR #35 commands plus the new claim shapes, compared with scripts/verify_fuzz/expected.txt; exits 1 if any fail-open or fail-closed count rises
bin/jig                                                # format, lint, types and unit tests over the whole repo, scripts/verify_fuzz/ included
```

**New tests, each watched failing on `949741f` first.** The names are suggestions (new); what each must prove is fixed.
- `test_counts_with_units_in_the_claim_are_checked` (new). "Max includes 500 credits." against the quote "Max includes 18,000 credits" is a miss with the note `claim numbers not in quote: 500`. Also covers `50 seats`, `10 users` and the other units, and `18000 credits` against `18,000 credits`, which verifies.
- `test_negated_or_trial_free_does_not_cover_a_zero_price` (new). The claim "Starter is $0." is a miss against "Starter is not free", "There is no free plan" and "Start a free trial". It still verifies against "Starter is free".
- `test_unsigned_prices_in_the_claim_are_checked` (new). "Pro costs 25 dollars." / "25 USD" / "$ 25" against the quote "Pro costs $20" is a miss with the note `claim numbers not in quote: $25`.
- `test_unsigned_price_matches_its_signed_spelling_in_the_claim_rule` (new). "Pro costs $25." against the quote "Pro costs 25 dollars" verifies `quote_exact`. So does the reverse, and so do both written as "25 dollars".
- `test_unsigned_quote_price_still_misses_a_signed_page_price` (new; pins the narrow rule). The quote "Pro costs 20 dollars" on the page "Pro costs $20." is not verified. On `949741f` this already holds; it must stay true after the change.
- `test_suffixed_trailing_and_leading_decimal_prices_are_one_number` (new). Four cases:
  - the quote "Enterprise $20" on the page "Enterprise $20k a year." is a miss, and so is `$1.2` on `$1.2M`;
  - the claim "$20k a year" against the quote "$20 per seat per month" is a miss;
  - "$20k" against "$20,000" verifies;
  - `25$` and `$.99` are extracted and compared as `$25` and `$0.99`.
- `test_a_repair_that_duplicates_another_claims_receipt_is_not_accepted` (new):
  - the setup: one claim that already verifies cites `GOOD_QUOTE`, and the scripted Mellea backend repairs a failing claim to the same `GOOD_QUOTE` receipt;
  - one `VerifiedEvent`, and one `DroppedEvent` carrying the original `BAD_QUOTE`;
  - through `Coordinator`, `DoneEvent` is `(verified_count, total_count) == (1, 2)`;
  - the log line reads `repaired=0`.
- `test_two_repairs_converging_on_one_receipt_keep_only_the_first` (new). Claims are settled in their original order.
- `test_a_repair_that_keeps_its_own_receipt_is_accepted` (new). Only the claim text changes, and the claim then verifies.
- `test_agent_written_claims_sharing_a_quote_both_count` (new). No repair factory, or no failing claim. Two claims citing one quote give `(2, 2)`.

**One existing test changes; it is not deleted.** `test_failing_claim_is_repaired_with_the_verifier_reason_then_verified` (`tests/test_harness_repair.py:173`) currently pins the duplicate: two verified claims with the same `GOOD_QUOTE`. Change only its setup, so that the claim that already verifies cites a different quote on `data.SUBJECT_PAGE`. Its assertions on two generations, the Verifier's reason as feedback, the page as grounding and Mellea's repair step stay.

**The measurement.** Commit the six scripts from `/Users/jay/Projects/receipts-drafts/verify_fuzz/` under `scripts/verify_fuzz/`, flattened:
- `fuzz_place_all.py`, `fuzz_dense.py` and `fuzz_skip.py` from `judge-r4/scripts/`;
- `fuzz_add.py` from `judge-r5/scripts/`;
- `fuzz_place2.py` from `claims/scripts/`;
- `fuzz_spread.py` from `r3/`.

Make them pass ruff without changing what they generate. Add:
- `run_baseline.py` (new): runs every command below plus the claim shapes, and compares each count with `expected.txt`;
- `expected.txt` (new): one line per count, naming its set and denominator;
- `fuzz_claim_values.py` (new). For each kind, count-with-unit, unsigned price, suffixed, trailing-sign, leading-decimal, negated or trial "free", and a control kind of bare non-count integers, it builds a quote that is on its page and two claims:
  - a TRUE claim that restates the quote's value in an equivalent spelling;
  - a WRONG claim that states a different value.

  It reports, per kind, WRONG claims verified of N and TRUE claims rejected of M. On `949741f`, WRONG claims verified must be above 0 for every kind (a) to (d) except the control, and `run_baseline.py` must exit 1. That is the measurement's red-first run.

**The baseline.** The main session re-ran the six durable copies on `949741f`'s `rules.py` on 2026-11-18, 8 s in total. No count in this table may rise:

| Command | Summary lines on `949741f` | The count that may not rise |
|---|---|---|
| `fuzz_place_all.py 2 6000` | `misquotes tried=5998 … verified=0`; `legit tried=5998 … rejected-for-numbers=195` | 0 of 5,998 misquotes verified; 195 of 5,998 true quotes rejected |
| `fuzz_dense.py 9 8000` | `true quotes tried=2931 … rejected-for-numbers=35` | 35 of 2,931 true quotes rejected |
| `fuzz_add.py 51 6000`, `52 6000`, `53 6000 all 1` | MIS `scored>=90` 1091 / 1048 / 1539, `verified` 1 / 1 / 0; TRUE tried 2331 / 2264 / 2346, `rejected-for-numbers` 0 / 1 / 1 | 2 of 3,678 add-a-word misquotes scoring at least 90 verified (10,994 generated); 2 of 6,941 true quotes rejected |
| `fuzz_place2.py` seeds 7, 11, 12, 13, × 40000 | `verified_with_a_wrong_slot` 1 / 9 / 5 / 7 | 22 wrong-slot quotes verified, of 160,000 generated. PR #35's `count_sets.py` put 109,249 of them as holding a wrong price; that script is not among the durable copies |
| `fuzz_skip.py 5 6000`, `6 6000` | `misquotes tried` 3767 / 3672, `verified` 7 / 15 | 22 of 7,439 misquotes verified |
| `fuzz_spread.py 1 6000` | `spread misquotes tried=6000 verified=0` | 0 of 6,000 misquotes verified |

These scripts call `verify_claim` with a fixed claim text ("Probe claim." or "x"), so they measure only the quote-to-page rule. Only change (d) can move them. If any count moves either way, the PR lists every changed case.

## Verification

A reviewer confirms each point without trusting the implementer's report.

1. **Scope.** `git diff --name-only origin/main...HEAD`: every path matches File scope's Allowed list and none matches Forbidden. Also run `git diff origin/main...HEAD | grep -nE '^\+.*(noqa|type: ignore|pytest\.mark\.(skip|xfail)|pyright: (basic|ignore)|per-file-ignores)'`; it must print nothing.
2. **Gates.** `find . -name __pycache__ -prune -exec rm -rf {} +`, then `bin/jig` (exit 0). Then `uv run pytest -q -m "not integration" -rs`: report the passed, deselected and skipped counts, and name every skip with its reason. Run each of the three changed test files alone as well.
3. **The committed scripts generate what PR #35 measured.** On the PR head, run each of the eleven commands twice: once with the durable copy, for example `uv run python /Users/jay/Projects/receipts-drafts/verify_fuzz/r3/fuzz_spread.py 1 6000`, and once with `scripts/verify_fuzz/<name>.py`. Diff the two outputs without the first `RULES …` line; each diff must be empty. Then, in a scratch worktree at `949741f` (`git worktree add <scratch>/base 949741f`), run the committed scripts against the base rules: the summary lines must equal the baseline table above.
4. **Red first.**
   - In the `949741f` worktree, copy in the PR's three test files and `scripts/verify_fuzz/`.
   - Run the three test files. Every test listed under Acceptance tests as new must fail by an assertion, except `test_unsigned_quote_price_still_misses_a_signed_page_price`, which must pass.
   - Run `uv run python scripts/verify_fuzz/run_baseline.py`. It must exit 1 on the claim-shape lines only; the eleven quote-to-page counts must match.
5. **Probes on the head.** Run `verify_claim` with a fetched page whose `ok=True`. Expected outcomes:
   - claim "Enterprise is $20 a year.", quote "Enterprise $20", page "Enterprise $20k a year.": not verified, note `quote not found on page: numbers differ (quote has $20; page has $20k there; …)`;
   - claim "Pro costs 25 dollars.", quote "Pro costs $20", page "Pro costs $20.": not verified, `claim numbers not in quote: $25`;
   - claim "Pro costs $25.", quote "Pro costs 25 dollars", page "Pro costs 25 dollars.": verified, `quote_exact`;
   - claim "Starter is $0.", quote "Starter is not free", page "Starter is not free.": not verified;
   - claim "Mel Max has 500 credits.", quote "Max includes 18,000 credits", page "Max includes 18,000 credits.": not verified, `claim numbers not in quote: 500`;
   - claim "Pro costs $20.", quote "Pro costs 20 dollars", page "Pro costs $20.": not verified (the narrow rule).

   On `949741f`, probes 1, 2, 4 and 5 verify, probe 3 does not, and probe 6 does not.
6. **Sabotage, one at a time.** Inject the defect, confirm red, revert, confirm green.

| Sabotage | Must turn red |
|---|---|
| Remove `credits` from the unit list | the counts test; `run_baseline.py` on the count shape |
| Drop the negation check for "free" | the "free" test |
| Drop the "free trial" check | the trial case of the "free" test |
| Revert `_NUMBER_TOKEN` to `[$€£¥]?\d+(?:[.,]\d+)*%?` | the suffix test; the claim-shape suffix and trailing-sign kinds |
| Drop the unsigned-price reading from the quote's values (claim side only) | the both-"25 dollars" case of `test_unsigned_price_matches_its_signed_spelling_in_the_claim_rule`, and `test_failing_claim_is_repaired_with_the_verifier_reason_then_verified` (its claim and `GOOD_QUOTE` both say "9 dollars") |
| Route the unsigned-price reading into `_match_quote` | `test_unsigned_quote_price_still_misses_a_signed_page_price` |
| Delete the duplicate-receipt check | the duplicate-repair test and the converging-repairs test |
| Make the check also reject a repair that keeps its own original receipt | `test_a_repair_that_keeps_its_own_receipt_is_accepted` |
| Make the check reject claims the agent wrote that share a quote | `test_agent_written_claims_sharing_a_quote_both_count` |
| Change one element of `PRICES` in `scripts/verify_fuzz/fuzz_place_all.py` | step 3's diff, and `run_baseline.py` |

   If a sabotage turns nothing red, ask whether the path reaches the guard; do not accept it as covered.
7. **The record.**
   - `rules.py`'s module docstring, the README's "The verifier" section, the "number rules" bullets and the known-limits list describe the same rules.
   - None of them still says "scripts in the review records, not in the repository" or lists (a) to (d) or (i) as open.
   - They name the accepted limits (e) to (h) and the new ones under Assumptions, each with a rate and its denominator where one was measured.
   - ADR-0007 states that a repair duplicating another claim's receipt is not accepted.
   - Each README worked example (the `<details>` blocks under "The verifier") is re-run on the head, and its printed output matches.

## Do not

- Do not change what the six PR #35 scripts generate (seeds, `n`, value lists, the order of RNG calls, the printed lines) while making them lint-clean. Do not lower a sample size, drop a seed, or edit `expected.txt` to absorb a rise.
- Do not apply the unsigned-price reading (c) to `normalize`, `_match_quote`, `_occurs_with_whole_numbers` or `_number_mismatches`. The quote-to-page rule stays as PR #35 measured it.
- Do not touch the alignment code (`_char_map`, `_aligned_range`, the window in `_fuzzy_miss`) or `FUZZY_THRESHOLD`, and do not add a plan-label check. PR #35's widened variants let 349 and 110 wrong prices verify, against 46 for the shipped rules, over four shapes (issue #45, 07:55 UTC comment).
- Do not change the repair prompt `_TASK` or `judge` to address (h), and do not dedupe in `Coordinator` or count distinct receipts. The owner chose to reject duplicate repairs, not to change the count.
- Do not delete or rename `test_failing_claim_is_repaired_with_the_verifier_reason_then_verified`, and do not weaken its assertions. Change only which quote its claim that already verifies cites.
- Do not change any expectation in `test_bare_integers_in_the_claim_are_not_checked`, `test_zero_price_in_the_claim_is_matched_by_free_in_the_quote` or `test_free_in_the_quote_covers_only_a_zero_price`; they must pass as written. Do not edit the golden set or the fakes to make a new rule pass.
- Do not add `noqa`, `type: ignore`, `skip`, `xfail` or `# pyright: basic`. Do not raise the complexity limit. Do not move a script out of ruff's reach.
- Do not write the new tests after the code. Each new test's red run on `949741f` goes in the PR description: test name, command, exit code and failing line.
- Do not claim "no regression" from a subset of the eleven commands. Report every summary line, with its set and denominator.
- Do not start a live run, run `scripts/mellea/live_*.py`, or export an API key to check behaviour.
- Do not post the PR description or an issue #45 comment before `/verify-claims` passes on it.

## Open questions

None. The owner answered the three questions that changed the plan on 2026-11-18:
- Q1, "Leave both as limits": (e) and (h) stay out of scope.
- Q2, "A: both sides, narrow": (d) on both sides, (c) in the claim rule only.
- Q3, "A: reject duplicate repairs".

## Assumptions

1. **How a count is recognised (a).** A unit counts in its singular or plural form, after the number with nothing, one space or one hyphen between them (`500 credits`, `1 seat`, `50-seat`). At most one other word may sit between the number and the unit (`1500 hosted-ai credits`, `5 active users`). The owner approved the unit list itself; the spacing rules are this brief's.
2. **A count compares its value, not its unit.** `500 seats` in the quote backs `500 credits` in the claim. This is the same family as limit (g) and is recorded as a limit.
3. **Which unsigned spellings count (c).** After the number: `dollar`, `dollars`, `usd`, `euro`, `euros`, `eur`, `gbp`, `jpy`, `yen`. Before the number: `usd`, `eur`, `gbp`, `jpy`. A sign followed by one space (`$ 25`). A number followed by one space and a sign (`25 €`). "pounds", "bucks" and number words stay out, because "pounds" is often a weight. The omissions are recorded as a limit.
4. **The quote's values for the claim rule add the signed readings.** They are all its number tokens plus the signed readings of its unsigned prices; the readings are added, not substituted. So a quote "25 dollars" backs both a claim `$25` and a claim's bare `25`.
5. **What the note shows.** The miss note names an unsigned price in its signed reading (`$25`) and a count as its number as written (`500`). Each is still sorted and deduplicated, as `_missing_numbers` does.
6. **Suffixes (d).** `k`, `m` and `b` count after normalizing (so `K`, `M`, `B` too). They must sit directly after a number that a currency sign leads, and must not be followed by a letter or digit (`$5 max` and `$5/mo` are unchanged). The amount is expanded with a decimal point: `$1.2m` = `$1,200,000`. Out of scope, and recorded as limits: `bn`, `mm`, `million` and `thousand`, a space before the suffix, a suffix on an unsigned number, and a decimal comma before a suffix.
7. **Trailing signs and leading decimals (d).** A trailing sign directly after the digits (`25$`, `25€`, `25£`, `25¥`) and a leading decimal after a sign (`$.99`, `€.50`) apply on both sides through `_NUMBER_TOKEN`. With a space (`25 €`), it is reading (c), claim rule only.
8. **Negation (b).** The words that negate a "free": `not`, `no`, `never`, `isn't`, `isnt`, `aren't`, `arent`, `without`, `non`. They negate a `free` when they come within the two words before it. `free` directly followed by `trial` adds no zero price either. One "free" in the quote that is neither negated nor a trial still adds the zero prices.
9. **What "identical" means (i).** Two receipts are identical when they are of the same kind with equal fields: for a `QuoteReceipt`, `url` and `quote` character for character; for a `SearchReceipt`, `query`, `rank` and `url`. `ts` is ignored, because it is copied from the logged row. The harness does not import the verifier's `normalize`. So a repair whose quote differs from another claim's only in case or spacing still counts separately; this is recorded as a limit.
10. **"The same run" means one specialist's claims, that is, one domain in that run.** `SpecialistRunner` sees only its own domain's claims. `Coordinator` cannot tell a repair from an original without a contract change (`ClaimEvent` has no such field, and `contracts.py` is frozen). A duplicate across domains is recorded as a limit.
11. **The order in which repairs are settled.** Failing claims are settled in their original order. A repair is compared with every other claim's receipt as it stands at that point: the agent's original, or the accepted repair of an earlier claim. A repair equal to its own claim's original receipt is accepted.
12. **The check runs after Mellea's loop.** It filters the results and does not feed back into Mellea, so a rejected duplicate has already spent its model calls (at most `MAX_REPAIRS`, which is 2). The INFO line keeps ADR-0007's format, `claim repair: <domain> failing=N repaired=M`, where M counts accepted repairs only.
13. **Where the scripts go.** `scripts/verify_fuzz/` sits outside every lane in section 9, next to the precedent `scripts/mellea/`. L2 owns it for this issue. `fuzz_skip.py` may keep calling the private `rules._canonical_number` (pyright does not cover `scripts/`).
14. **"Not regress".** No fail-open count (wrong prices or misquotes verified) and no fail-closed count (true quotes rejected) rises over the table above. Any fall is reported case by case, not taken as an improvement.
15. **Closing the issue.** The owner asked to "finish" #45, so the PR description says `Closes #45`. The remaining limits (e) to (h) are written in `rules.py` and the README as accepted by the owner on 2026-11-18, with no "tracked in #45" pointer. Before merge, one comment on #45, checked by `/verify-claims`, records the shipped rules, the rates and the quote-side `$20k` finding.
16. **The fixtures stay as they are.** The fakes (`src/receipts/fakes/data.py:15-16`, "9 dollars", "14 dollars") and the golden set (`tests/fixtures/comparisons/acme_vs_bolt/`) are not edited. With assumption 4, their claims keep their current outcomes, and the existing tests that use them pass unchanged.
