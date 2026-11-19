# Verdict: gh45 `records`, the whole PR (judge, fresh context, 2026-11-19)

Reviewed: branch `jay/gh-45-records` at `923c5af`, diff `origin/main...HEAD` (30 files; merge base `3b2673c` = `origin/main`). This is the PR's `/judge` before the owner merges. Saved by the orchestrator from the judge's final message; Verification evidence condensed, findings verbatim.

VERDICT: PASS

No CRITICAL, HIGH or MEDIUM findings; 4 LOW, all in the written record. No live run, no paid call, no key exported; tracked tree clean; scratch worktree removed. Run outputs: scratch `judge-whole-pr/` (not durable).

## Verification 1: scope — met
30 paths, all in the brief's Allowed list as amended (the brief's own path at brief:56). Unchanged (`git diff --quiet` exit 0): the frozen set (`contracts.py`, `settings.py`, `fakes/`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`); harness `coordinator.py`, `service.py`, `live.py`, `tools.py`, `packs.py`; `api/`, `db/`, `ui/`, `auth/`, `packs/`, `tests/fixtures`; `scripts/mellea`, `scripts/leak_gate`, `seed_demo_runs.py`, `export_openapi.py`, `docs/api`; `.github`, `bin`, `.gitleaksignore`, `AGENTS.md`, `CLAUDE.md`, `src/receipts/verify/__init__.py`. Only ADR in the diff: 0007. Marker grep over `src tests scripts` exit 1. `git diff --exit-code 641eadd -- scripts/verify_fuzz` exit 0. README hunks only in "The verifier" (`:258`, `:264-272`), "Tests and gates" (`:433`), the Demo bullets (`:469-470`). `records` test changes are comments/docstrings only (`tests/test_verify.py:703-707`; `tests/test_verify_claim_numbers.py:3-6`, `:771`). No test deleted; the only assertion change is the brief-sanctioned `tests/test_harness_repair.py:178`, `:186`.

## Verification 2: gates — met
`bin/jig` exit 0 (all `ok`). `pytest -q -m "not integration" -rs`, seven variables unset: 820 passed, 14 deselected (marker `integration`: 12 `tests/test_db_constraints.py`, 1 `tests/test_db.py`, 1 `tests/test_integration_live.py`), 0 skipped. Alone: `test_verify.py` 117, `test_verify_claim_numbers.py` 160, `test_harness_repair.py` 18. `run_baseline.py` exit 0, 34 of 34 `ok`. `ruff check .` and `ruff format --check .` ("205 files already formatted") exit 0. Highest complexity `_verify_quote` 5; longest functions `_fuzzy_miss` 32 lines, `_repair_failing` 30.

## Verification 3: the committed scripts generate what PR #35 measured — met
On the head, all 12 durable-vs-committed runs exit 0 and diff empty without the `RULES` line. At `949741f` (scratch worktree, `uv sync --frozen`, `scripts/verify_fuzz/` copied in), every summary line equals the brief's table: `place_all` 0 and 195 of 5,998; `dense` 35 of 2,931; `add` 1091/1048/1539 scored, 1/1/0 verified, TRUE 2331/2264/2346 tried, 0/1/1 rejected; `place2` 1/9/5/7; `skip` 3767/3672 tried, 7/15 verified; `spread` 0 of 6,000. `verified_fuzzy` base→head: s7 6568→6557, s11 6726→6715, s12 6656→6641, s13 6537→6529 (45 of 160,000).

## Verification 4: red first at `949741f` — met
With the PR's three test files and `scripts/verify_fuzz/` copied in: `test_verify.py` 8 failed / 109 passed of 117; `test_verify_claim_numbers.py` 85 / 75 of 160; `test_harness_repair.py` 3 / 15 of 18. All 96 failures `AssertionError`, 0 `ERROR` lines. Failing lines: `test_verify.py` suffix family (`on_the_page` ×3, `spelt_another_way` ×3, `dollar_point_99`, `probe_1`); `test_verify_claim_numbers.py` counts 16 at `:738`, free 15 at `:830`, unsigned 21 (`:547` ×19, `:548` ×2), signed-spelling 8 at `:583`, suffix family 5 at `:359`, 6 at `:382`, 6 at `:421`, probes 2 at `:637` and 2 at `:857`, guards 2 at `:482` and 2 at `:766`; harness: duplicate, converging, keeps-own. Passing on base: `test_unsigned_quote_price_still_misses_a_signed_page_price` 6 of 6 (required); `test_agent_written_claims_sharing_a_quote_both_count` 2 of 2 (LOW 4); the three pinned tests, byte-identical to `949741f`. `run_baseline.py` at `949741f`: exit 1, exactly 10 `ROSE`, all claim-shape (WRONG verified count/unsigned/suffix/trailing/leading_decimal 300 of 300, free 147 of 300; TRUE rejected unsigned 104, suffix 138, trailing 82, leading_decimal 55, each of 300); all 20 quote lines `ok`.

## Verification 5: the six probes — met
| # | Head | `949741f` |
|---|---|---|
| 1 | not verified: `quote not found on page: numbers differ (quote has $20; page has $20k there; partial_ratio=100.0)` | verified, `quote_exact` |
| 2 | not verified: `claim numbers not in quote: $25` | verified, `quote_exact` |
| 3 | verified, `quote_exact` | not verified: `claim numbers not in quote: $25` |
| 4 | not verified: `claim numbers not in quote: $0` | verified, `quote_exact` |
| 5 | not verified: `claim numbers not in quote: 500` | verified, `quote_exact` |
| 6 | not verified: `…numbers differ (quote has 20; page has $20 there; partial_ratio=92.3)` | not verified, same note |

## Verification 6: the ten sabotage rows — met
Each injected, red, reverted, green, status clean. 1 (`credit|` out of `_COUNT_UNITS`, `rules.py:264`): 5 failed; `--kinds count` `31 of 300 — ROSE`. 2 (`:507-508` deleted): 12 failed; `--kinds free` `114 of 300 — ROSE`. 3 (`:509` → `return True`): 4 failed (`trial`, `trial-hyphen`, both plural); `33 of 300 — ROSE`. 4 (`_NUMBER_TOKEN` reverted): 27 failed; `--kinds suffix,trailing` four `ROSE` (300, 138, 300, 82 of 300). 5 (`:524` own tokens only): 19 failed incl. 8 of 8 "both unsigned" and `test_failing_claim_is_repaired_with_the_verifier_reason_then_verified`. 6 (reading into `_match_quote`, both variants): the narrow-rule test 6 of 6 red. 7 (`specialist.py:425` deleted): 3 failed (duplicate, converging, keeps-own); `(1, 2)` and `repaired=0` at `tests/test_harness_repair.py:294`, `:296` exist (the test stops at `:289` under this row). 8 (own-receipt branch `return True`): 1 failed, keeps-own. 9 (drop agent-written sharers): at the top of `_repair_failing` both parameters red; after `_merge` only `[no-failing-claim]` red (the no-factory path returns at `specialist.py:411-412`). 10 (`fuzz_place_all.py:34` `$8`→`$7`): durable diff 152 lines, counts unchanged; `run_baseline.py` exit 1 `PIN MISMATCH fuzz_place_all.py: …`; revert exit 0.

## Verification 7: the record — met, except LOW 1 to 3
`rules.py:1-196`, `docs/verifier.md:24-105` and `README.md:245-272` describe the same rules; 35 probes of their examples hold. Both limits lists have 14 items in the same order (`rules.py:117-188`, `docs/verifier.md:41-105`), every example holds; the pre-existing "227 of the 230" (`rules.py:134`) reproduces (193 of 195 + 34 of 35). Repo grep outside `docs/superpowers/`: 0 hits for "scripts in the review records", "not in the repository", "tracked in issue #45", "tracked in GitHub issue #45", "Issue #45 tracks", "is read as `$20`", "bare integers are not checked", "no sign attached". No (a)-(d) or (i) listed as open. (e)-(h) owner-accepted 2026-11-18 at `rules.py:109`, `docs/verifier.md:36`, `README.md:265`, with rates and denominators; 109,249 only at `rules.py:126` and `docs/verifier.md:48` with `count_sets.py` provenance. New limits present with examples (assumptions 2, 3, 6, 9, 10; `$5m`/`$5mo` both ways; "free 14-day trial", "free: trial"; negation across punctuation; "25 per seat", "In 2025 users", "GPT-4 tokens"; "unless a number follows the sign" at `rules.py:28-29`). ADR-0007 `:18` and `:28`. **Binding README rule met:** `README.md:264-272` names known limits with rates and links `docs/verifier.md`; Demo bullets `:469-470` with "20 of 20" and "6 of the 8" unchanged; `run_baseline.py` line at `:433`. Seven `<details>` examples: `diff` exit 0 on the head and on `949741f`. `rules.py` in `records` docstring-only (0 of 70 non-docstring nodes differ). Timing "about 11 s" not confirmed (19.6, 27.7, 31.6 s at load 10.7 on 8 CPUs; not a finding). Every carried-over `records` item present.

## Findings (verbatim)

| # | Severity | Finding | Citation | Fix |
|---|---|---|---|---|
| 1 | LOW | A number without a denominator: "let 349 and 110 wrong prices verify over four of the shapes, against 46 for the shipped rules". The sums are right (2+107+67+173 = 349; 2+22+1+85 = 110; 22+22+0+2 = 46), but the denominators differ per shape. | `docs/verifier.md:60-61` | Give each shape with its denominator: `fuzz_place2` 22 / 2 / 2 of 160,000; `fuzz_skip` 22 / 107 / 22 of 7,439; `fuzz_spread` 0 / 67 / 1 of 6,000; `fuzz_add` 2 / 173 / 85 of 3,678. Or drop the totals. |
| 2 | LOW | The README's table row says "written out as `25 dollars` or `$ 25`". The `docs/verifier.md` row says only "`25 dollars`", yet `docs/verifier.md:3-5` says the README "keeps the summary table". | `README.md:258` vs `docs/verifier.md:18` | Make the two rows identical. |
| 3 | LOW | The integration branch's dispatch log says "Whole-PR diff `origin/main...923c5af`: 31 files". The diff has 30. | `git show 2a7d0e7:docs/superpowers/plans/2026-11-16-gh45-verifier-follow-ups.md` line 281; `git diff --name-only origin/main...923c5af \| wc -l` → 30 | Say 30, or 31 once this verdict file is added. |
| 4 | LOW | Brief Verification 4 requires every new test to fail on `949741f` except the narrow-rule test. `test_agent_written_claims_sharing_a_quote_both_count` passes there 2 of 2: it guards against over-rejection and cannot fail without a defect. Sabotage row 9 covers it instead (both parameters red). The PR body already says so. | `docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md:139`; scratch run of `tests/test_harness_repair.py` at `949741f`: 3 failed, 15 passed, exit 1, this test PASSED ×2 | Record only. The brief's exception list could name it. |

## The two drafts (read-only; for the claims judge)
No number in either draft contradicts what was measured (the 34 head lines, the 10 `ROSE` lines, the 20 quote lines, the per-seed `verified_fuzzy` and 45 of 160,000, the six probes on both revisions, 820/14/0 and 160/117/18, the `$5m` edge on `949741f`, `949741f` and `3b2673c` identical in `src/`, `tests/`, `scripts/`, the comment's rates). To fix: `pr-body.md:60` and `issue-45-comment.md:12` call `604e54f` "the last task's head" (it is `923c5af`; the 34 lines are the same); `pr-body.md:180` names this verdict `2026-11-18-…` and "pending" (it is `2026-11-19-gh45-records-whole-pr.md`, PASS); `pr-body.md:31`'s dedupe re-run note (4 failed, the subprocess test failing for lack of a project) does not conflict (the judge's synced worktree gave 3 failed, 15 passed).

VERDICT: PASS

## Orchestrator disposition (2026-11-19)

- **LOW 1 and 2:** prose-only fixes in `docs/verifier.md:60-61` and `:18`, applied by a `records-text` follow-up on the integration branch with its own judge, as `dedupe-docstrings` was.
- **LOW 3:** corrected in the plan's dispatch log (30 files at `923c5af`).
- **LOW 4:** record only; the PR body already names the exception.
- **Drafts:** the head commit, verdict file name and PASS are updated before `/verify-claims`.
