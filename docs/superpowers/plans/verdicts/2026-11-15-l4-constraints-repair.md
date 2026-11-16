# Verdict: l4-constraints-repair (gh-16, PR #32)

- **Reviewed:** branch `jay/gh-16-l4-constraints`, head `6d261ec`, base `origin/main` = `2244225`, worktree `/Users/jay/Projects/receipts/.worktrees/l4c`. Repair diff `git diff 7583d85..6d261ec` touches 1 file (+17/-1).
- **Judge:** blind, fresh context. Read-only apart from running tests and one temporary sabotage edit, which was reverted (see item 1). Prior verdict: `docs/superpowers/plans/verdicts/2026-11-15-l4-constraints.md` (FAIL on `7583d85`).

## Rubric results

| Item | Result | Evidence |
|---|---|---|
| 1 MEDIUM #1 (PK sabotage) | Resolved | The PR body (`gh pr view 32 --json body`, exit 0) has "`test_duplicate_primary_key_is_rejected`, second insert given a fresh id (both rows deleted): `Failed: DID NOT RAISE IntegrityError`, `1 failed`, exit 1; restored, passes." **I reproduced it.** I changed `:89` to insert `_valid(fresh_id)` and put deletes for both `run_id` and `fresh_id` in the `finally`. Then `pytest ... -m integration -k duplicate` gave `E Failed: DID NOT RAISE IntegrityError` at `tests/test_db_constraints.py:89`, `1 failed, 6 deselected`, exit 1. Restore: `git checkout -- tests/test_db_constraints.py`, then `git diff --exit-code` exit 0 and `git status --short` empty. Leftover `constraint-test-%` rows = 0 (measured after the full run below). |
| 2 LOW #2 (NULL id) | Resolved, with LOW #1 below | `tests/test_db_constraints.py:104-113`: total `count(*)` before (`:105-106`), `values["id"] = null()` (`:108`), `pytest.raises(IntegrityError)` around `engine.begin()` (`:109-110`), count after (`:111-112`), `assert after == before` (`:113`). The PR body says the sabotage (valid id instead of `null()`) gave `DID NOT RAISE`, `1 failed`, exit 1. Cleanup: there is none. That is safe for the committed version, because while the PK exists Postgres rejects the insert and the `begin()` block rolls back, so nothing persists. If the guard is missing (the sabotaged case), the row is accepted and nothing removes it. That matches the leak the implementer reported. After my runs, `SELECT count(*) FROM runs WHERE id IS NULL` = 0. |
| 3 LOW #3 (varchar note) | Resolved, with LOW #2 below | `tests/test_db_constraints.py:10-12` says that the `varchar(n)` limits are "intentionally untested", "enforced only on Postgres", "raise `DataError` rather than `IntegrityError`" and are "outside the constraint kinds listed at spec:48". |
| 4 LOW #5 (PR template) | Resolved, with LOW #3 and #4 below | The body headings `## What and why`, `## Ticket` (`#16`) and `## Evidence` match `.github/PULL_REQUEST_TEMPLATE.md:1-9`. All four evidence checkboxes are `[x]`. The jig table is identical to my `bin/jig` output (exit 0, rows `python format/lint/types/tests ok`). Four reds are named. The prior verdict is named by path. `bin/red-test` is named as not run ("no gate touched"). |
| 5 Neon run | Met | `source ~/.zshenv && PYTHONPYCACHEPREFIX=/tmp/pyc-judge-l4cr uv run pytest tests/test_db_constraints.py -q -m integration -rs -p no:cacheprovider` gave `7 passed in 6.05s`, exit 0. A follow-up count snippet (the pipeline exited 0 and printed all three counts) gave: `id LIKE 'constraint-test-%'` = **0**, `id IS NULL` = **0**, total `count(*) FROM runs` = **1** (content not read). Without `DATABASE_URL` (`env -u DATABASE_URL ...`), 7 of 7 skipped, exit 0, reason `DATABASE_URL not set: runs-table constraint tests (test_db_constraints) skipped`. |
| 6 Gates | Met | Scope: `git diff --name-only 2244225...6d261ec` gave only `tests/test_db_constraints.py` (exit 0). `uv run pyright` gave `0 errors, 0 warnings, 0 informations`, exit 0. `uv lock --check` exit 0. `grep -nE "Any\|type: ignore\|pyright: ignore\|noqa" tests/test_db_constraints.py` exit 1 (no matches). Ruleset `27284472` requires 5 checks (`gh api .../rules/branches/main`, exit 0). On `6d261ec` all 5 passed: gitleaks, leak-gate, dependency-audit, ci-python, api-image (`gh pr checks 32` exit 0; check-runs API shows `head_sha` `6d261ec`). The third-party check `Mermaid Diagram Sync Assistant` was skipped and is not counted. |
| Security floor | Met | The file holds no secrets or URL. No gate, ignore entry or test was removed (one-file additive diff). |

## Findings

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | LOW | `test_null_id_is_rejected` compares the **whole table's** row count, and that table is a shared, live database. Any write to `runs` between `:106` and `:112` (for example the demo app starting a run) makes the test fail even though the constraint holds. The test also has no `finally`, so when the guard is missing it leaves behind a row with a NULL id that no query in the file can find. | `tests/test_db_constraints.py:105-113`. Total `count(*) FROM runs` = 1 (count snippet exit 0), so the database is shared and not isolated. | Tag the row with a unique marker (for example `subject=f"constraint-test-{uuid4()}"`), count and delete on that marker, and put the delete in a `finally` |
| 2 | LOW | The new varchar sentence broke what "these" refers to. Line 13, "SQLite would also enforce these", now directly follows the sentence saying the varchar limits are "enforced only on Postgres" (`:11`). So it reads as a claim that SQLite enforces the length limits, which contradicts `:11`. | `tests/test_db_constraints.py:10-13` | Move the varchar sentence after `:13-14`, or change "these" to "the PK and NOT NULL constraints" |
| 3 | LOW | Two of the four reds in the PR body have no exit code: the import-only `NameError: name 'Engine' is not defined` and the five NULL-sabotage `DID NOT RAISE` results. The two new reds do state exit 1. | `gh pr view 32 --json body` (exit 0), Evidence bullets 1-2. AGENTS rubric 6 ("every 'verified' has a command and its exit code") | Add the exit code (and the `N failed` count) to both bullets |
| 4 | LOW | The "attached" `/judge` verdict is a path that does not exist on any branch. Readers of the PR cannot open it. The body also calls MEDIUM #1 "resolved" before any re-review had been done. | `git -C /Users/jay/Projects/receipts status --short docs/superpowers/plans/verdicts/` gives `?? docs/superpowers/plans/verdicts/` (untracked). `gh pr view 32 --json body` (exit 0) | Paste the verdict table into a PR comment (or commit the verdicts directory), and link this re-review |
| 5 | LOW (accepted) | Carried over as prior LOW #4: the tests write to the `DATABASE_URL` demo database (total 1 row), not the Neon `dev` branch the spec names. The coordinator accepted this target. Measured leftovers are 0. | `tests/test_db_constraints.py:41,86-93`. `docs/superpowers/specs/2026-11-14-receipts-design.md:48`. Count snippet exit 0 | No action. Accepted by the coordinator. |

No CRITICAL, HIGH or MEDIUM findings. Prior MEDIUM #1 is resolved: the sabotage was run independently and gave `DID NOT RAISE IntegrityError`, exit 1.

## Worktree

After the sabotage was reverted, `git -C /Users/jay/Projects/receipts/.worktrees/l4c diff --exit-code` exit 0. `git status --short` returned nothing at the end of the review, after `bin/jig` (exit 0). HEAD is still `6d261ec`.

## Verdict

PASS needs zero HIGH and every MEDIUM resolved or accepted with a reason. There are 0 HIGH. The one prior MEDIUM is resolved and was reproduced. LOW #1-#4 are new or residual and do not block. LOW #5 is accepted by the coordinator.

VERDICT: PASS

Practice applied: Watch it fail for the right reason (AGENTS.md s4). I did not take the PR's sabotage claim on trust; I re-ran it. The PK test failed with `DID NOT RAISE IntegrityError` at `:89`, exit 1, and passed again once restored.
