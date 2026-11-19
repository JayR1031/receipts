# Verdict: gh45 issue #45 comment draft, round 2 (claims-judge, fresh context, 2026-11-19)

Draft: scratch `gh45-drafts/issue-45-comment.md` (36 lines). Branch at `a5fc368`; head named in the draft `3b16d84`; base `949741f`. Saved by the orchestrator from the claims-judge's final message; the re-run list condensed, findings verbatim.

VERDICT: FAIL

All round-1 fixes landed; every number re-measured the same on both revisions (6 brief probes plus 19 rule and limit examples; `run_baseline.py` with `3b16d84`'s and `949741f`'s `src/` on `PYTHONPATH`: exit 0 with 34 of 34 `ok` identical to the evidence file, and exit 1 with exactly the 10 `ROSE` lines; the 20 quote lines byte-identical); every new source exists (`tests/test_verify.py:963`; `README.md:258` at `3b16d84` vs `:220` at `949741f`; the 17:16:32 UTC follow-up in the issue's 17:20:57Z comment; 12 verdict files). The draft fails on one new sentence. 1 HIGH, 2 MEDIUM, 6 LOW.

## Round-1 findings: H1, H2, H3, M1, M3, M4, LOW 1 to 8 closed (LOW 1 with the allowed `PR #<n>` placeholder, the only placeholder; LOW 7 closed outside the draft by the evidence file's header). M2 closed in the draft; its I5 half (a dated note on the issue's 17:20 comment) is open as M-b.

## New findings (verbatim)

| # | Claim (quoted) | Invariant | Severity | Evidence or what is missing | Fix |
|---|---|---|---|---|---|
| N1 | draft:12 "(later commits add verdict files only)" | I1, I2 | HIGH | False as written, and no source is given. `git diff --name-only 3b16d84 HEAD` (HEAD = `a5fc368`) lists `docs/superpowers/plans/2026-11-16-gh45-verifier-follow-ups.md` as well as two verdict files; `a5fc368` ("…; plan log") adds plan lines 314-315. "Later" has no end point, and saving this verdict will add more plan-log lines. The scoped version is true: `git diff --quiet 3b16d84 HEAD -- src tests scripts README.md docs/verifier.md docs/adr` exits 0 (re-run at `a5fc368`), as the evidence file's line 1 and `pr-body.md:63` say. | Replace it with: "(later commits change no file under `src`, `tests`, `scripts` or `docs/adr`, nor `README.md` or `docs/verifier.md`: `git diff --quiet 3b16d84 HEAD -- src tests scripts README.md docs/verifier.md docs/adr` exit 0)". |
| M-a | draft:12 "(plan dispatch log, 2026-11-19 22:30; …)" | I1 (revision) | MEDIUM | The entry is plan line 314, added by `a5fc368`. It is not on `3b16d84`, the revision the sentence names (`git show 3b16d84:<plan> \| grep -c '2026-11-19 22:30'` gives 0). The "22:30" label is also not a real time. `a5fc368`, which adds the entry, was committed at 2026-11-19T19:40:49Z, and this judge's clock read 19:53 UTC. The log runs about two hours ahead of the commits: the row stamped "21:20" names `8f5876a`, which was committed at 19:14:54Z. | Cite "`docs/superpowers/plans/2026-11-16-gh45-verifier-follow-ups.md:314` at `a5fc368`". The same label appears at `pr-body.md:63` and `:164`. |
| M-b | draft:8, the correction of the 17:16:32 UTC follow-up | I5 | MEDIUM | The correction exists only in this new comment. The 2026-11-15T17:20:57Z comment still ends "The owner's chosen follow-up for 2 (17:16:32 UTC): count claims with identical receipts once." with no dated note (`gh issue view 45`, exit 0). The 06:43 comment's "> **Superseded (2026-11-15 07:49 UTC).**" line shows the convention. | The owner or orchestrator, when posting, edits the 17:20 comment's item 2 to open with "> **Replaced (2026-11-19):** on 2026-11-18 the owner chose to reject duplicate repairs instead (PR #<n>)." |
| L1 | draft:1 "(recorded in the plan, …)" | I1 | LOW | The plan records the 2026-11-18 06:16:22 UTC approval (plan:248-254) and the 2026-11-19 answers (plan:256-262). The rule scope, Q1 to Q3, is recorded in the brief (`:11`, `:13`, `:189-192`), and the comment never names the brief. | Use "(recorded in the brief, `docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md:189-192`, and the plan's sections "Approval and answers" and "Owner answers before `records`")". |
| L2 | draft:8 "recorded in this issue's comment of that day" | Clarity | LOW | All five comments are dated 2026-11-15. | Use "in this issue's comment of 2026-11-15, 17:20 UTC". |
| L3 | draft:8 "`Coordinator`'s verified/total is unchanged" | Clarity | LOW | The counting code is unchanged, but the number is meant to change: a refused copy no longer adds a verified claim. | Use "`Coordinator` counts verified/total as before (`coordinator.py` is not in the diff `origin/main...HEAD`; whole-PR verdict, Verification 1)". |
| L4 | draft:16 "`949741f`'s counts are `expected.txt`'s quote lines" | Numbers (set) | LOW | The claim-shape counts in :15 are not in `expected.txt` (`expected.txt:33-34`: targets, "not 949741f's counts"). | Use "`949741f`'s quote counts are `expected.txt`'s quote lines (`expected.txt:1`); all its counts were re-measured by …". |
| L5 | draft:15 "(all 147 that cite a negated or trial free; the other 153 …)" | I1 | LOW | True, source not named: `verdicts/2026-11-18-gh45-fuzz-claims.md`, gate 4(d). | Append "(`fuzz-claims` verdict, gate 4(d))". |
| L6 | draft:12 short verdict path; draft:24 "(the PR-body claims verdict)"; draft:3 "whose `src/` equals `3b16d84`'s"; draft:10 "read with `gh issue view 45`" | I1, I6 | LOW | All true; the first is a short path to a FAIL verdict, the second has no path, the last two give no command or exit code. | Full paths with "(round 1)"; add "(`git diff --quiet 923c5af 3b16d84 -- src` exit 0)" and "`--json body,comments`, exit 0". |

Note for the PR-body judge: `pr-body.md:63` has the same wording as N1 and the same "22:30" label.

VERDICT: FAIL

## Orchestrator disposition (2026-11-19T20:02:35Z, read from `date -u`)

- **N1, M-a, L1 to L6:** draft repair 2 of 3, with the PR-body round-2 findings, in one pass.
- **M-a is also a defect in this plan.** Every dispatch-log time from 2026-11-18 06:17 to 2026-11-19 23:10 was a label the orchestrator wrote, not a clock reading; the labels run about two hours ahead of the commits that carry them. The plan now says so at the top of its dispatch log, and `git log --format='%h %cI'` on the integration branch is the time record. From this entry on, log times are read from `date -u`.
- **M-b:** for "main" and the owner at posting time: the issue's 2026-11-15 17:20 UTC comment, item 2, gets a dated "Replaced (2026-11-19)" note.
