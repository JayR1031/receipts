# Judge verdict: gh-41 `records-repair-2` (repair attempt 2 of 3, issue #41, Sign in with Google)

Blind re-judge in a fresh context. My runs took place 2026-11-16 from 07:12:46 to 07:18:34 UTC (`date -u`).

- **What was judged.** Worktree `.worktrees/gh41-records`, branch `jay/gh-41-records`, head `dd3c10a`. Its one parent is `66e6095` (`git rev-list --parents -n1 HEAD`). `origin/main` is `c5d0114`, which is also the merge base.
  - Repair diff: `git diff 66e6095...dd3c10a`.
  - Whole-PR diff: `git diff origin/main...dd3c10a`.
- **What I read.**
  - The previous verdicts `verdicts/2026-11-15-gh41-records-repair.md` and `verdicts/2026-11-15-gh41-records-whole-pr.md`.
  - `AGENTS.md` sections 0 to 8.
  - From the gh41 plan: the `records-repair` and `records-repair-2` blocks (:291-316) and "Approval and answers" (:334-336).
  - From the W1 plan, the main checkout's working copy: "Coordinator rulings 2026-11-15 01:11 UTC" (:387-391) and the `l4-repair` and `l4-constraints` rows (:441-442).
  - The brief's File scope (:29-42).
- **UNSET** below means `env -u VIRTUAL_ENV -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE`. The task's own exit command was run exactly as written, without the `VIRTUAL_ENV` unset.
- **What I did not run.** No Neon run, no sabotage, no model or Keenable calls and no live runs. The previous re-judge reproduced the numbers on `66e6095`, and the repair changes no `src/` or `tests/` file (`git diff --quiet 66e6095 dd3c10a -- tests/ src/` exits 0).
- **Method.** I captured exit codes with `$?` on output written to scratchpad files, never through a pipe. `bin/jig` wipes bytecode caches itself (`bin/jig:91-112`), and I wiped them before each direct pytest run. Nothing from the environment is printed here.
- **End state.**
  - `git status --porcelain` prints 0 lines.
  - `git diff --exit-code` exits 0, and so does `git diff --cached --exit-code`.
  - HEAD is still `dd3c10a`.
  - `git stash list` prints 0 lines, and I created no worktree or commit.

## Findings

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | LOW (new; the facts hold) | **The new citations in spec :50 and ADR-0008:63 point to text that no commit contains.** Spec :50 cites "(W1 plan, coordinator ruling 2026-11-15; owner's answer 2, 2026-11-16)". The W1 plan tracked at `dd3c10a` is identical to `origin/main`, and it has no coordinator ruling and no `l4-constraints` row. That text exists only in the main checkout's untracked working copy (:387-391, :442). The gh41 plan, which holds answer 2, is in no commit. ADR-0008:63 names the path `docs/superpowers/plans/verdicts/2026-11-15-gh41-records-repair.md`, and no commit has that path either. The brief forbids `docs/superpowers/plans/**`, so this PR could not publish these files. The claims themselves are supported by tracked files: runbook :103-104 says "`DATABASE_URL` in `~/.zshenv` is the deployed Neon database"; `verdicts/2026-11-15-l4-constraints.md:43` and `verdicts/2026-11-15-l4-constraints-repair.md:26` say the tests write to the `DATABASE_URL` demo database, not a `dev` branch, and the coordinator accepted it. There is a precedent: the earlier "owner's 2026-11-16 ruling" in spec :50 and ADR-0008:47 also cite the unpublished gh41 plan. | `git grep -n -e 'Coordinator rulings\|DATABASE_URL\|demo DB\|`dev`' -- docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md` on the worktree exits 1. `git diff --stat dd3c10a origin/main -- <W1 plan>` exits 0 with no output (identical). `git log --all -S'tests hit the demo DB not a'` finds no commit (exit 0, empty). `git log --all -S'Coordinator rulings 2026-11-15'` finds only `c5d0114` and `20fab2a`, where the string is a mention at `verdicts/2026-11-15-gh33-r2-body-claims.md:34`, and that line itself says "untracked in the main checkout". `git cat-file -e dd3c10a:docs/superpowers/plans/2026-11-15-gh41-google-sign-in.md` exits 128, and so does the same check on `dd3c10a:docs/superpowers/plans/verdicts/2026-11-15-gh41-records-repair.md`. `git log --all -- <both paths>` gives no commit. Brief :42 lists `docs/superpowers/plans/**` as Forbidden. | The PR body says that the cited plan text and verdict are not yet committed and will land with a records commit like `c5d0114` (#51). Alternatively, a later records pass cites the tracked sources (runbook :103-104, `l4-constraints` verdicts). |
| 2 | LOW (new) | **"The integration tests" in spec :50 is one test too broad.** Of the 14 `integration`-marked tests, 13 use the `DATABASE_URL` database: 12 in `test_db_constraints.py` and 1 in `test_db.py`. The 14th, `tests/test_integration_live.py`, uses a temporary SQLite file, and its docstring says "never the Neon database". | UNSET `uv run pytest --collect-only -q -m integration` exits 0 with `14/701 tests collected`: 12 `test_db_constraints.py`, 1 `test_db.py`, 1 `test_integration_live.py`. `tests/test_integration_live.py:2`, `:52`; `tests/test_db_constraints.py:67`; `tests/test_db.py:212` | "The Neon integration tests (13 of the 14 `integration`-marked tests) and the deployed app use the same Neon database..." |
| 3 | LOW (new, wording) | **Spec :50 says "a tenth test writes one valid row through `claim_run`".** `claim_run` writes no row: it sets `user_id` on a row that already exists, and its docstring says it "creates none". The test inserts the `runs` row itself and a `users` row through `get_or_create`, then claims the run. The rest of the clause holds: the test reads `user_id` back and rejects nothing. | `tests/test_db_constraints.py:215` (`get_or_create`), `:217` (`insert(RUNS)`), `:218` (`claim_run`), `:220-221` (read back); `src/receipts/db/repo.py:254-256` ("creates none"), `:262-267` (`row.user_id = user_id`) | "...a tenth test inserts one valid run, claims it with `claim_run` and reads `user_id` back, which shows the column exists but rejects nothing." |
| 4 | LOW (new to the gh41 verdicts; already present on `origin/main` at :97) | **Spec :98, under "## Verification" (:94), contradicts the new spec :50 twice.** It says "Neon round-trip on `dev`; each schema constraint rejecting its bad row on `dev`". Spec :50 now says "no `dev` branch is in use" and that 4 of the 5 `users` constraints are not yet proven by a rejected insert. The previous re-judge's search for finding 1 did not match this line, and no gh41 verdict names it. Related, outside the PR's paths: `tests/test_db.py:211` says "Needs `DATABASE_URL` (Neon `dev` branch)". That is the docstring the `l4-repair` verdict carried (W1 plan :441). | `docs/superpowers/specs/2026-11-14-receipts-design.md:98` against `:50`. `git show origin/main:<spec> \| grep -n 'Neon round-trip on `dev`'` hits :97 (exit 0). `grep -ln 'round-trip on `dev`\|:98\b' verdicts/2026-11-15-gh41-*.md` exits 1. `git grep -n -E '`dev`\|dev branch\|dev-branch' dd3c10a -- ':!docs/superpowers/plans/verdicts/'` hits spec :50, :67, :98 and `tests/test_db.py:211` (exit 0). `tests/test_db.py` is not among the 45 PR paths (`grep -c` prints 0). The `records-repair-2` title (plan :306) names only the sentences at :50. | The PR body names spec :98 (and `tests/test_db.py:211`) as known drift. A later records pass rewrites :98 to the `DATABASE_URL` database and the constraints actually proven, which spec :50 lists. |
| 5 | LOW (carried; the previous re-judge's finding 6) | **The Neon test file's docstring still cites a spec list that no longer exists.** It points to "spec:48 (NOT NULL, FK, CHECK, unique)". Neither the repair nor this PR changes it. | `tests/test_db_constraints.py:20-22`; `git diff --quiet 66e6095 dd3c10a -- tests/ src/` exits 0 | PR body; a later pass. |

Counts:
- 0 CRITICAL, 0 HIGH, 0 MEDIUM.
- 5 LOW: findings 1 to 4 are new, and finding 5 is carried.

## Status of the previous re-judge's findings (`verdicts/2026-11-15-gh41-records-repair.md`)

| Previous | What it was | Status on `dd3c10a` |
|---|---|---|
| Finding 1, MEDIUM | Spec :50 asserted "One Neon database, `main`", a count and a name that no record supports | **Resolved** (check 3). New wording issues are findings 1 and 2 here, both LOW. |
| LOW 2 | The `claim_run` round trip was listed as proven by a rejected insert | **Resolved.** It is now described as column evidence that "rejects nothing", and "9 of the 12" is right. One wording slip remains (finding 3 here, LOW). |
| LOW 3 | The `users.id` primary key was missing from the not-yet-proven list | **Resolved.** "the `users.id` primary key and the three `users` NOT NULLs ..., 4 of the 5 `users` constraints" matches the mapping (check 4). |
| LOW 4 | ADR-0008:64 said "write only" | **Resolved.** It now says "row read or write only", which matches `routes.py:14` ("read or written"). |
| LOW 5 | ADR-0008:63 gave no source run | **Resolved.** The source sentence names the file and both counts, and the file contains them (check 5). The path is not yet in any commit (finding 1 here, LOW). |
| LOW 6 | The `test_db_constraints.py:20-22` docstring | **Unchanged.** It is outside scope (finding 5 here). |

## Checks

**1. Scope.**
- `git diff --name-only 66e6095...dd3c10a | sort` exits 0 and lists exactly 2 paths: `docs/adr/0008-google-sign-in.md` and `docs/superpowers/specs/2026-11-14-receipts-design.md`. Those are 2 of 2 in the `records-repair-2` scope (plan :307-310).
- `git diff -U0 66e6095...dd3c10a | grep '^@@'` shows 2 hunks: `@@ -63,2 +63,2 @@` in ADR-0008 and `@@ -50 +50 @@` in the spec.
- `--stat`: 2 files, 3 insertions, 3 deletions.
- One commit, `dd3c10a`, with trailer `Co-Authored-By: Claude Fable 5.1`.
- `gitleaks git --log-opts="66e6095..dd3c10a" --redact --exit-code 1` exits 0: "1 commits scanned", "no leaks found".
- `python3 -I scripts/leak_gate/check_tracked.py` exits 0: "scanned 203 files against 2 patterns".

**2. The task's exit command.**
- `env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && grep -q matches_the_mapping docs/adr/0008-google-sign-in.md && ! grep -n 'user accounts' <spec> && ! grep -n 'One Neon database' <spec>` exits **0** (07:13:01 to 07:13:22 UTC).
- The jig printed only its table (6 lines):

```
stack   class   result
------  ------  ------
python  format  ok
python  lint    ok
python  types   ok
python  tests   ok
```

That is 4 of 4 rows `ok`.

**3. Finding 1, the MEDIUM: resolved.** The new opening of spec :50 reads:

> The integration tests and the deployed app use the same Neon database, the one `DATABASE_URL` names; no `dev` branch is in use (W1 plan, coordinator ruling 2026-11-15; owner's answer 2, 2026-11-16).

- **No count and no name.**
  - `grep -n 'One Neon database'` on the spec exits 1.
  - On line 50, a grep for `` `main` ``, "one database" or a number followed by "database" counts 0 (exit 1).
  - "the same Neon database, the one `DATABASE_URL` names" identifies the database by its setting, not by a count or a name.
- **The citations exist and say this.** I read them in the main checkout's working copies; finding 1 explains why they are not in any commit.
  - W1 plan :387: "## Coordinator rulings 2026-11-15 01:11 UTC".
  - W1 plan :391: "**L4 constraint tests** may run against `DATABASE_URL` as `@pytest.mark.integration`".
  - W1 plan :442 (`l4-constraints` row): "tests hit the demo DB not a `dev` branch — accepted by the coordinator".
  - gh41 plan :334: "Approval and answers (owner, 2026-11-16 01:06 UTC ...)".
  - gh41 plan :336, answer (2): "the `db` integration test may run against the live `DATABASE_URL` from `~/.zshenv`".
  - The dates in the spec (2026-11-15, 2026-11-16) match those headings.
- **Tracked support.**
  - Runbook :103-104 says the `DATABASE_URL` in `~/.zshenv` is the deployed Neon database, so the tests and the deployed app share it.
  - `verdicts/2026-11-15-l4-constraints.md:43` and `verdicts/2026-11-15-l4-constraints-repair.md:26` say the tests write to the `DATABASE_URL` demo database, "not the Neon `dev` branch", and that the coordinator accepted it.
- **The sentence asserts only that:** a shared database, and no `dev` branch in use. One set is too broad (finding 2, LOW).
- **Spec :67 is untouched and acceptable.**
  - The line is byte-identical to `66e6095` (`cmp` exits 0). It is :66 on `origin/main`, shifted by the PR's +1 at :18.
  - It sits under "## Execution steps after approval" (:65). It is the owner's numbered setup to-do from 2026-11-14; the next step is marked "✅ Done 2026-11-14".
  - It tells the owner to get keys, including "Neon with a `dev` branch". It says nothing about what the tests or the app use now, so it does not contradict :50.
  - Spec :98 does contradict :50 (finding 4).

**4. LOWs 2 and 3: resolved.** The constraint passage in spec :50 now reads:

> ...and prove a constraint by inserting the row it exists to stop (AGENTS.md §4) for the `runs` NOT NULLs and primary key, `users.sub` UNIQUE and the `runs.user_id` foreign key (9 of the 12 Neon tests); a tenth test writes one valid row through `claim_run` and reads `user_id` back, which shows the column exists but rejects nothing. Not yet proven by a rejected insert: the `users.id` primary key and the three `users` NOT NULLs (`sub`, `email`, `created_at`), 4 of the 5 `users` constraints.

- **The 12 tests.** UNSET `uv run pytest tests/test_db_constraints.py --collect-only -q -m integration` exits 0: "12 tests collected".
- **9 of 12 are rejected-insert tests.**

| Line | Test | Count |
|---|---|---|
| :140 | duplicate `runs` primary key | 1 |
| :154-158 | `runs` NULL in `subject`, `rival`, `status`, `created_at`, `events` | 5 |
| :161 | NULL `runs.id` | 1 |
| :176 | duplicate `users.sub`, SQLSTATE 23505 | 1 |
| :203 | `runs.user_id` naming no user, SQLSTATE 23503 | 1 |

- **The other 3 of 12 reject nothing.** They are the drift check (:192), the `claim_run` round trip (:209) and the idempotency check (:232).
- **Every `runs` NOT NULL column is covered.** The `runs` NOT NULL columns in `src/receipts/db/schema.py:67-74` are `id`, `created_at`, `subject`, `rival`, `status` and `events`; 6 of 6 have a rejection test.
- **The `users` constraints.** `src/receipts/db/schema.py:58-61` gives `users` 5 constraints: the `id` primary key, `sub` UNIQUE, and NOT NULL on `sub`, `email` and `created_at`.
  - 1 of 5 is proven by a rejected insert: `sub` UNIQUE (:176).
  - 4 of 5 are not. The two `insert(USERS)` calls (:181, :183) use two different ids, and `null()` appears only on `RUNS` (:157, :165).
  - The spec's "4 of the 5" is right.
- **The round trip.** "rejects nothing" is right: there is a valid insert at :217 and positive asserts at :221-223. "writes one valid row through `claim_run`" is not (finding 3).

**5. LOWs 4 and 5: resolved.**
- **ADR-0008:64** now reads "describes the 503 `user_store` path as the row read or write only". `src/receipts/auth/routes.py:14` says "A database error while that row is read or written".
- **ADR-0008:63** now ends: "Both counts were reproduced by the whole-PR re-judge on 2026-11-16 (`docs/superpowers/plans/verdicts/2026-11-15-gh41-records-repair.md`): SQLite exit 1, 1 failed of 13; Neon exit 1, 1 failed of 12, with `test_duplicate_user_sub_is_rejected` still passing."
- **The cited file exists** in the main checkout and contains both counts:
  - :74, SQLite: "exit 1, `1 failed, 12 passed`: 1 failed of 13".
  - :75, Neon: "exit 1, `1 failed, 11 passed`, 0 skipped: 1 failed of 12", with `test_duplicate_user_sub_is_rejected` **PASSED**.
  - :166 repeats both.
  - Its runs were on 2026-11-16, 07:00-07:06 UTC.
- The file is not in any commit (finding 1).

**6. The whole PR is otherwise unchanged.**
- **Paths and Forbidden.** `git diff --name-only origin/main...dd3c10a | sort` lists 45 paths (exit 0). Grepping those 45 for every `Forbidden:` pattern on brief :42 exits 1, so 0 of 45 match. The patterns: `contracts.py`, `fakes/`, `tests/conftest.py`, `tests/fixtures/`, `harness/`, `verify/`, `packs/`, `seed_demo_runs.py`, `leak_gate/`, `bin/`, `.github/`, `Dockerfile`, `docs/adr/000[1237]-`, `docs/superpowers/plans/`, `.gitleaks.toml` and `.gitleaksignore`.
- **AGENTS.md.** It changes only at `@@ -104` and `@@ -107`, both below `## 9. Project overlay` at :89.
- **Unit suite.** UNSET `uv run pytest -q -m "not integration" -rs` exits **0**: `687 passed, 14 deselected`. That is 701 collected and **0 skipped**: `grep -c SKIPPED` prints 0 (exit 1). There is no skip to name.
- **Verification 7 greps.**
  - `grep -n 'user accounts'` on the spec exits 1.
  - `grep -n 'no accounts' AGENTS.md` exits 1.
  - `grep -n Google docs/adr/0004-approved-ai-vendors.md` exits 0, with hits at :31, :32, :41 and :42.
  - `ls docs/adr/0008-*.md` exits 0 and lists 1 file.

## What the PR body must still carry

1. **Everything under "What the PR body must contain"** in `verdicts/2026-11-15-gh41-records-whole-pr.md` (its items 1 to 6), with these counts updated for `dd3c10a`:
   - **66 commits, of which 9 are merges.** Sources: `git rev-list --count` and `--merges --count`, `origin/main..dd3c10a`.
   - **Trailer split:** 51 `Claude Fable 5.1`, 9 `Claude Opus 5.5` and 6 none, of 66. The 6 are the same six default-message merges: `23d2492`, `bdbf418`, `7f72a15`, `9a942a1`, `5b94add` and `fd2f166`.
   - **Red-first count:** the subject grep `git log --oneline origin/main..dd3c10a | grep -ci red` prints 17 of 66. The true count is 15 of 66; the two repair commits are records-only, and neither subject matches.
2. **The whole-PR verdict's LOWs 4 to 8 (its findings 5 to 9), still open:**
   - the session docstring against a naive `now` (`src/receipts/auth/session.py:12` against `:107-112`);
   - the untested `.strip()` (`src/receipts/auth/models.py:71`);
   - `dict[str, Any]` in `account_view` (`src/receipts/ui/app.py:179`, `:275`), accepted by the `ui` judge;
   - merge-commit hygiene (counts above);
   - the red-first count (above).
3. **The whole-PR verdict's findings 2 to 4 are now in records** and need only a pointer:
   - the `routes.py:14-15` docstring is deferred at ADR-0008:64;
   - the unproven `users` constraints are listed at spec :50;
   - the stale `dev`/table text at spec :50 is rewritten.
4. **From this verdict:**
   - finding 1: the cited plan text and verdict are not yet in any commit;
   - finding 4: spec :98 and `tests/test_db.py:211` still say `dev`;
   - finding 5: the `tests/test_db_constraints.py:20-22` docstring;
   - findings 2 and 3 as known wording, unless a later records pass fixes them.
5. **The owner's open steps are unchanged:**
   - Verification 6, the local browser sign-in;
   - the post-deploy acceptance list (runbook :161-173);
   - the Testing-mode / publish decision.

## Verdict

**Finding 1 (MEDIUM) is resolved.** Spec :50 no longer asserts a count or a name. It states a shared `DATABASE_URL` database and no `dev` branch in use, and the cited plan passages say exactly that. **LOWs 2 to 5 are resolved.** 9 of 12 rejected-insert tests and 4 of 5 `users` constraints unproven both check out against the test file and the mapping, ADR-0008:64 matches the docstring, and ADR-0008:63's cited file holds both counts.

Results on `dd3c10a`:
- 0 CRITICAL, 0 HIGH, 0 MEDIUM.
- 5 LOW: 4 new, 1 carried. All are wording or records hygiene, for the PR body or a later records pass.
- The exit command exits 0, and the jig is 4 of 4 `ok`.
- Unit suite: 687 passed, 14 deselected, 0 skipped of 701.
- Scope: 2 of 2 paths, 2 hunks.
- Whole PR: 45 paths, 0 Forbidden.

VERDICT: PASS
