# Judge verdict: gh-41 whole PR and its final task `records` (issue #41, Sign in with Google)

Blind judge, fresh context. My runs took place 2026-11-16 06:44 to 06:54 UTC (`date -u`).

- Worktree `.worktrees/gh41-records`, branch `jay/gh-41-records`, head `3145d8f`. `origin/main` is `c5d0114`, which is also the merge base. The diff judged is `git diff origin/main...3145d8f`, 45 files.
- I read `AGENTS.md` in full (section 9 is part of the diff), the brief in full, the plan's "Approval and answers", "Coordinator rulings" and "Verdicts and PRs" sections, and the findings tables of the twelve task verdicts.
- Sabotages were edits in the working tree only. I reverted each one with `git checkout -- <file>` and checked `git diff --exit-code` after each: exit 0 for 12 of 12 reverts (sabotage h ran twice on Neon to capture the test id; one early attempt at sabotage a failed on a shell quoting error before any test ran). I used no stash, made no commit and created no worktree.
- End state: `git status --porcelain` prints 0 lines, `git diff --exit-code` exits 0, `git diff --cached --exit-code` exits 0, and HEAD is still `3145d8f`.
- UNSET below means `env -u VIRTUAL_ENV -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE`. `VIRTUAL_ENV` is unset only to silence uv's environment-mismatch warning; it is not a setting.
- I captured exit codes with `$?` on output written to a file, never through a pipe. I did not print `DATABASE_URL` or any part of it. The Neon count script prints only integers.

## Findings

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | MEDIUM (not accepted) | **ADR-0008 does not record the `unique=True` sabotage substitution.** The brief's Verification 4 says that removing `unique=True` from `UserRow.sub` turns "the Neon constraint test" red. On Neon, the duplicate-insert test cannot go red: `users_sub_key` already exists, and `create_all` never alters an existing table. The test that does go red is the drift check. No record in the diff says this, so a reviewer who follows the brief literally sees `test_duplicate_user_sub_is_rejected` stay green and has no record explaining why. The rubric for this verdict requires the sentence in ADR-0008, so I do not accept the gap. | `src/receipts/db/schema.py:59`. Sabotage h on Neon: exit 1, 1 failed of 12, `tests/test_db_constraints.py::test_users_unique_on_neon_matches_the_mapping`; `test_duplicate_user_sub_is_rejected` passed. Searching the records, `grep -rn "matches_the_mapping\|duplicate_user_sub\|unique=True" docs/adr docs/runbooks docs/security docs/api.md README.md AGENTS.md` exits 1. ADR-0008:62 records only the two algorithm-pin substitutions. | Add one bullet to ADR-0008 Consequences, beside :62. It should say: removing `unique=True` leaves `test_duplicate_user_sub_is_rejected` green on Neon (the constraint `users_sub_key` already exists and `create_all` does not alter it); `test_users_unique_on_neon_matches_the_mapping` goes red instead (1 of 12); on SQLite `tests/test_db_users.py::test_a_concurrent_first_sign_in_that_wins_the_insert_is_re_read` goes red (1 of 13). The fix is in the records scope; this is repair attempt 1 of 3. |
| 2 | LOW (carried, not deferred anywhere) | The `routes.py` docstring says less than the code does. It limits the 503 to "a database error while that row is read or written". The `except SQLAlchemyError` in `callback` covers all of `_finish_login`, including `get_user_repo` (building `SqlUserRepo` and running `create_schema`). ADR-0008:41 states the full scope correctly. No record in the diff defers the docstring fix, and `routes.py` is outside the `records` scope. | `src/receipts/auth/routes.py:14-15` against `:334-337` (`except SQLAlchemyError` around `_finish_login`), `:281` and `:203-211`; routes-dbfail verdict LOW 1 | The PR body names the item as deferred to a later auth-lane pass and quotes the suggested wording ("a database error from the users store (building it, its schema, or the row)"). |
| 3 | LOW (carried, not in a record) | The three `users` NOT NULL constraints have no rejection test on Neon. Spec :50, in a file this PR edits, still says "every schema constraint (NOT NULL, foreign key, CHECK, unique) is proven by an integration test" against Neon. That sentence is now false for the 3 new NOT NULL constraints on `users` (`sub`, `email`, `created_at`). The `users.sub` UNIQUE and the `runs.user_id` foreign key are proven on Neon. ADR-0008 does not mention the gap. | `src/receipts/db/schema.py:59-61`. `grep -nE "null\(\)" tests/test_db_constraints.py` hits only `:157` and `:165`, both on `runs`. `docs/superpowers/specs/2026-11-14-receipts-design.md:50`. db-repair verdict LOW 7. | The PR body (or ADR-0008) says the `users` NOT NULLs are not yet proven on Neon. A follow-up adds three `users` NULL cases in the `_assert_rejected` style. |
| 4 | LOW | Spec :50 contradicts this PR's own records. It says the integration tests run against the Neon `dev` branch and lists the tables as `runs, sources, search_results, claims, events`. ADR-0008:47 and the runbook say the integration run used the deployed database, and the PR adds `users`. The table list and the `dev` branch claim were already stale on `origin/main` (one `runs` table since the 2026-11-14 scope cut). The brief named only spec lines 18 and 51 for editing. | `docs/superpowers/specs/2026-11-14-receipts-design.md:50`; `docs/adr/0008-google-sign-in.md:47`; `docs/runbooks/render.md:103-104` | Fix it in a later records pass, or have the PR body name it as known drift outside the brief's line scope. |
| 5 | LOW (carried from the `oidc` verdict) | The session module docstring says "no exception escapes a verify call". A naive `now` raises `TypeError` at the expiry comparison, which is outside the `try`. | `src/receipts/auth/session.py:12` against `:107-112`; oidc verdict LOW 3 | PR body, or a later pass rewords the docstring ("for any token input; `now` must be timezone-aware"). |
| 6 | LOW (carried from the `contract` verdict) | The `.strip()` in `StartDecision.refuse` has no test. `tests/test_auth_models.py` has no whitespace-only reason case. | `src/receipts/auth/models.py:71`; `grep -n '"   "' tests/test_auth_models.py` exits 1 | PR body; optional follow-up adds `(False, "   ")`. |
| 7 | LOW (accepted by the `ui` judge) | `dict[str, Any]` appears in the public `account_view` return type, which `tests/` consumes. It is Gradio's `gr.update` type, inside the ADR-0006 basic-mode exception for `ui/`, and no domain type crosses. | `src/receipts/ui/app.py:179`, `:275`; ui verdict LOW 4 | PR body notes it. |
| 8 | LOW | Commit hygiene. 6 of the 9 merge commits carry git's default message and no trailer: `23d2492`, `bdbf418`, `7f72a15`, `9a942a1`, `5b94add`, `fd2f166`. The `Co-Authored-By` trailers are mixed across the 64 commits: 49 `Claude Fable 5.1`, 9 `Claude Opus 5.5` (the `oidc` and `routes-dbfail` commits and `1e7b0a5`), 6 none. | `git log --format='%(trailers:key=Co-Authored-By,valueonly)' origin/main..HEAD`; `git rev-list --merges origin/main..HEAD \| wc -l` gives 9 | The PR body names the six default-message merges (no history rewrite) and states the trailer split. |
| 9 | LOW | The quick red-first count overstates. `git log --oneline origin/main..HEAD \| grep -ci red` prints 17 of 64, but 2 are false matches: "configu**red**" in `0337ca1` and "sha**red**" in `0948b0a`. The true count is 15 of 64 red-first subjects. Each of the 15 changes only `tests/` files, and together they cover 7 of 7 new test files plus `test_settings`, `test_ui_app`, `test_api_runs` and `test_wiring`. | `git show --name-only --format= <sha>` for the 15 commits listed under Rubric C | The PR body lists red runs by file and commit, not by grep count. |

Counts: 0 CRITICAL, 0 HIGH, 1 MEDIUM (open, not accepted), 8 LOW.

## Rubric A: the brief's Verification, step by step

**1. Scope and frozen files.**
- `git diff --name-only origin/main...HEAD | sort` lists 45 paths, and 45 of 45 are in `Allowed:`.
- A grep for every `Forbidden:` pattern, including `docs/superpowers/plans/` and `docs/adr/000[1237]-`, exits 1: no hits. No plan or verdict file is in the diff.
- `AGENTS.md` changes only at hunks `@@ -104` and `@@ -107`. Both are below `## 9. Project overlay` at :89.
- `src/receipts/settings.py` changes only in the docstring (five names become ten, plus the ADR-0008 lift sentence) and the five fields at :26-30 with the brief's types and defaults.
- `pyproject.toml` adds one runtime line, `"joserfc>=1.8.0"`. ADR-0008:22-25 gives the reasons for joserfc over authlib.
- `uv.lock`: `git diff origin/main...HEAD -- uv.lock | grep -c '^-version'` prints `0`. The diff is 190 insertions and 0 deletions. The package count goes from 159 (`origin/main`) to 163 (head). The four added names are `cffi`, `cryptography`, `joserfc` and `pycparser`, with versions 2.1.1, 50.0.2, 1.8.0 and 3.12, as ADR-0008:22 says.

**2. UI and `auth_dependency` greps.**
- `grep -rnE "os\.environ|getenv|get_settings|receipts\.settings" src/receipts/ui/` exits 1.
- `grep -rn "auth_dependency" src/` exits 1.
- All 5 of 5 `src/receipts/ui/*.py` files start with `# pyright: basic`.

**3. `get_secret_value()` hits.** The grep over `src/receipts/auth` and `src/receipts/api/wiring.py` returns 11 hits.

| Hit | Class |
|---|---|
| `auth/session.py:12`, `auth/routes.py:43`, `auth/provider.py:37` | docstrings |
| `auth/session.py:94` | sign |
| `auth/session.py:108` | verify |
| `auth/provider.py:145` | token-exchange form body |
| `auth/routes.py:142` | blank check (`_is_set`, returns a bool) |
| `api/wiring.py:156` | blank check (`_is_set`; it was at `:103` on `origin/main`) |
| `api/wiring.py:195` | key handed to the Keenable client constructors (it was at `:142` on `origin/main`) |
| `api/wiring.py:395` | blank check |
| `api/wiring.py:397` | constant-time compare (`_passcode_ok`) |

None is inside `logger.*`, an `HTTPException` detail or an f-string that reaches a response. ADR-0008:63 records "Verification 3, as practised" and names all four classes.

**4. Sabotages.** Each was separate and reverted, with `git diff --exit-code` exit 0 after each. **8 of 8 of the brief's sabotages went red.**

| # | Sabotage | File run | Result |
|---|---|---|---|
| a | delete the nonce comparison (`oidc.py:63-64`) | `tests/test_auth_oidc.py` | exit 1, 8 failed of 43 (`test_a_mismatched_nonce_fails_the_nonce_check[*]`) |
| b | `_same(client_id, claims.aud)` replaced by `True` (`oidc.py:59`) | same | exit 1, 5 failed of 43 (`test_a_wrong_audience_fails_the_aud_check[*]`) |
| c1 | `exp > now` changed to `exp >= now` (`oidc.py:61`) | same | exit 1, 1 failed of 43 (`test_an_expired_token_fails_the_exp_check[exp-equals-now]`) |
| c2 | `exp` check dropped | same | exit 1, 3 failed of 43 (`[exp-equals-now]`, `[one-second-ago]`, `[one-day-ago]`) |
| d | `_verify` decodes the payload without the signature (`session.py:108-109`) | `tests/test_auth_session.py` | exit 1, 18 failed of 63, among them the tampered-cookie cases `test_a_session_with_one_changed_character_verifies_to_none[signature]` and `[header]`, `..._whose_payload_names_another_user...`, and `..._signed_with_another_secret...`. Some `garbage` cases also failed because my edit raises `IndexError`; that is an artefact of the sabotage, not a finding. |
| e | `may_start` returns `allow()` first (`limits.py:36`) | `tests/test_auth_limits.py` | exit 1, 9 failed of 16, among them `test_may_start[signed-in-5-of-5]` and `[signed-out-20-of-20]` |
| f | `list_runs_for` without `_owned_by` (`repo.py:271`) | `tests/test_db_users.py` | exit 1, 4 failed of 13 |
| f | same | `tests/test_api_runs.py` | exit 1, 4 failed of 19, among them `test_get_runs_with_a_session_cookie_lists_only_that_users_runs` |
| g | `create_app()` calls `get_settings()` (`app.py:64`) | `UNSET ... tests/test_settings.py::test_create_app_boots_with_an_empty_environment` | exit 1, 1 failed of 1, `AssertionError: settings were read`. After the revert: 1 passed. |
| h | `unique=True` removed (`schema.py:59`), on Neon | `uv run pytest tests/test_db_constraints.py -q -m integration -rfs` | exit 1, 1 failed of 12: `test_users_unique_on_neon_matches_the_mapping`. `test_duplicate_user_sub_is_rejected` stayed green, as the `db` verdict established. 0 skipped. ADR-0008 does not record this substitution (finding 1). |
| h | same, on SQLite (extra) | `tests/test_db_users.py` | exit 1, 1 failed of 13: `test_a_concurrent_first_sign_in_that_wins_the_insert_is_re_read` |

**5. Whole suite, files alone, gates.**
- `UNSET uv run pytest -q -m "not integration" -rs` exits 0: `687 passed, 14 deselected`. That is 701 collected, **0 skipped** (no skip lines).
- Each file alone under UNSET, all exit 0 and 0 skipped. New files: `test_auth_limits.py` 16 of 16, `test_auth_models.py` 21 of 21, `test_auth_oidc.py` 43 of 43, `test_auth_provider.py` 69 of 69, `test_auth_routes.py` 68 of 68, `test_auth_session.py` 63 of 63, `test_db_users.py` 13 of 13. Changed files: `test_api_runs.py` 19 of 19, `test_wiring.py` 92 of 92, `test_ui_app.py` 29 of 29, `test_settings.py` 8 of 8.
- `test_db_constraints.py` under UNSET with `-m "not integration"` exits 5 with 12 deselected, as intended: it is integration-only.
- `UNSET bin/jig` exits 0: format, lint, types and tests, 4 of 4 `ok`.
- `uv lock --check` exits 0 ("Resolved 163 packages").
- `uv run pip-audit --strict --vulnerability-service osv` exits 0 and prints `No known vulnerabilities found` (2026-11-16 06:46 UTC).
- `grep -c ignore-vuln .github/workflows/security.yml` prints `0`.
- `uv run python scripts/export_openapi.py` exits 0, then `git diff --exit-code docs/api/openapi.json` exits 0.
- `env -i PATH="$PATH" HOME="$HOME" uv run python -c 'from receipts.api.app import create_app; create_app()'` exits 0.
- `uv run pyright src` exits 0: `0 errors, 0 warnings, 0 informations`.
- `grep -rn "type: ignore" src/ tests/` exits 1.
- `git diff origin/main...HEAD -- tests/ | grep -E '^\+.*(pytest\.mark\.skip|pytest\.skip\(|xfail)'` exits 1. The one removed `def test_` (`test_create_app_injects_the_starter_into_the_ui`) was renamed and extended to `test_create_app_injects_the_starter_and_the_gate_into_the_ui` (`tests/test_wiring.py:224`), as the plan's `wiring` note required.

**Neon.** `uv run pytest tests/test_db_constraints.py -q -m integration -rs` exits 0: **12 of 12 passed, 0 skipped**. Count queries (`uv run python` with `receipts.settings.sqlalchemy_url`, URL never printed), taken before the run, after it, and after the sabotage-h runs, were identical each time:

| Query | Count |
|---|---|
| `users` total | 0 |
| `runs` where `id like 'constraint-test-%'` | 0 |
| `users` where `sub like 'fake-sub-%'` | 0 |
| `runs` where `user_id is not null` | 0 |
| `runs` total | 3 (the last known value) |

**6. Synthetic boot (the owner's browser step not attempted).** I used `TestClient` with base URL `http://localhost:8000` and `GOOGLE_CLIENT_ID=client-id-not-real GOOGLE_CLIENT_SECRET=not-a-real-secret SESSION_SECRET=<openssl rand -hex 32, not printed> DEMO_PASSCODE=open-sesame`. Anthropic and Keenable keys were unset in both runs.

Without `DATABASE_URL`:
- `GET /ui` answers 307 to `/ui/` (Gradio's mount), and `GET /ui/` answers 200.
- `/ui/config` has the `Passcode` textbox, `visible=True`.
- `POST /ui/gradio_api/run/account` answers 200 with the line `0 of 20 signed-out runs used today (UTC)` and no "Sign in with Google". `gate.account(None)` returns `sign_in_available=False`.
- `GET /auth/me` answers 401 `{"detail":"not signed in"}`.
- `GET /auth/login` answers 503 `{"detail":"DATABASE_URL is not set"}`. The detail contains none of the four synthetic values and sets no cookie.

With `DATABASE_URL=sqlite:///<scratchpad>/v6.sqlite`:
- `GET /auth/login` answers 302 to `https://accounts.google.com/o/oauth2/v2/auth` with `state`, `nonce`, `code_challenge`, `code_challenge_method=S256`, the `localhost:8000` callback and `scope=openid email`.
- It sets the cookie `receipts_oauth` with `HttpOnly`, `Max-Age=600`, `Path=/`, `SameSite=lax` and `Secure`. No secret value appears in the `Location`.
- `GET /auth/login` with `Host: 127.0.0.1:8000` answers 302 to `http://localhost:8000/auth/login` with no cookie.
- `/ui/`, `/ui/config` and `/ui/gradio_api/login_check` all answer 200 signed out.
- The UI still hides sign-in in this half-configured state, as ADR-0008:59 says.
- `POST /auth/logout` answers 303 to `/ui`.
- `/healthz` answers 200 with `{"status","sha","version"}` and `X-Receipts-Mode: demo`.

The SQLite file was deleted.

**7. Records.**
- `grep -n "user accounts"` on the spec exits 1.
- `grep -n "no accounts" AGENTS.md` exits 1.
- `grep -n Google docs/adr/0004-approved-ai-vendors.md` hits :31 (Neon row), :32 (Render), :41 (the new Google sign-in row) and :42 (the existing storage.googleapis.com row).
- `ls docs/adr/0008-*.md` lists one file. It names the dependency (:22), the lifted files (:21), the package counts 159 to 163 (:52) and `pip-audit` with dates (:52).

I checked each record against the code on this head:
- **Settings and defaults:** match `settings.py:26-30` (ADR-0008:29-35, README env table, runbook :14-20).
- **DDL:** ADR-0008:47 and runbook match `repo.py:76-77`.
- **Cookie names, TTLs and flags:** match `session.py:30-35` and `:49-53` (`receipts_session` 7 days, `receipts_oauth` 10 minutes).
- **Session payload:** `{uid, exp}` matches `session.py:70-71`.
- **Routes and status codes:** `docs/api.md` matches `openapi.json`: POST `/api/runs` 202/401/422/429/503; `/auth/login` 302/503; `/auth/callback` 302/400/422/503; `/auth/logout` 303; `/auth/me` 200/401. The 10 check names in `docs/api.md` equal the 9 `AuthError` literals plus `round_trip`.
- **Identity provider:** built per process by `get_identity_provider` at `routes.py:191-200`, cached on `app.state`.
- **Refusal texts:** match `limits.py:17` and `:22-25`.
- **429:** `api/routes.py:68-81`.
- **303 logout:** `routes.py:347-351`.
- **Deletion order:** runs, then the user row, from the FK without `ON DELETE` (`repo.py:76`; runbook :145-158).
- **Testing-mode sentence:** README :23 and runbook :76.
- **Deletion channel:** "by contacting the repository owner" at AGENTS.md :108.
- **`SIGNED_OUT_RUNS_PER_DAY` default 20** everywhere.
- **httpx parents:** `uv tree --frozen --invert --package httpx --depth 1 --no-dev` lists the same 8 parents as ADR-0008:26.
- **requests users:** the same 5 as ADR-0008:26.
- **joserfc upload time:** `upload-time = "2026-11-03..."`, matching ADR-0008:22.
- **Threat model and ADR-0008:** every cited test name exists. That is 35 of 35: 32 in the threat model, 3 in ADR-0008, each `def` found exactly once. All 9 of 9 cited parametrize ids exist in `--collect-only`.
- **Identities:** the only email addresses on added lines are at `example.com`, and no real person's name was added.
- **Language:** all English.
- **No footnotes:** the edits were made where the stale text stood: spec :18-19 and :52, AGENTS.md :108, ADR-0004 :31.

The exception is spec :50, which is stale (findings 3 and 4).

## Rubric B: carried items

| Item | Where on this head | Status |
|---|---|---|
| joserfc reasons | ADR-0008:22-25, :69 ("second entry" corrected, contract LOW 4) | recorded |
| httpx undeclared, 8 parents, risk | ADR-0008:26 | recorded, verified against `uv tree` |
| `OAuthRoundTrip` in `oidc.py` | ADR-0008:38 | recorded |
| `IdentityProvider` protocol / `GoogleIdentityProvider` real | ADR-0008:38; `provider.py:63`, `:100`; brief :32 renamed in `4141603` | recorded |
| `email_verified` dropped | ADR-0008:48 | recorded |
| session payload `{uid, exp}` | ADR-0008:43; threat model | recorded |
| boot test proves only "no `get_settings()` call" | ADR-0008:27 | recorded (contract LOW 3 closed) |
| Verification 3 as practised | ADR-0008:63 | recorded |
| `unique=True` sabotage substitution | nowhere | **missing (finding 1)** |
| two unobservable algorithm-pin sabotages | ADR-0008:62 | recorded |
| count-then-claim non-atomic; a simultaneous burst can exceed the signed-out cap | ADR-0008:56; threat model "Run budget" row | recorded |
| unclaimed window | ADR-0008:57 (says "has not been measured", no sub-second claim) | recorded |
| per-process provider, JWKS cache with no expiry | ADR-0008:45, :72 | recorded (wiring LOW 7 closed) |
| deleted-user cookie (start and account signed out; History under the stale id; empty in practice) | ADR-0008:58, :73; threat model last row | recorded |
| half-configured state (302, 200, sign-in hidden) | ADR-0008:59; runbook "When the UI offers it" | recorded, reproduced in step 6 |
| `/ui/gradio_api/run/account` exposure | ADR-0008:60; threat model "Personal data" row | recorded |
| `routes.py:14-15` docstring | nowhere | **not deferred in a record (finding 2)**; PR body |
| ADR-0004: Google row; Neon row corrected | :41; :31 (plus Render :32) | recorded |
| AGENTS.md section 9: Data bullet, L7, Frozen line | :108; :104; :105 | recorded |
| Runbook: env names | :14-20 | recorded |
| Runbook: `user_id` check | :106-131 | recorded |
| Runbook: Testing mode | :76-80 | recorded |
| Runbook: `localhost:8000` | :101-104 | recorded |
| Runbook: `--tb=short` note | :137-143 | recorded |
| Runbook: deletion order | :145-158 | recorded |
| Runbook: owner's post-deploy steps | :161-173 | recorded |
| `gate.py` `MissingSettingError` stale (wiring LOW 8) | `gate.py:32-36` now says `PermissionError` (gate-docstring-2) | resolved in code |
| `users` NOT NULLs untested on Neon (db LOW 6/7) | nowhere | not recorded (finding 3); PR body |

## Rubric C: hygiene

- `gitleaks git --log-opts="origin/main..HEAD" --redact --exit-code 1` (8.30.1) exits 0: "55 commits scanned", "no leaks found". That is 64 commits minus the 9 merges.
- `python3 -I scripts/leak_gate/check_tracked.py` exits 0: "scanned 203 files against 2 patterns".
- `git log --format=%s origin/main..HEAD | wc -l` gives 64 commits, of which 9 are merges.
- `git log --oneline origin/main..HEAD | grep -ci red` gives 17 of 64. 15 of 64 are true red-first subjects: `213a4a3`, `0cf19e8`, `6747ecb`, `1a0ce51`, `4039fd2`, `51f7543`, `a09c2b3`, `cc28659`, `64fedd6`, `c7f17b1`, `ce17775`, `1b77158`, `44372b5`, `4acbbb9`, `05d04ed`. Each changes only `tests/` files (finding 9).
- Merge commits and trailers: finding 8.
- Records commit `4141603` edited the brief (line 32, protocol name only) after dispatch, to match the code (provider verdict LOW 11).

## What the PR body must contain

1. "N of M" for every test file, from step 5 above:
   - whole suite: 687 passed, 14 deselected, 0 skipped of 701 collected;
   - Neon: 12 of 12, 0 skipped;
   - each new file's count (16, 21, 43, 69, 68, 63 and 13 of the same).
2. The red run for each new test file: file, red commit (the 15 above), exit code and one failure line. It must also carry the corrections the task verdicts asked for:
   - `0149fa6`'s "3 `UndefinedColumn`" was 2 `UndefinedColumn` + 1 column assertion, of 12;
   - the wiring HIGH red was 3 `DID NOT RAISE` + 1 claims-list assertion, not 4;
   - the oidc second red was 2 of 4 `'bool' object is not iterable` + 2 of 4 `list indices...`;
   - provider "57 failed" holds only for the `async with` form (5 for `aclose`);
   - green commit `154e82e` re-wrapped 3 test lines (AST identical);
   - `e677782`'s title "four pinned" is 3 of 4 true;
   - db-repair: `test_a_claim_survives_the_later_save_run_append_event_and_save_battlecard`, exit 1, `1 failed, 12 passed` per sabotage.
3. The sabotage lists, or citations to the verdicts that hold them:
   - the brief's 8 (this verdict: 8 of 8 red, with h through the drift check);
   - contract's 9 model sabotages;
   - oidc 32 of 33;
   - limits 11 of 11;
   - ui 14 of 15 (`a598c93` lists none);
   - provider 34 of 38;
   - routes 43 of 44 (the implementer's "38 of 38" is unlistable);
   - routes-dbfail 5 of 5 + 7 of 7 (the "6 of 6" is unlisted);
   - wiring 32 of 34 and the repair's row-check sabotages.
4. The merge-commit note: 6 of 9 merges have default messages and no trailer (finding 8), no rewrite. Also the trailer split: 49 Fable 5.1, 9 Opus 5.5, 6 none, of 64.
5. The carried LOWs not in any record:
   - findings 2 to 7;
   - limits LOW 3 (second parametrize lacks ids);
   - ui LOW 5 (no-Gate component set unpinned) and LOW 6 (`login_check` unasserted; this judge probed 200);
   - routes LOW 5 (consent-screen cancel gives raw JSON 400);
   - the `make_engine` `hide_parameters` note (already in the threat model).
6. The owner's steps still open:
   - Verification 6 (local browser sign-in, `0 of 5 runs used today (UTC)` after sign-in);
   - the post-deploy acceptance list (runbook :161-173);
   - the Testing-mode / publish decision.

## Verdict

0 HIGH. 1 MEDIUM (finding 1) is open. The rubric for this verdict names it as required in ADR-0008, and the fix is one bullet inside the `records` scope, so I do not accept it. Everything else holds:
- scope 45 of 45 in Allowed, 0 Forbidden;
- the 8 of 8 brief sabotages red;
- 0 skips;
- Neon 12 of 12 with the counts unchanged at 0/0/0/0/3;
- every gate exits 0.

After a one-bullet ADR-0008 repair (attempt 1 of 3), a re-judge needs only finding 1 re-checked plus `bin/jig`.

VERDICT: FAIL
