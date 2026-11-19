# Verdict: gh45 PR body draft, round 2 (claims-judge, fresh context, 2026-11-19)

Draft: scratch `gh45-drafts/pr-body.md` (203 lines). Checked against `jay/gh-45-verifier-follow-ups` at `a5fc368` (code equals `3b16d84`). Review time 2026-11-19 19:54:18Z (`date -u`). Saved by the orchestrator from the claims-judge's final message; re-runs condensed, findings verbatim.

VERDICT: PASS

0 CRITICAL, 0 HIGH, 3 MEDIUM, 5 LOW. All 14 round-1 findings closed (M2, M5, M7 with a leftover). The edits added no false number but three MEDIUM defects: false dispatch-log time labels in the new citations, a false "verdict files only", and an earlier issue comment with no correction note. The judge asks for the three MEDIUMs to be fixed before posting. `Closes #45` at :3; attribution at :203.

## Re-runs (read-only)
Head `run_baseline.py` exit 0, 34 lines = draft:66-99 and the evidence file (diff exit 0); base run with `PYTHONPATH=<git archive 949741f src>` exit 1, 10 `ROSE` = draft:45-54, 20 quote lines byte-identical; `fuzz_place2.py 7 200` RULES line names the base copy; 14 verdict files' VERDICT lines and finding counts match draft:176-189; `git diff --quiet 949741f 3b2673c -- src tests scripts` exit 0; `923c5af`..`3b16d84` `-- src` exit 0; `604e54f`..`923c5af` comments/docstrings only; `949741f` = `fa71ccf` = `1ab8605` in `src/receipts/verify`; `git show --cc --format= e16065f` 0 lines; marker grep exit 1; `test_bare_integers…` `cmp` exit 0 across `949741f`..`3b16d84`; `gh issue view 45`: OPEN, 5 comments, none edited, only 19:38:00Z names `$20k` (claim side).

## Round-1 findings: H1, H2, M1, M3, M4, M6, L1, L2, L3, L5 closed; M2 closed (LOW leftover N6); M5 closed with a new error (N2); M7 closed (LOW leftover N5); L4 closed (time label → N1).

## New findings (verbatim)

### MEDIUM
**N1 (I1): the cited dispatch-log times are not UTC.** Draft :29 "(plan dispatch log, 2026-11-18 07:25)"; :63 "(plan dispatch log, 2026-11-19 22:30 …)" and "2026-11-19 19:20 to 22:30"; :164 "(plan dispatch log, 2026-11-19 22:30 …)"; :199 "(plan dispatch log, 2026-11-19 18:05)". The log's column is headed "Time (UTC)" (plan:272), yet each cited row was committed before the time on its label: the 07:25 row in `dbdab1a` at 2026-11-18 06:53:47Z; the 18:05 row in `d5b02fc` at 2026-11-19 17:57:33Z; the 19:20 row in `2a7d0e7` at 18:29:47Z; the 22:30 and 23:10 rows in `a5fc368` at 19:40:49Z. Some rows conflict the other way (the 09:05 row says "merged as `641eadd`", committed 17:35:24Z). The rows' content supports each claim; only the time labels are false. **Fix:** cite rows by event and commit, not time: :29 → "(plan dispatch log, the `fuzz-port-repair` → `merged` row)"; :63 and :164 → "(plan dispatch log, the final-gates row for `3b16d84`, added in `a5fc368`)"; :63's range → "(plan dispatch log, the rows from `records` → `judging` to the final gates)"; :199 → "(plan dispatch log, the `e16065f` merge row)". Separately, the orchestrator adds a dated note at the top of the log saying its times are not UTC and that commit times are authoritative (I5).

**N2 (Rule Zero, I2): "add verdict files only" is false.** Draft :63. `git diff --name-only 3b16d84 HEAD` also lists the plan, because `a5fc368` adds two log rows; the cited pathspec leaves out `docs/superpowers/`. **Fix:** "Later commits on the branch change only `docs/superpowers/` (verdict files and the plan's dispatch log): `git diff --quiet 3b16d84 HEAD -- . ':(exclude)docs/superpowers'` exit 0." (run: exit 0).

**N3 (I5): the earlier issue comment carries no correction note.** Draft :19 quotes the 2026-11-15T17:20:57Z comment exactly, but that comment's top has no dated note (`lastEditedAt` null); the 06:43:22Z comment shows the pattern ("> **Superseded (2026-11-15 07:49 UTC).**"). **Fix:** outside the draft, for the owner or orchestrator at posting: prepend to the 17:20:57Z comment "> **Updated 2026-11-19.** Item 2's follow-up was replaced on 2026-11-18: the owner chose to reject duplicate repairs, not to count identical receipts once (PR #<n>, ADR-0007)." Draft:19 can stay.

### LOW
**N4:** :15 cites probe 5 for "Max includes 500 credits." but probe 5's claim is "Mel Max has 500 credits."; the exact example is `tests/test_verify_claim_numbers.py:673`. Fix: "(note …; `tests/test_verify_claim_numbers.py:673`; probe 5 below makes the same check with "Mel Max has 500 credits.")".
**N5:** :102 (the M7 sentence) leaves out `control` and reads as a complete list of unmeasured fail-open limits while missing several (`500 seats` for `500 credits`, `5 very active users`, another plan's "free", (g) swapped values, "bucks", the copied receipt). Fix: "The claim shapes other than `control` generate only spellings inside rules (a) to (d) (`fuzz-claims` verdict, gate 4(b)); `control` measures whole numbers with no unit. No shape generates any other fail-open limit below (among them a count with another unit, `500 seats` for `500 credits`; `30 days`; `5 very active users`; "free 14-day trial"; another plan's "free"; "25 pounds"; `$20 million`; the `$5m`/`$5mo` cut; swapped values), so 0 of 300 does not measure them."
**N6:** :113's RULES-line clause has no source (true by the judge's run). Fix: drop it or cite "the base results are `949741f`'s: 10 `ROSE` lines and `verified_fuzzy` 6,568, 6,726, 6,656 and 6,537 (issue-comment claims verdict)".
**N7:** :29 "all five pytest runs" no longer names its set (six pytest rows). Fix: "re-ran the five per-task pytest runs, the first row's three runs at `949741f` (its M4), and the measurement's red run".
**N8:** :126 "2 of 3,678 add-a-word misquotes scoring at least 90" lacks its verb. Fix: "and 2 of the 3,678 add-a-word misquotes that score at least 90 verified (10,994 generated)".

VERDICT: PASS

## Orchestrator disposition (2026-11-19T20:04:33Z, `date -u`)

- N1's "separately" item is done: the plan's dispatch log opens with a dated correction (commit `ccabd57`).
- N1, N2, N4 to N8 are applied in draft repair 2 of 3, together with the comment's round-2 findings; both drafts then go to round 3, because this PASS predates those edits.
- N3 goes to "main" and the owner for posting time, with the comment verdict's M-b.
