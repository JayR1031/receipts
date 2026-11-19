# Verdict: gh45 PR body draft, round 3 (claims-judge, fresh context, 2026-11-19)

Draft: scratch `gh45-drafts/pr-body.md` (203 lines), diffed against the round-2 copy (21 changed lines, every one checked). Branch `jay/gh-45-verifier-follow-ups` at `ece3623` (code equals `3b16d84`). Review finished 2026-11-19T23:18:58Z (`date -u`). Saved by the orchestrator from the claims-judge's final message; re-runs condensed, findings verbatim.

VERDICT: PASS

0 CRITICAL, 0 HIGH, 1 MEDIUM, 3 LOW. Round-2 N1, N2, N4 to N8 closed; N3 open by design (an edit to issue #45 at posting). The repair added one error (R3-M1, one clause), to fix before posting. Every number re-run matched the draft.

## Re-runs (read-only; outputs in scratch `r3-pr-judge/`)
Head `3b16d84` (`git archive` export, worktree `.venv`, `PYTHONPATH=<export>/src`): `run_baseline.py` exit 0, 34 of 34 `ok`, identical to the evidence file and draft:66-99. Base `949741f` `src/`: `run_baseline.py --kinds quote` exit 0, 20 lines byte-identical to the head's, `verified_fuzzy` 6568/6726/6656/6537, 0 `ROSE` (the evidence for R3-M1). Every quoted `git diff --quiet` exits as the draft says (:7, :29 for `fa71ccf` and `1ab8605`, :63 at `ece3623` and `2d4bd4d`, :149, :168 marker grep exit 1, :199 `git show --cc` 0 lines, :19 `coordinator.py` absent). Dispatch-log rows by `git log -S`: `fuzz-port-repair` → `merged` in `dbdab1a`; final gates in `a5fc368`; `records` → `judging` in `2a7d0e7`; the `e16065f` merge in `d5b02fc`. 16 verdict files' `VERDICT` lines and finding counts match the table. `tests/test_verify_claim_numbers.py:673` and `rules.py:145-146` on `3b16d84` as quoted. `test_bare_integers…` `cmp` exit 0 across `949741f`..`3b16d84`. `gh issue view 45`: OPEN, 5 comments, none edited.

## Round-2 findings: N1 closed (every log citation by event and commit; the other times are issue or plan-heading timestamps; the plan's correction note is at plan:272, `ccabd57`); N2 closed; N3 open by design; N4 closed (LOW leftover R3-L2); N5 closed; N6 closed but the repair added R3-M1; N7 closed; N8 closed. The repairer's own edits at :7, :9, :15, :19, :20, :29, :34, :36, :63, :115, :126, :145, :149, :164, :188-191 each hold against their cited artifact. Rule Zero scan clean; `Closes #45` at :3; attribution at :203; :188-189 end "round 3 pending".

## New findings (verbatim)

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| R3-M1 | draft:113 "`run_baseline.py --kinds quote`, run with `949741f`'s `src/` first on the path (`PYTHONPATH`; run that way, the base results are `949741f`'s: 10 `ROSE` lines and `verified_fuzzy` 6,568, …)" | Numbers (wrong set), I6 | MEDIUM | This ties the 10 `ROSE` lines to the `--kinds quote` run, which cannot print any: `quote` runs only the eleven PR #35 commands (`run_baseline.py:5`, `:214`). Re-run as written: exit 0, 20 lines, 0 `ROSE`. The cited source, issue-comment round-1 verdict :10, got the 10 `ROSE` lines from the full run. The `verified_fuzzy` values are right for the `--kinds quote` run. The draft's own :39 and :42 tie the `ROSE` lines to the full run correctly. Added by the N6 repair. | Replace the parenthesis with: "(`PYTHONPATH`; run that way, `fuzz_place2.py` prints `949741f`'s `verified_fuzzy` 6,568, 6,726, 6,656 and 6,537, and the full run, without `--kinds`, exits 1 with the 10 `ROSE` lines above; issue-comment claims verdict, round 1, `docs/superpowers/plans/verdicts/2026-11-19-gh45-issue-comment-claims.md`)" |
| R3-L1 | draft:129 "at least 6 of the 8 verified pricing claims did (`src/receipts/verify/rules.py:145-146` on `3b16d84`)" | I1 (source) | LOW | The figure is true, but the citation is this PR's own docstring repeating it, not where it was measured. The measurement record is issue #45's comment of 2026-11-15T17:20:57Z, line 5, and `docs/superpowers/plans/verdicts/2026-11-15-w3-readme-posts-claims-r2.md:95` (`live_repaired.out:17`). | "(issue #45's comment of 2026-11-15, 17:20 UTC; `docs/superpowers/plans/verdicts/2026-11-15-w3-readme-posts-claims-r2.md:95`; restated at `src/receipts/verify/rules.py:145-146` on `3b16d84`)" |
| R3-L2 | draft:15 "`tests/test_verify_claim_numbers.py:673`" | I1 (revision) | LOW | No commit is named; the line only holds from `counts-free` onward. | "`tests/test_verify_claim_numbers.py:673` on `3b16d84`" |
| R3-L3 | draft:16 the four "free" misses and the "Starter is free" verify | I1 | LOW | Present since round 1, true but unsourced; pinned at `tests/test_verify_claim_numbers.py:778`, `:788`, `:790`, `:792`, claim at `:825`, on `3b16d84`. | Append "(`tests/test_verify_claim_numbers.py:777-792` on `3b16d84`)" after "Starter is free". |

VERDICT: PASS

## Orchestrator disposition (2026-11-19T23:20:47Z, `date -u`)

R3-M1 and R3-L1 to L3 were applied to the draft by the orchestrator after this PASS, using the judge's replacement text verbatim and changing no other character (lines 113, 129, 15, 16). R3-M1's new clause states what the issue-comment round-1 verdict measured: the `--kinds quote` run prints the base `verified_fuzzy` values, and the full run exits 1 with the 10 `ROSE` lines. N3 (the dated note on issue #45's 2026-11-15 17:20 UTC comment) goes to "main" and the owner for posting time.
