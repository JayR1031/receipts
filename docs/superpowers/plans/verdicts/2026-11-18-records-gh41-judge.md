# Judge verdict: `records-gh41` (PR #54, JayR1031/receipts)

Blind review in a fresh context, 2026-11-18, about 06:10 to 06:20 UTC.

- **What was judged:** `git diff origin/main...HEAD` in `.worktrees/records-gh41`, at HEAD `10c1053` on base `949741f`. That is 24 files, 3162 lines added and 33 deleted.
- **Ticket:** commit the records that exist only on the owner's machine, so the citations at spec :50 and ADR-0008 :47 and :63 resolve.
- **Not run:** no live runs, no model calls.

## Findings

| # | Severity | Finding | Citation | Fix |
|---|---|---|---|---|
| 1 | MEDIUM | **The secret-shape claim names no command.** The PR body says "the key and DSN patterns from PR #51 find nothing (exit 1)", but gives no command, so nobody can re-run it. PR #51's own body cites gitleaks as its secret scan, not key or DSN patterns. The pattern appears, cut short, only at `docs/superpowers/plans/verdicts/2026-11-16-w3-records-judge-r2.md:47`. PR #51's round-2 judge raised the same gap there (its MEDIUM 2). The claim itself holds: both of my gitleaks runs were clean. | `gh pr view 54 --json body` (exit 0), the "Secret shapes" line. `gh pr view 51 --json body` (exit 0), body line 19. My runs: `gitleaks git . --log-opts=origin/main..HEAD --redact --exit-code 1` exited 0, "no leaks found". `gitleaks dir docs/superpowers --redact --exit-code 1` exited 0. | Replace the line with the two gitleaks commands and their exit codes, or print the grep command itself. |
| 2 | LOW | **The PR body still holds an unfilled placeholder:** `**Reviews:** {REVIEWS}`. | `gh pr view 54 --json body` (exit 0), the line before the attribution. | Fill it with this verdict's path and result before merge, or delete the line. |
| 3 | LOW | **The "Not included" list leaves out one file.** It names only the #41 brief. The owner's machine also holds `docs/superpowers/briefs/2026-11-16-gh45-verifier-follow-ups.md`. That file is untracked in the main checkout, absent from `origin/main` and absent from this diff. It was created at 2026-11-18T01:08:55-0500, 22 seconds before commit `10c1053` (01:09:17 -0500). It is a brief for open work on issue #45, not a review record or a plan, so it is not a scope miss. But the ticket says "push it all". | `git -C /Users/jay/Projects/receipts ls-files --others --exclude-standard docs/superpowers` lists it. `git cat-file -e origin/main:<path>` exits 1. It is not in `git diff --name-only origin/main...HEAD`. `stat -f '%SB'` gives the creation time. | Name it under "Not included", with the reason (it ships with the #45 PR), or add it. |
| 4 | LOW | **The body mislabels the cited ruling and under-describes the W0/W1 change.** The body calls the ruling spec :50 cites "the coordinator's scope-cut ruling". It is actually `## Coordinator rulings 2026-11-15 01:11 UTC`, at W0/W1 plan :387-391 with the l4-constraints row at :442. That is a different section from `## Scope cut 2026-11-14` at :20. The body also lists 3 items for a change of 271 added and 33 deleted lines. The change also adds the W2 facts bullet (:333) and the sections from :336 to :414 (PR #11 notes, Escalations, W1 wiring convention, L2 coordinator spec, W1 complete, Status sync, W2 second opinion). | `grep -n -E '^#' docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md` (exit 0). `git diff --numstat origin/main...HEAD`. | Name the ruling by its heading, and list the added sections. |
| 5 | LOW | **The W0/W1 plan's top line contradicts this change (rubric 7).** Line :3 still reads "Written 2026-11-14 (hackathon H0–1); nothing dispatched yet." This diff sets the tasks to `merged` and adds `## W1 complete — 01:30 UTC` (:402). The top of the record was not fixed. | `docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md:3`, `:402` | Update :3 to the final state. That is part of "advance it to its final state". |
| 6 | LOW | **The #41 plan's top line and its status line contradict its own content (rubric 7).** Line :3 reads "nothing dispatched yet; awaiting the owner's approval." Line :399 reads "PR: not yet opened". Yet :399 also says "All tasks terminal 2026-11-16 07:21 UTC", and PR #52 merged at 2026-11-16T10:45:46Z as `949741f`. | `docs/superpowers/plans/2026-11-15-gh41-google-sign-in.md:3`, `:399`. `gh pr view 52 --json state,mergedAt,mergeCommit` (exit 0): `MERGED 2026-11-16T10:45:46Z 949741f`. | Update :3 and :399 to the state on record. |
| 7 | LOW | **"Brought up to its final state" overstates.** The file is the owner's last copy (byte-identical), so the ticket's rule is met. But it stops with `w2` at `judging` (:310, and :449 with verdict "pending") and `w3` at `planned` (:320, :450). On GitHub, PR #29 merged at 2026-11-15T03:00:34Z and issues #19 and #20 are closed. | `grep -n -E '^state = "(judging\|planned\|running)"'` on the plan (exit 0). `gh pr view 29 --json state,mergedAt` (exit 0). `gh issue view 19` and `gh issue view 20` both show CLOSED. | Say "the owner's last copy", and note that w2 and w3 stop at judging and planned. Or update those two rows. |

## Checks that found nothing

**Scope**
- All 24 changed paths are under `docs/superpowers/` (`git diff --name-only origin/main...HEAD`).
- No workflow, `.gitleaksignore`, test or code file is touched. The gitleaks gate still blocks: `security.yml:22` has `--exit-code 1`.

**Provenance**
- All 24 files are byte-identical to the owner's copies in `/Users/jay/Projects/receipts` (`cmp`, 24 of 24 the same).

**The #41 brief is correctly excluded**
- `main`'s copy is the later one. At :32, `main` has the corrected `IdentityProvider` protocol wording; the owner's copy still has the older wording.
- `main` committed it in `949741f` on 2026-11-16. The owner's copy was last modified on 2026-11-14 at 23:39 -0500.

**The W0/W1 change only advances the plan**
- All 33 deleted lines are superseded task states, deps, titles, scopes or status-table rows.
- `bin/plan-check` exits 0 on this plan with "20 tasks, 0 problems", and on the #41 plan with "17 tasks, 0 problems".

**Citations, as read on `origin/main`**
- Spec :50, "W1 plan, coordinator ruling 2026-11-15", resolves to W0/W1 plan :387-391 and :442.
- Spec :50, "owner's answer 2, 2026-11-16", resolves to #41 plan :334-336.
- ADR-0008 :47, "owner's answer (a) in the issue #41 plan", resolves to #41 plan :336, which says "additive changes only … test rows deleted".
- ADR-0008 :63 resolves to `verdicts/2026-11-15-gh41-records-repair.md:74-75`:
  - SQLite: exit 1, 1 failed of 13.
  - Neon: exit 1, 1 failed of 12, with `test_duplicate_user_sub_is_rejected` PASSED.
  - The run was 2026-11-16 07:00-07:06 UTC (:3).
- Before this PR, `origin/main` had neither new file (`git cat-file -e` exits 1) and no :387 section.

**Counts in the PR body**
- 24 files.
- 21 verdicts:
  - 17 files named `2026-11-15-gh41-*`;
  - 2 claims checks;
  - 1 gh48 round 2;
  - 1 W3 records round 3.
- Plus 1 new plan, 1 brief and 1 changed plan, for 24 in total. All correct.
- The #41 plan does give every task's state and verdict: 17 rows at :381-397, and every verdict path it cites exists.

**Email addresses**
- 5 matches in 5 of the 24 files, all at `example.com`, which matches the body's 5:
  - `gh41-db-repair.md:124`
  - `gh41-oidc.md:110`
  - `gh41-provider.md:59`
  - `gh41-routes.md:28`
  - `gh41-wiring-repair.md:96`

**Secrets and personal data (my 26-pattern scan over the 24 files, exit 0)**
- 0 hits for API keys, Google client secrets or ids, private keys, JWTs, DSNs with passwords, Neon hosts, phone numbers, GPS coordinates or IPv4 addresses.
- The only 40-hex string is a git SHA (`gh48-r2.md:3`).
- A case-sensitive scan of added lines for usernames and press bylines exits 1: none.

**Codex details (shape scan; nothing printed)**
- No Codex session id, folder, file name or settings key was found.
- All 5 UUIDs are Claude Code scratchpad session ids, at `gh41-routes.md:3`, `gh41-routes-dbfail.md:3`, `gh41-pr-body-claims.md:3` and `gh41-pr-body-claims-r2.md:3,8`. `main` already carries the same kind in at least 10 files.
- Lines that mention Codex (W0/W1 :26, :59, :329; `w3-records-judge-r3.md` :33, :35, :42, :43, :65) describe it by shape only. The four clock times at r3 :35 are labelled as PR-body revision times.
- I could not re-run the owner's withheld pattern: it is kept outside the repository and I did not find it. So the body's "exit 1" for that scan is accepted, not reproduced.

**Infrastructure identifiers newly made public (W0/W1 :333 and :349-374)**
- A Render owner id, a workspace name, and Vercel deployment ids and team slug. None is a credential.
- The Render service id and `dpl_` ids are already on `main` (`docs/runbooks/render.md:3`, `verdicts/2026-11-15-gh42.md:6`).
- The team slug contains the owner's surname. That is already public in 22 author and committer name lines of `main`'s history and in the owner's public GitHub profile name.

**Gates**
- `python3 -I scripts/leak_gate/check_tracked.py` exited 0: "scanned 226 files against 2 patterns".
- `gh pr checks 54` exited 0. All 5 checks pass: api-image, ci-python, dependency-audit, gitleaks, leak-gate.

**Rubric items 2, 3 and 4** (tests, watched failing, typed boundaries) do not apply: the PR changes docs only, and no test or code changed.

VERDICT: PASS
