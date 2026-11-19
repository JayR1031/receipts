# Re-judge verdict: `wiring-repair` (GitHub issue #41, Sign in with Google), head `e5435b7`: PASS

Blind re-judge in a fresh context, after repair attempt 1 of 3. Clock read with `date -u`: 2026-11-16T06:20Z. Worktree `.worktrees/gh41-wiring`, branch `jay/gh-41-wiring`, head `e5435b7`.

Diffs:
- Whole task: `git diff 2c13cc5...e5435b7`, 7 files, +1287 / -39.
- Repair only: `git diff 23d2492..e5435b7`, 3 files, +226 / -27.

What I read:
- the previous verdict, in full;
- AGENTS.md sections 0 to 5;
- the plan's `wiring` and `wiring-repair` blocks, the `wiring` dispatch note and the Coordinator rulings;
- the brief's Constraints ("Rule Zero on counts", "Start rule", "Modes") and its Assumptions.

How I ran things: every unit command ran with the seven live names unset. No network, no model or Keenable call, no live run, and no secret printed. Probes used invented values and SQLite files in the session scratchpad, not in the worktree.

## Previous findings: status

| Previous | Status | Evidence |
|---|---|---|
| HIGH 1 (a deleted user's cookie passes the start rule) | **Resolved** | `src/receipts/api/wiring.py:489-495` (`_row`), `:502` (`visitor = user if await self._row(repo, user) is not None else None`), `:503` and `:508-509` (`_decide` and `claim_run` take `visitor`). 4 of 4 sabotages red. The previous judge's probe now starts 0 of 4 runs (below). |
| MEDIUM 2 (the half-configured start path the UI uses had no test) | **Resolved** | Tests at `tests/test_wiring.py:1187`, `:1197`, `:1213`, `:1239`. `_ui_run` (`:469-485`) now drives `gated_run_stream(app.state.run_service, app.state.gate, None, ...)`. Both sabotages the previous judge saw stay green are now red: 5 of 687 failed for each. |
| MEDIUM 3 (the merged tree turned `test_openapi_export` red) | **Resolved** | Export, then `git diff --exit-code docs/api/openapi.json`: exit 0. `git merge-tree --write-tree jay/gh-41-google-sign-in e5435b7`: exit 0, tree `9b25930`, which equals the tree of `e5435b7`. `git merge-base --is-ancestor 2c13cc5 e5435b7`: exit 0, so this is a fast-forward candidate. Red before the regeneration: the merge commit's `openapi.json` against the merged code gave 1 failed, 1 passed, exit 1 (`test_committed_document_matches_a_fresh_export`). |
| LOW 4 (two pools) | **Resolved** (docstring) | See check 7 below. |
| LOW 5 (`0 of 0`) | **Resolved** | See check 6 below. |
| LOW 6 (dead patches) | **Resolved** | See check 7 below. |
| LOW 7, LOW 8 | **Carried to `records`**, unchanged | Rows 5 and 6 below. |

## Findings

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | LOW | **History and `GET /api/runs` disagree with `start` and `account` for a session whose `users` row is gone.** `start` and `account` read the row and treat a missing one as signed out. `history`, and the API list behind the same `history_for`, list the cookie's user id instead. As a result, runs that person starts with the passcode never appear in their History panel, while their account line counts those same runs. **No other person's data is exposed.** `runs.user_id` references `users.id` with no `ON DELETE`, so on an FK-enforcing store a `users` row with claimed runs cannot be deleted. Once the runs are deleted first, the stale id lists 0 rows. Ids are `user-` plus a `uuid4` and are never reused. The exposure the implementer raised is therefore not real on Neon. What is left is the inconsistency. Not in the repair's assignment; new. | `src/receipts/api/wiring.py:378-384` (`history_for`) and `:512-513` (`history`), against `:502` (`start`) and `:520` (`account`); `src/receipts/api/routes.py:112-113`; the UI reads History through `gate.history(identify(...))` at `src/receipts/ui/app.py:192`. Probe (`create_app()`, live service on a SQLite file with `PRAGMA foreign_keys = 1`, `RUNS_PER_USER_PER_DAY=2`, a session for `user-deleted-0001`, right passcode, 4 attempts; exit 0): 4 of 4 started, 0 claimed for the ghost, 4 counted as signed-out, `account(ghost)` used=4 limit=20, `history(ghost)` 0 rows, `history(None)` 4 rows. FK probe on the same kind of store (exit 0): deleting a `users` row with a claimed run raised `IntegrityError`; after deleting the runs and then the user, `list_runs_for(stale id)` returned 0 rows. Schema: `src/receipts/db/schema.py:75-77`, `src/receipts/db/repo.py:76`, `src/receipts/db/users.py:34`. | Let `LiveGate.history` use `_row` (missing row means `history_for(service, None)`), and have `GET /api/runs` do the same. Or record the choice in ADR-0008 (`records`). |
| 2 | LOW | **Half-configured with all four sign-in settings set (`ANTHROPIC_API_KEY` missing): sign-in works at `/auth/*`, but the Gate reads every session as signed out.** `/auth/login` answers 302 and `/auth/me` answers 200 for a valid session. Meanwhile `account(session)` shows no email and `sign_in_available=False`, and `start(session, "")` is refused with "a valid passcode is required". **Rule Zero is not violated:** the line shows `0 of 20`, and those are exactly the inputs `may_start` gets here (`_count_today(None, ...)` returns 0 with no repo, and the cap is `signed_out_runs_per_day`). **The brief's "Modes" bullet is not violated:** it only requires hiding the link when one of the four settings is missing. "Everything else works exactly as today" still holds: a passcode run is a demo replay. Treating the session as signed out fails closed and matches `start`. | `src/receipts/api/wiring.py:460-470` (`_demo_account`), `:493-494` (no repo means no row), `:518-519`. Probe (four sign-in settings plus `DEMO_PASSCODE` and `KEENABLE_API_KEY`, SQLite `DATABASE_URL`, an existing synthetic user; exit 0): `/auth/login` 302, `/auth/me` 200, `account(session)` email=None used=0 limit=20 sign_in_available=False, `start(session, "")` `PermissionError: a valid passcode is required`. | Record it in ADR-0008 or the PR body (`records`). No code change needed. |
| 3 | LOW | **One claim in the implementer's report is broader than the evidence.** The report says "Red: 4 failed `DID NOT RAISE PermissionError`". Reproduced, 3 of the 4 failures are `DID NOT RAISE PermissionError`. The fourth, `test_a_session_whose_user_row_is_gone_starts_an_unclaimed_signed_out_run`, fails on `AssertionError` because the claims list holds `('run-…', 'user-deleted-0001')`. The commit message itself is accurate: it says "e.g.". | Run with `wiring.py` and `test_wiring.py` at `4acbbb9` put in the working tree, then restored: exit 1, `4 failed, 86 passed`. Restore `git diff --exit-code` exit 0. | State it as 3 + 1 in the PR body. |
| 4 | LOW | **Merge commit hygiene.** `23d2492` carries git's default message ("Merge branch 'jay/gh-41-google-sign-in' into jay/gh-41-wiring"), names no finding, and has no trailer. Its tree is exactly git's automatic merge (no hand edits). | `git show -s 23d2492`. `git merge-tree --write-tree 6df1b7f 2c13cc5`: exit 0, tree `eca081c`, which equals `23d2492^{tree}`. | Note it in the PR body: it merged the integration head for MEDIUM 3. No rewrite (rebases are forbidden). |
| 5 | LOW (carried to `records`) | Previous LOW 7: the docstring cites ADR-0008 for the per-process identity provider, and ADR-0008 does not record that choice yet. | `src/receipts/api/wiring.py:63-68`. `grep -n -i "per process\|key cache\|per request" docs/adr/0008-google-sign-in.md` matches only `:27`, which is unrelated. | `records`. |
| 6 | LOW (carried to `records`) | Previous LOW 8: the `Gate` docstring still says a missing key raises `MissingSettingError`, but the live Gate raises `PermissionError("KEENABLE_API_KEY is not set")`. | `src/receipts/auth/gate.py:34-35`; `src/receipts/api/wiring.py:430-435`. | `records`. |

No HIGH and no MEDIUM findings at this head.

## Checks

1. **Scope.**
   - `git diff --name-only 2c13cc5...e5435b7 | sort` lists 7 paths, all in the `wiring` scope: `docs/api/openapi.json`, `src/receipts/api/{app,models,routes,wiring}.py`, `tests/test_api_runs.py`, `tests/test_wiring.py`.
   - `git diff --name-only 23d2492..e5435b7 | sort` lists the 3 repair files: `docs/api/openapi.json`, `src/receipts/api/wiring.py`, `tests/test_wiring.py`.
   - `git diff 2c13cc5...e5435b7 -- src/receipts/auth src/receipts/ui src/receipts/db src/receipts/harness scripts tests/conftest.py src/receipts/contracts.py src/receipts/fakes` is 0 bytes; `--quiet` exit 0.
   - Each repair commit's `--stat`: `10d2ba7` `openapi.json` only; `0337ca1`, `4acbbb9` and `05d04ed` tests only; `5908019` and `e5435b7` `wiring.py` only.
2. **Exit command** (6 `&&` clauses), each run separately from the worktree root:
   - `bin/jig` exit 0, 4 of 4 rows `ok`;
   - the four-file pytest exit 0, 148 passed;
   - `export_openapi.py` exit 0;
   - `git diff --exit-code docs/api/openapi.json` exit 0;
   - `env -i` boot exit 0;
   - `! grep -rn auth_dependency src/` exit 0.

   The whole string, run as one `bash -c`: exit 0.

   Other gates:
   - Whole suite `pytest -q -m "not integration" -rs`: exit 0, `687 passed, 14 deselected`, 0 skipped (0 `SKIPPED` lines).
   - `uv run pyright src`: exit 0, `0 errors, 0 warnings, 0 informations`.
   - `grep -rn "type: ignore" src/ tests/`: exit 1 (no hits).
   - Added lines in the repair diff: no `Any`, no `dict[`, no `get_secret_value`, no log call in `src/`.

   Per file, each run alone: `test_wiring.py` 92 of 92, `test_ui_app.py` 29 of 29, `test_api_runs.py` 19 of 19, `test_openapi_export.py` 2 of 2, `test_settings.py` 8 of 8, `test_api.py` 5 of 5.

   New test ids in `test_wiring.py`: 11, so 81 + 11 = 92.
   - 3 ghost tests (`:871`, `:884`, `:895`);
   - 3 parametrized refusals (`:1187`);
   - `:1197`, `:1213` and `:1239`;
   - 2 parametrized LOW 5 cases (`:1257`).

   Plus 2 renames (`:1058`, `:1075`).
3. **HIGH 1, sabotage on `tests/test_wiring.py`.** Each sabotage was edited, run, restored, then `git diff --exit-code` exit 0.
   - (a) `visitor = user`: exit 1, 4 of 92 failed:
     - `test_a_session_whose_user_row_is_gone_is_signed_out_and_needs_the_passcode`
     - `..._starts_an_unclaimed_signed_out_run`
     - `..._meets_the_signed_out_cap`
     - `test_half_configured_a_session_is_signed_out_and_needs_the_passcode`
   - (b) `visitor = None` (shows the check is not over-broad): exit 1, 6 of 92 failed:
     - `test_signed_in_start_needs_no_passcode_and_claims_the_run`
     - `test_signed_in_at_the_limit_is_refused_and_starts_nothing`
     - `test_runs_before_midnight_utc_do_not_count_today`
     - `test_each_count_reaches_its_own_may_start_slot[signed-in-at-limit]`
     - `test_each_count_reaches_its_own_may_start_slot[signed-in-under]`
     - `test_a_missing_keenable_key_is_a_permission_error_naming_it`
   - (c) row read, but `_decide(..., user, ...)`: exit 1, 3 of 92 failed:
     - `..._needs_the_passcode`
     - `..._meets_the_signed_out_cap`
     - `test_half_configured_a_session_is_signed_out_and_needs_the_passcode`
   - (d) row read, but `claim_run` for `user`: exit 1, 1 of 92 failed:
     - `..._starts_an_unclaimed_signed_out_run` (the spy at `:853-868` records the claim).

   **The previous judge's probe, re-run on an FK-enforcing SQLite file** (`PRAGMA foreign_keys = 1`, `RUNS_PER_USER_PER_DAY=2`, blank passcode, a session for `user-deleted-0001`, 4 attempts; exit 0): **0 of 4 started**. All 4 were `PermissionError: a valid passcode is required`, with 0 `IntegrityError`, 0 rows in `runs` and 0 counted. The previous result was 4 of 4 started. With the right passcode: 4 of 4 started as signed-out, 0 claimed, 0 `IntegrityError`.

   Red commit `4acbbb9` reproduced (see finding 3). Green commit `5908019`: 90 of 90. The slot test now inserts the users row for its signed-in cases (`:962`); synthetic values only (`fake-sub-…`, `slot@example.com`).
4. **MEDIUM 2.**
   - Sabotage (i), refuse every signed-out start with no live repo (message "a valid passcode is required", the harder variant), whole suite: exit 1, **5 of 687 failed**:
     - `test_partial_config_ui_run_carries_the_demo_names_not_the_users`
     - `test_half_configured_gate_checks_the_passcode_before_the_key`
     - `test_half_configured_gate_replays_the_demo_with_the_passcode_uncounted_and_unclaimed`
     - `test_half_configured_a_session_is_signed_out_and_needs_the_passcode`
     - `test_demo_account_line_is_0_of_the_signed_out_cap_signed_in_or_out[half-configured]`
   - Sabotage (ii), drop `not passcode_configured(settings) and` at `:499`, whole suite: exit 1, **5 of 687 failed**:
     - `test_half_configured_gate_refuses_a_wrong_or_blank_passcode_and_starts_nothing[wrong|blank|whitespace]`
     - `..._checks_the_passcode_before_the_key`
     - `test_half_configured_a_session_is_signed_out_and_needs_the_passcode`
   - The implementer's own counts, reproduced on the `0337ca1` tree: (i) 3 of 86, (ii) 4 of 86.
   - Demo count 1 (`_count_today` returns 1 with no repo), whole suite: exit 1, 1 of 687 failed (`..._replays_the_demo_..._uncounted_and_unclaimed`).
   - `_ui_run` (`:469-485`) calls `gated_run_stream(app.state.run_service, app.state.gate, None, ...)`. That matches the signature at `src/receipts/ui/app.py:129-137`, and its docstring now says the starter is unused. `test_ui_app.py`: 29 of 29.
   - The `run_starter` path keeps its own tests (`tests/test_wiring.py:529`, `:612`, `:623`).

   **The red-first evidence meets AGENTS.md section 4 for these tests.** They pin behaviour that already existed: `0337ca1` is green, 86 of 86, and `git diff 23d2492 0337ca1 -- src/` is empty. Section 4's TDD bullet has no code to implement here. Its sabotage bullet ("inject the defect, confirm red, remove it, confirm green") is the guard that applies. The commit message of `0337ca1` records both sabotages with their counts. Both reproduce, and the tests from `0337ca1` were not changed afterwards: the only lines removed from the test file after that commit belong to the renamed demo-history test, in red commit `05d04ed`.
5. **MEDIUM 3.** See the status table. The only change in `openapi.json` is one line at `:646`, the `/auth/callback` 503 description.
6. **LOW 5 (Rule Zero).**
   - `_demo_account(settings)` (`wiring.py:460-470`) returns used 0, limit `signed_out_runs_per_day`, signed out.
   - `test_demo_account_line_is_0_of_the_signed_out_cap_signed_in_or_out[local-demo|half-configured]` checks `account(None)` and `account(session)` against `0 of 7`.
   - Red commit `05d04ed`: 3 of 92 failed, reproduced.
   - Sabotage `runs_limit=0`: 3 of 687 failed. Sabotage hard-coded `20`: 2 of 687 failed.
   - `grep -rn '0 of 0' src/ tests/` hits only docstrings (`wiring.py:463`, `tests/test_wiring.py:1079`, `:1261`). `grep -rn "runs_limit=0" src/ tests/` exit 1. No code path builds `0 of 0`.
   - With all four sign-in settings set and a live setting missing, the sign-in link stays hidden: graded in finding 2 (LOW; neither Rule Zero nor "Modes" is violated).
7. **LOW 4 and LOW 6.**
   - LOW 4: `wiring.py:56-61` now reads "When a sign-in reaches the users store before the live service exists (`/auth/callback` or `/auth/me` is the first request to need it), `receipts.auth.routes.get_user_repo` builds a `SqlUserRepo` on its own engine, and building the live repo later keeps that one: the process then holds two pools, one for users and one for runs, until it restarts." That matches the code: `src/receipts/auth/routes.py:203-213` and `wiring.py:282`, `:286-293`. Probe (`get_user_repo` first, then `resolve_run_service`; exit 0): `user_repo kept: True`, `same engine as run repo: False`. Code unchanged, with the reason given; that matches the previous verdict's second fix option.
   - LOW 6: the `forbidden` patches are gone. The test is renamed `test_local_demo_starts_without_a_passcode_or_a_key_signed_in_or_out` (`:1058`), and its docstring says what it proves. The only `"claim_run"` `setattr` left is the instance spy at `:867`.
8. **The implementer's new risk** (a deleted user's cookie lists runs). Graded in finding 1. A third party's data cannot be exposed on Neon. On SQLite, which is local-only and does not enforce FKs by default, the leftover runs would be the cookie holder's own. What remains is the History inconsistency, LOW.
9. **Merge commit.** Finding 4 (LOW).
10. **Cleanliness.** After every sabotage and reproduction, the restore's `git diff --exit-code` was 0. At the finish: `git status --porcelain` printed 0 lines (exit 0), `git diff --exit-code` exit 0, and `git status --porcelain --ignored` shows nothing outside the venv and caches.

## Sabotages and reproductions

| Id | Sabotage (in `src/receipts/api/wiring.py`, reverted) | Tests | Result |
|---|---|---|---|
| a | `visitor = user` (skip the row check) | `test_wiring.py` | red, 4 of 92 |
| b | `visitor = None` (every session signed out) | `test_wiring.py` | red, 6 of 92 |
| c | row read, deleted user still passed to `_decide` | `test_wiring.py` | red, 3 of 92 |
| d | row read, `claim_run` still for `user` | `test_wiring.py` | red, 1 of 92 |
| i | refuse every signed-out start with no live repo | whole suite | red, 5 of 687 |
| ii | demo skips a configured passcode | whole suite | red, 5 of 687 |
| n | demo count 1 | whole suite | red, 1 of 687 |
| l5a | `_demo_account` `runs_limit=0` | whole suite | red, 3 of 687 |
| l5b | `_demo_account` `runs_limit=20` | whole suite | red, 2 of 687 |
| i@0337ca1 / ii@0337ca1 | (i) and (ii) on the `0337ca1` tree | `test_wiring.py` | red, 3 of 86 / 4 of 86 |

Sabotages at head: 9 of 9 red, 0 green. On `0337ca1`: 2 of 2 red.

Commit reproductions:
- `0337ca1`: 86 of 86 green.
- `4acbbb9`: 4 failed, 86 passed.
- `5908019`: 90 of 90 green.
- `05d04ed`: 3 failed, 89 passed.
- `23d2492`'s `openapi.json` against the merged code: 1 failed, 1 passed.

## Implementer's claims

Confirmed:
- jig 4 rows `ok`;
- four-file run 148 passed;
- `test_wiring.py` 92 of 92 (81 + 11);
- whole suite 687 / 14 / 0;
- pyright 0;
- 3 repair files;
- MEDIUM 3 red before and 2 of 2 after;
- HIGH 1's four tests and their red run (4 failed, but see finding 3 for the wording);
- the `visitor = user` count (4) and the `visitor = None` count (6);
- the MEDIUM 2 counts: (i) 3, (ii) 4, demo count 1 → 1;
- LOW 5: red 3, sabotage 0 → 3, sabotage 20 → 2;
- the LOW 4 docstring;
- the LOW 6 removal;
- the merge commit has a default message and no trailer.

Not checked: "exit 0 on the first attempt". I can only see this head.

## What `records` and the PR body must carry

1. ADR-0008: the per-process identity provider and its key cache (finding 5); the History choice for a deleted user's session, unless it is fixed first (finding 1); the half-configured sign-in behaviour (finding 2).
2. `src/receipts/auth/gate.py:34-35`: a missing key raises `PermissionError` naming the variable (finding 6).
3. PR body:
   - the merge commit `23d2492` and why it exists (finding 4);
   - HIGH 1's red run stated as 3 `DID NOT RAISE` + 1 assertion on the claims list (finding 3);
   - the MEDIUM 2 tests pin existing behaviour, with sabotage (i) and (ii) as their red evidence.

Practice applied: sabotage each guard separately. Both sabotages that stayed green on the first pass (674 of 674) now fail 5 of 687, so the half-configured path is covered and not just read.

VERDICT: PASS
