# Judge verdict: gh-41 `records-repair` (repair attempt 1 of 3 after the whole-PR FAIL, issue #41, Sign in with Google)

Blind re-judge, fresh context. Runs from 2026-11-16 07:00:43 to 07:06:45 UTC (`date -u`).

- **What was judged.** Worktree `.worktrees/gh41-records`, branch `jay/gh-41-records`, head `66e6095`. Its one parent is `3145d8f`, the head the whole-PR judge failed (`git rev-list --parents -n1 66e6095`).
  - Repair diff: `git diff 3145d8f...66e6095`.
  - Whole-PR diff: `git diff origin/main...66e6095`. `origin/main` is `c5d0114`, which is also the merge base.
- **What I read.** The previous verdict `verdicts/2026-11-15-gh41-records-whole-pr.md`. `AGENTS.md` sections 0, 4 and 7. From the plan: the `records-repair` block (:291-302) and "Approval and answers" (:321-323). The brief's File scope (:29-42) and Verification (:62-81). The W1 plan's Neon and `dev` lines. The `l4`, `l4-repair`, `l4-constraints` and `l4-constraints-repair` verdicts.
- **UNSET** below means `env -u VIRTUAL_ENV -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE`. `VIRTUAL_ENV` is unset only to silence uv's environment-mismatch warning; it is not a setting.
- **The Neon steps.** They kept `DATABASE_URL` set and the other six names unset.
- **Exit codes and caches.** I captured exit codes with `$?` on output written to a file, never through a pipe. Bytecode caches were removed before each pytest or jig run (AGENTS.md section 1).
- **The sabotage.** It was one edit in the working tree, reverted with `git checkout -- src/`. I used no stash, made no commit and created no worktree. There were no model or Keenable calls and no live runs.
- **No DDL changed anything on Neon.** The fixture's `create_schema` found every table, column and index already present. `users_sub_key` on `sub` was present before and after.
- **End state.** `git status --porcelain` prints 0 lines, `git diff --exit-code` exits 0, `git diff --cached --exit-code` exits 0, and HEAD is still `66e6095`.
- **Nothing from the environment is printed here.** The Neon count script (`scratchpad/scripts/neon_counts.py`) prints only integers and booleans. My Neon pytest run left out the runbook's `--tb=short` (`docs/runbooks/render.md:137-143`). Its long traceback therefore wrote the `engine` fixture's repr into a scratchpad file: database user and host, password masked as `***`. I confirmed that with a count-only grep. I never displayed that line, and I deleted the file (`rm` exit 0). The next re-judge dispatch should carry `--tb=short`.

## Findings

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | MEDIUM (new, open, not accepted) | **Spec :50 opens with a sentence no artifact supports: "One Neon database, `main`, for building and the demo."** It asserts a count (one, so no `dev` branch exists) and a name (`main`). The records establish only that the integration tests and the deployed app use the same database, the one `DATABASE_URL` names, and not a `dev` branch. No record names the Neon branch or database `main`. Spec :67, in the same file, still lists "Neon with a `dev` branch" as an owner setup step, and no record says whether that branch was made. A second method contradicts the literal reading: the Postgres database the tests and the app share is not named `main`. A Neon branch name cannot be read from SQL, and I had no Neon API access, so the branch list was not checked. | `docs/superpowers/specs/2026-11-14-receipts-design.md:50`, `:67`. **Supported:** `docs/runbooks/render.md:103-104` ("`DATABASE_URL` in `~/.zshenv` is the deployed Neon database"); W1 plan `docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md:442` ("tests hit the demo DB not a `dev` branch — accepted by the coordinator"); `verdicts/2026-11-15-l4-constraints-repair.md:26`; gh41 plan :348. **Search scope:** every `*.md` in the worktree at `66e6095` (`.venv` excluded), grepped for lines with "neon" and any of `` `main` ``, "main branch", "branch", "one database", "same database", "demo db", "deployed" (exit 0). Among those lines, only spec :50 names `main` as a Neon database or branch; the other hits concern the deployed database, the `dev` branch, or git branches (README :522, the `gh33` claims verdicts). In the main checkout, the W1 plan grep for `\bdev\b` (exit 0) hits :333, :441 and :442 on Neon (its other hits, :353, :374 and :380, are `/dev/null` in shell commands); none of them says a `dev` branch was created. **Second method:** Neon `select current_database() = 'main'` gives `False` (count script, exit 0, 07:02:51 and 07:03:47 UTC). | Narrow the first sentence to what is known, for example: "The integration tests and the deployed app use the same Neon database, the one `DATABASE_URL` names; no `dev` branch is in use." This is one sentence inside the `records-repair` scope; it would be repair attempt 2 of 3. |
| 2 | LOW | **Spec :50 lists the `claim_run` round trip among the things proven "by inserting the row it exists to stop".** The round trip inserts a valid run, claims it, and reads `user_id` back. Nothing is rejected; it shows the column exists on Neon. | `docs/superpowers/specs/2026-11-14-receipts-design.md:50`; `tests/test_db_constraints.py:209-229` (valid insert at :217, positive asserts at :221-223) | "...and the `runs.user_id` foreign key; a `claim_run` round trip shows the column exists on Neon." |
| 3 | LOW | **Spec :50's "not yet proven" list leaves out the `users` primary key.** No Neon test inserts a duplicate or NULL `users.id`. The two `insert(USERS)` calls use two different ids, and `null()` appears only on `runs`. So the `users` table has 5 constraints: 1 is proven by a rejected insert (`sub` UNIQUE) and 4 are not (the primary key and the 3 NOT NULLs). The spec names 3 of those 4. | `src/receipts/db/schema.py:58-61`; `tests/test_db_constraints.py:178` (two ids), `:181`, `:183` (the only `insert(USERS)`); `grep -nE 'null\(\)' tests/test_db_constraints.py` hits only `:157` and `:165`, both on `RUNS` (exit 0) | Add "and the `users.id` primary key" to the not-yet-proven sentence. |
| 4 | LOW | **ADR-0008:64 says the `routes.py` docstring describes the 503 path "as the row write only".** The docstring says "while that row is read or written". The rest of the bullet holds: the `except SQLAlchemyError` also covers `get_user_repo`, which builds `SqlUserRepo` and runs `create_schema`. | `docs/adr/0008-google-sign-in.md:64`; `src/receipts/auth/routes.py:14-15` against `:281` → `:203-213` (`SqlUserRepo()` :210, `create_schema` :211), inside the `try` at `:333-340` (`except SQLAlchemyError` :337) | "...describes the 503 `user_store` path as the row read or write only..." |
| 5 | LOW | **ADR-0008:63 gives "1 of 12" and "1 of 13" without saying which run produced them.** The implementer's report says they were taken from the brief, not re-run. The bullet just above (:62) names its source runs, as AGENTS.md section 7 asks. Both numbers are true: I reproduced them on `66e6095` (check 3). | `docs/adr/0008-google-sign-in.md:62` (names "the `oidc` and `provider` judges' sabotage runs") against `:63` (no source) | Append the source, for example "(the whole-PR judge on `3145d8f` and the re-judge on `66e6095`, 2026-11-16)". |
| 6 | LOW (outside the `records-repair` scope) | **The Neon test file's docstring cites a spec list that this repair removed.** The docstring says "constraint kinds listed at spec:48 (NOT NULL, FK, CHECK, unique)". The spec now has no such list, and spec :48 is the Keenable paragraph. The line number was already wrong on `origin/main`, where the Neon paragraph was :49. | `tests/test_db_constraints.py:20-22`; `grep -n CHECK docs/superpowers/specs/2026-11-14-receipts-design.md` exit 1; `git show origin/main:docs/superpowers/specs/2026-11-14-receipts-design.md` puts "Neon (Claude's call)" at :49 | Name it in the PR body. A later pass points the docstring at AGENTS.md section 4 or drops the reference. `tests/` is outside this repair's scope. |

Counts:
- 0 CRITICAL, 0 HIGH.
- 1 MEDIUM: finding 1, new, introduced by this repair, open and not accepted.
- 5 LOW: findings 2 to 6.
- The previous verdict's MEDIUM is **resolved** (check 3).

## Status of the previous verdict's findings

The previous verdict numbered its findings 1 to 9. Its LOWs 1 to 8 are its findings 2 to 9.

| Previous | What it was | Status on `66e6095` |
|---|---|---|
| Finding 1, MEDIUM | ADR-0008 did not record the `unique=True` sabotage substitution | **Resolved.** ADR-0008:63 records it, and both of its numbers reproduce exactly (check 3). It needs a source attribution (finding 5, LOW). |
| LOW 1 (finding 2) | `routes.py:14-15` docstring gap not deferred anywhere | **Resolved.** ADR-0008:64 names the file and lines and says why it is deferred: the file is outside the records scope. One word is inaccurate (finding 4, LOW). |
| LOW 2 (finding 3) | `users` NOT NULLs unproven on Neon while spec :50 said every constraint is proven | **Resolved.** Spec :50 no longer says "every", and it names the three NOT NULLs. It leaves out the `users` primary key (finding 3, LOW). |
| LOW 3 (finding 4) | Spec :50: `dev` branch and the old five-table list | **Table half resolved:** "Tables that exist today: `runs` and `users`" matches `schema.py:56` and `:65` and Neon (2 public tables, exactly `{runs, users}`). **`dev`-branch half replaced by an unsupported claim** (finding 1, MEDIUM). |
| LOWs 4 to 8 (findings 5 to 9) | Session docstring vs a naive `now`; `.strip()` untested; `dict[str, Any]` in `account_view`; merge-commit hygiene; red-first count | **Unchanged.** The repair diff touches no `src/` or `tests/` file. They stay for the PR body, with the counts updated below. |

## Checks

**1. Scope of the repair.**
- `git diff --name-only 3145d8f...66e6095 | sort` (exit 0) lists exactly 2 paths: `docs/adr/0008-google-sign-in.md` and `docs/superpowers/specs/2026-11-14-receipts-design.md`.
- `git diff --stat` shows 2 files, 3 insertions, 1 deletion. Both paths are the 2 of 2 in the `records-repair` scope (plan :294-297).
- One commit, `66e6095`, with trailer `Co-Authored-By: Claude Fable 5.1`.

**2. The task's exit command.** UNSET `bin/jig && grep -q matches_the_mapping docs/adr/0008-google-sign-in.md && ! grep -n 'user accounts' docs/superpowers/specs/2026-11-14-receipts-design.md` exits **0** (07:00:43 UTC). The jig table:

```
stack   class   result
------  ------  ------
python  format  ok
python  lint    ok
python  types   ok
python  tests   ok
```

4 of 4 rows `ok`.

**3. The previous MEDIUM, by behaviour.** ADR-0008:63 reads:

> **The `users.sub` uniqueness sabotage cannot turn the Neon duplicate-insert test red.** The brief's Verification 4h sabotage (remove `unique=True` from `UserRow.sub`) leaves `tests/test_db_constraints.py::test_duplicate_user_sub_is_rejected` green once the `users` table exists on Neon, because `users_sub_key` already exists there and `Base.metadata.create_all` never alters an existing table. The guard for that sabotage is `test_users_unique_on_neon_matches_the_mapping`, which reads the live constraint from the catalogue and compares it with the mapping; under the sabotage it fails 1 of 12 Neon constraint tests. On SQLite the same sabotage fails 1 of 13 tests in `tests/test_db_users.py`, `test_a_concurrent_first_sign_in_that_wins_the_insert_is_re_read`.

I removed `unique=True, ` from `src/receipts/db/schema.py:59`. `git diff -- src/` showed only that one-line change.

| Run | Command | Result | ADR says | Match |
|---|---|---|---|---|
| SQLite | UNSET `uv run pytest tests/test_db_users.py -q -rs` | exit 1, `1 failed, 12 passed`: 1 failed of 13, `test_a_concurrent_first_sign_in_that_wins_the_insert_is_re_read` (`AssertionError: assert User(id='user...) == User(id='user...)`) | 1 of 13, that test | yes |
| Neon (07:03:12 UTC) | `uv run pytest tests/test_db_constraints.py -v -m integration -rs` | exit 1, `1 failed, 11 passed`, 0 skipped: 1 failed of 12, `test_users_unique_on_neon_matches_the_mapping` (`AssertionError: assert set() == {'sub'}`). `test_duplicate_user_sub_is_rejected` **PASSED**. | 1 of 12; duplicate-insert test green | yes |

Revert:
- `git checkout -- src/` exits 0.
- `git diff --exit-code -- src/` exits 0.
- `schema.py:59` carries `unique=True` again.

Neon count queries, taken before the sabotage run (07:02:51 UTC) and after it (07:03:47 UTC). The two outputs are identical (`diff` exit 0).

| Query | Before | After | Expected |
|---|---|---|---|
| `users` total | 0 | 0 | 0 |
| `runs` where `id like 'constraint-test-%'` | 0 | 0 | 0 |
| `users` where `sub like 'fake-sub-%'` | 0 | 0 | 0 |
| `runs` where `user_id is not null` | 0 | 0 | 0 |
| `runs` total | 3 | 3 | 3 |
| public tables | 2, set equals `{runs, users}` | same | — |
| `users` unique constraints equal `[("users_sub_key", ["sub"])]` | True | True | — |
| `current_database() = 'main'` | False | False | — (used in finding 1) |

The ADR now states the true count, and it is the count the whole-PR judge reported. **The previous MEDIUM is resolved.**

**4. LOW 1.** ADR-0008:64 reads:

> **A docstring names less than its code covers (deferred).** The docstring at `src/receipts/auth/routes.py:14-15` describes the 503 `user_store` path as the row write only; the code also covers building the users store and running its schema. The file is outside the records scope, so the docstring is left for a later pass.

- It names the file and lines (`src/receipts/auth/routes.py:14-15`).
- It says why the fix is deferred: the file is outside the records scope.
- Its account of the code is right (`routes.py:281` → `:203-213`, inside `except SQLAlchemyError` at `:337`).
- One word is wrong: "write only", where the docstring says "read or written" (finding 4).

**5. Spec :50.** The paragraph now reads:

> **Neon (Claude's call):** One Neon database, `main`, for building and the demo. Settings rewrite `postgresql://` → `postgresql+psycopg://`; `pool_pre_ping=True` (Neon suspends idle compute). Portable SQLAlchemy 2 types so unit tests run on SQLite. Tables that exist today: `runs` and `users`. SQLite is for fast unit tests only. The Neon tests run against the live Neon database under the owner's 2026-11-16 ruling (additive changes only, test rows deleted), not a `dev` branch, and prove a constraint by inserting the row it exists to stop (AGENTS.md §4) for the `runs` NOT NULLs and primary key, `users.sub` UNIQUE, the `runs.user_id` foreign key, and the `claim_run` round trip. Not yet proven that way: the three `users` NOT NULLs (`sub`, `email`, `created_at`).

What each of the 12 Neon tests targets (`tests/test_db_constraints.py`, read in full):

| Line | Test | Targets | Rejected insert? |
|---|---|---|---|
| :140 | `test_duplicate_primary_key_is_rejected` | `runs` primary key, uniqueness | yes |
| :154 | `test_null_in_required_column_is_rejected[subject, rival, status, created_at, events]` (5 cases) | `runs` NOT NULL, 5 columns | yes, 5 |
| :161 | `test_null_id_is_rejected` | `runs` primary key, NOT NULL | yes |
| :176 | `test_duplicate_user_sub_is_rejected` | `users.sub` UNIQUE (SQLSTATE 23505) | yes |
| :192 | `test_users_unique_on_neon_matches_the_mapping` | catalogue vs mapping drift | no (catalogue read) |
| :203 | `test_run_user_id_naming_no_user_is_rejected` | `runs.user_id` foreign key (SQLSTATE 23503) | yes |
| :209 | `test_claim_run_round_trip_writes_user_id_on_neon` | `runs.user_id` column exists | no (valid row) |
| :232 | `test_create_schema_twice_is_idempotent_on_neon` | DDL idempotency, FK target, index name | no (catalogue read) |

9 of 12 are rejected-insert tests. 3 of 12 are not: the drift check, the round trip and the idempotency check. The `runs` NOT NULL columns in `schema.py:67-74` are `id`, `created_at`, `subject`, `rival`, `status` and `events`, and 6 of 6 have a rejection test.

| Spec :50 claim | Evidence on this head | Holds |
|---|---|---|
| "One Neon database, `main`, for building and the demo" | see finding 1 | **no** (finding 1, MEDIUM) |
| "Tables that exist today: `runs` and `users`" | `grep -n __tablename__ src/receipts/db/schema.py` hits `:56` users and `:65` runs (exit 0); Neon has 2 public tables, exactly `{runs, users}` | yes |
| "under the owner's 2026-11-16 ruling (additive changes only, test rows deleted)" | plan :323, owner 2026-11-16 01:06 UTC, answer (2): "may run against the live `DATABASE_URL` ... additive changes only ... test rows deleted, URL never printed". The `runs` tests ran on that database earlier under the coordinator's W1 acceptance (W1 plan :442); the present tense is accurate. | yes |
| "not a `dev` branch" | W1 plan :442; `l4-constraints-repair` verdict :26; gh41 plan :348; runbook :103-104 | yes |
| "`runs` NOT NULLs and primary key" by rejected insert | :140, :154-158, :161-170; 6 of 6 NOT NULL columns | yes |
| "`users.sub` UNIQUE" by rejected insert | :176-189 | yes |
| "the `runs.user_id` foreign key" by rejected insert | :203-206 | yes |
| "and the `claim_run` round trip" by rejected insert | :209-229, a valid row | **no** (finding 2, LOW) |
| "Not yet proven that way: the three `users` NOT NULLs" | `null()` only at :157 and :165, on `runs` | true but incomplete: the `users.id` primary key is also unproven (finding 3, LOW) |

**6. No regression in the whole PR.**
- **Paths and Forbidden.** `git diff --name-only origin/main...66e6095 | sort` lists 45 paths. A grep of those 45 for every `Forbidden:` pattern on brief :42 exits 1, so there are no hits. The patterns: `contracts.py`, `fakes/`, `conftest.py`, `fixtures/`, `harness/`, `verify/`, `packs/`, `seed_demo_runs.py`, `leak_gate/`, `bin/`, `.github/`, `Dockerfile`, `docs/adr/000[1237]-`, `docs/superpowers/plans/`, `.gitleaks.toml` and `.gitleaksignore`.
- **AGENTS.md.** The diff touches only the hunks at `@@ -104` and `@@ -107`, both below `## 9. Project overlay` at :89.
- **Whole unit suite.** UNSET `uv run pytest -q -m "not integration" -rs` exits **0**: `687 passed, 14 deselected`. That is 701 collected and **0 skipped** (`grep -c SKIPPED` prints 0).
- **Verification 7 greps.**
  - `grep -n 'user accounts'` on the spec exits 1.
  - `grep -n 'no accounts' AGENTS.md` exits 1.
  - `grep -n Google docs/adr/0004-approved-ai-vendors.md` exits 0, with hits at :31, :32, :41 and :42.
  - `ls docs/adr/0008-*.md` exits 0 and lists 1 file.
- **Leak gates.**
  - `gitleaks git --log-opts="3145d8f..66e6095" --redact --exit-code 1` exits 0: "1 commits scanned", "no leaks found".
  - `python3 -I scripts/leak_gate/check_tracked.py` exits 0: "scanned 203 files against 2 patterns".

## What the PR body must still carry

Everything listed under "What the PR body must contain" in `verdicts/2026-11-15-gh41-records-whole-pr.md` still applies, with these updates:
- **Commit totals now 65 commits, of which 9 are merges** (`git rev-list --count` and `--merges --count`, `origin/main..66e6095`). The trailer split is 50 `Claude Fable 5.1`, 9 `Claude Opus 5.5` and 6 none (the same six default-message merges).
- **Red-first count:** the grep gives 17 of 65, and 15 of 65 are true red-first subjects (the same 15 commits; the repair commit is records-only).
- **Carried LOWs** (the previous verdict's LOWs 4 to 8 = findings 5 to 9):
  - the session docstring vs a naive `now` (`session.py:12` against `:107-112`);
  - `.strip()` untested (`models.py:71`);
  - `dict[str, Any]` in `account_view` (`ui/app.py:179`, `:275`), accepted by the `ui` judge;
  - the merge-commit hygiene (counts above);
  - the red-first count (above).
- **New LOW from this verdict:** finding 6 (the `tests/test_db_constraints.py:20-22` reference to a removed spec list), plus any of findings 2 to 5 that the next repair does not fix.
- The owner's steps that are still open are unchanged.

## Verdict

0 HIGH. The previous MEDIUM is resolved, with both numbers reproduced on `66e6095`: Neon 1 failed of 12 (the drift check, with the duplicate-insert test green) and SQLite 1 failed of 13 (the concurrent-sign-in test). Neon counts are unchanged at 0, 0, 0, 0, 3.

The repair introduced one new MEDIUM (finding 1). The spec's first Neon sentence asserts a database count and the name `main`, and no record establishes either. The literal reading is contradicted by `current_database() = 'main'` being `False`. I do not accept it: the fix is one sentence inside the `records-repair` scope, and AGENTS.md section 0 (:9) requires an artifact for each claim. Repair attempt 2 of 3 should:
- narrow that sentence (finding 1);
- optionally fix findings 2 to 5 in the same two files.

A re-judge then needs only the spec :50 and ADR-0008:63-64 text re-checked, plus `bin/jig`.

VERDICT: FAIL
