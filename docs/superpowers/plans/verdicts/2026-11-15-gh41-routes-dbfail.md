# Verdict: gh41 routes-dbfail (head 2c13cc5, base bdbf418)

Blind judge, fresh context. Inputs: the `routes` verdict (`docs/superpowers/plans/verdicts/2026-11-15-gh41-routes.md`, findings 1 and 2), brief `docs/superpowers/briefs/2026-11-15-gh41-google-sign-in.md:15`, `AGENTS.md` sections 4 and 6, `git diff bdbf418...2c13cc5`. Worktree `.worktrees/gh41-routes-dbfail`, branch `jay/gh-41-routes-dbfail`. Every command was run from the worktree root. The sabotage driver, the probes and the exported red tree are in the session scratchpad (`/private/tmp/claude-501/-Users-jay-Projects-receipts/477932e0-9e2e-4163-93cf-4433b57d002f/scratchpad/dbfail_sab/`, `.../dbfail_probe/`, `.../red1b77158/`), not in the repo.

| # | Severity | Finding | Citation (`file:line` or command + exit) | Fix |
|---|---|---|---|---|
| 1 | LOW | The docstring limits the 503 to "a database error while that row is read or written". The `except` actually covers all of `_finish_login`, and that includes building the repo and running `create_schema`. So a store that cannot even be built also answers 503 `user_store`. That behaviour is right; the sentence just names less than the code does. | `src/receipts/auth/routes.py:14-15` (sentence); `:281` calls `get_user_repo`, which builds the repo and runs `create_schema` at `:210-211`; `:337-340` (except). Probe `dbfail_probe/no_repo_probe.py`: no injected repo, `DATABASE_URL` with a driver that does not exist and a synthetic password. At head: exit 0, `status 503 \| detail {'detail': 'sign-in check failed: user_store'} \| synthetic password in response: False \| round trip cleared: True`. At base: exit 0, `escaped: NoSuchModuleError`. | Change it to "A database error from the users store (building it, its schema, or the row; any `SQLAlchemyError`) is 503". |
| 2 | LOW | The implementer claims "6 of 6 extra sabotages of the 503 path red", but neither commit lists the 6, so they cannot be checked one by one. This verdict's own runs (check 4) stand in for them. | `git log -2 --format=%B 2c13cc5` exit 0: both messages describe the change, and neither lists any sabotage. | In the PR body, list the 6 sabotages or cite this verdict's list. |

## Checks

1. **Scope.** `git diff --name-only bdbf418...2c13cc5 | sort` lists `src/receipts/auth/routes.py` and `tests/test_auth_routes.py`, so 2 of 2 paths. Both fall inside the brief's `Allowed` globs (`src/receipts/auth/**` and `tests/test_auth*.py`). The commits are `1b77158` (red) and `2c13cc5` (green). The auth router is still not included in `create_app()` (`src/receipts/api/app.py:60-61`), and `grep -c auth/callback docs/api/openapi.json` exits 1, so the OpenAPI file does not change.
2. **Exit command and suite.**
   - `env -u ... bin/jig`: exit 0. Rows: python format `ok`, lint `ok`, types `ok`, tests `ok` (4 of 4).
   - `env -u ... uv run pytest tests/test_auth_routes.py -q`: exit 0, 68 passed of 68 collected, 0 skipped (`-rs` lists none).
   - The new test run alone (`-k user_store_failure`): exit 0, 2 passed and 66 deselected.
   - Whole suite `-m "not integration" -q -rs`: exit 0, 643 passed and 14 deselected of 657 collected, 0 skipped.
   - `uv run pyright src/receipts/auth`: exit 0, `0 errors, 0 warnings, 0 informations`.
   - `grep -n "type: ignore"` on both files exits 1. So does `grep -nE "dict\[str, *Any\]|\bAny\b"`, and so does `grep -nE "logging|logger|print\(|os\.environ|getenv" routes.py`.
   - Run with a socket-guard plugin (`netguard/netguard_plugin.py`): exit 0, 68 passed, `NETGUARD blocked attempts: 0`.
3. **The `except` block** (`src/receipts/auth/routes.py:337-340`).
   - It reads `except SQLAlchemyError:` with no `as`, so the error is never bound to a name.
   - The block holds one comment, one constant (`status.HTTP_503_SERVICE_UNAVAILABLE`) and `return _refused(_USER_STORE, clear_round_trip=True, status_code=unavailable)`. Nothing is logged or raised again.
   - The detail is the constant `sign-in check failed: user_store` (`_USER_STORE` at `:119`, `_refused` at `:290-297`).
   - `_refused` clears the round-trip cookie with `**COOKIE_FLAGS`, which are `path="/"`, `secure`, `httponly` and `samesite="lax"` (`src/receipts/auth/session.py:49-54`). It never calls `_set_session`, so no session cookie is set.
   - **The departure from `raise HTTPException(...) from None` is at least as safe.** Returning a response creates no second exception, and the `SQLAlchemyError` ends with the `except` block. There is one theoretical hole: if `_refused` itself raised, the new error would carry the database error as `__context__`. `raise ... from None` has the same `__context__` (`from None` only hides it when printed). `_refused` builds a JSON body from a constant and deletes a cookie with constant flags, and neither depends on the request or on the error, so I found no input that makes it raise. The returned form is also the only one of the two that clears the cookie: sabotage (i) below, `raise HTTPException(503, ...) from None`, went red at `tests/test_auth_routes.py:579`.
   - SQLAlchemy 2.1.8 does not log inside `_handle_dbapi_exception`: `grep -nE "_log|logger|warn\("` over its 200-line body exits 1.
   - The repr of a SQLAlchemy error leaves out the bound parameters: probe exit 0, `param in repr: False | param in str: True`.
4. **Sabotage.** Each edit was applied alone and the file was run. After each, `git checkout -- src/` reverted it, and `git diff --exit-code -- src/` exited 0. Required (a)-(e): **5 of 5 red.**
   - (a) `except SQLAlchemyError as exc:` plus `logging.getLogger(__name__).error("user store failed: %s", exc)`: 2 of 68 failed, at `tests/test_auth_routes.py:592` (`... reached the log`).
   - (b) `clear_round_trip=False` on the 503: 2 of 68 failed, at `:579` (`KeyError: 'receipts_oauth'`, because there is no `Set-Cookie` for the round trip).
   - (c) `status_code` dropped, so the answer is 400: 2 of 68 failed, at `:575`.
   - (d) `_refused` deletes the cookie with `path="/auth"`: **9 of 68 failed**, every one at `:264` (`assert '/auth' == '/'`). They are the 3 wrong-state cases, the 4 claim-validation cases and the 2 store-failure cases. That closes `routes` finding 2, where the same sabotage left 66 of 66 green.
   - (e) `except IntegrityError` only: 1 of 68 failed, `[OperationalError]`, because the error escaped from `:551`.
   - Extra sabotages: **7 of 7 red**, each 2 of 68 failed:
     - `logger.exception("user store failed")`, whose message is constant: red at `:592`, from the traceback text.
     - `logger.debug("...: %s", exc)`: red at `:592`.
     - a bare `raise`: the error escaped.
     - a detail of `str(exc)`: red at `:576`.
     - `print(exc)`: red at `:592` (`stdout or stderr`).
     - (i) `raise HTTPException(503, ...) from None`: red at `:579`.
     - a detail of `database`: red at `:576`.
   - One control stayed green: 68 of 68 passed with `logger.debug("...: %r", exc)`. That is correct, because the repr carries no parameters (check 3), so nothing leaked.
   - Total: 12 of 12 sabotages that leak or change behaviour went red.
5. **Red first.** `git show --stat 1b77158` changes `tests/test_auth_routes.py` only (69 insertions, 1 deletion). `git diff --exit-code 1b77158 2c13cc5 -- tests/` exits 0, so the tests did not change between red and green. I exported the red tree with `git archive 1b77158` and ran it against its own `routes.py` (confirmed by `__file__`): exit 1, **2 failed of 68**. The failures are both cases of `test_a_user_store_failure_is_503_clears_the_round_trip_and_leaks_no_identity` (`[OperationalError]`, `[IntegrityError]`). Each escapes through `src/receipts/auth/routes.py:274` (`in _finish_login`) out of the fake's `get_or_create` at `tests/test_auth_routes.py:551`. That is the stated reason. The red commit message names the test and the reason.
   - The test is not vacuous: `:583` asserts that the raised error's text contains both the synthetic email and the `sub` before checking that neither leaks.
   - `_logged` (`:554-557`) formats each record with `logging.Formatter`, which appends the exception text. That is why sabotage `logger.exception(<constant>)` went red.
6. **Synthetic data, no network.** The test file holds 3 email literals, all at `example.com` (lines 13, 533 and 630; `grep -noE` over the file). `grep -n "@" ... | grep -v example.com`, excluding decorators, exits 1. The new `sub` is `fake-sub-store-0002`.
   - `gitleaks git --log-opts=bdbf418..2c13cc5 --redact`: exit 0, 2 commits scanned, `no leaks found`.
   - `scripts/leak_gate/check_tracked.py`: exit 0, 149 files scanned against 2 patterns.
   - No ignore entry was added and no test was deleted.
7. **Docstring at `routes.py:13-20`**, quoted: "the round-trip cookie is cleared and the browser goes (302) to `/ui`. A failed check is 400 and writes no row. A database error while that row is read or written (any `SQLAlchemyError`) is 503, and the error is dropped unread: its text carries the bound `sub` and email, so it is never returned, raised again or logged. Both answer with the detail `sign-in check failed: <check>` (`user_store` for the database), naming the check and never a value, and set no session cookie. Every failure after the round-trip cookie verified, a failed check and a database error alike, also clears that cookie, so an attempt is not retried with the same values."
   - This matches the behaviour checked in checks 3 and 4, except for the scope of "while that row is read or written" (finding 1).
   - The `round_trip` refusal (`:331-332`) comes before the cookie is verified and correctly does not clear it.
   - `_finish_login`'s docstring (`:270-271`) and "Nothing here logs." (`:42`) still hold.
   - `routes` finding 1's complaint about this docstring was fixed in the docstring itself, not in a footnote.
8. **Claims checked.** Confirmed:
   - red `1b77158`: 2 failed of 68, from `routes.py:274`;
   - green: 68 of 68;
   - whole suite: 643 passed / 14 deselected / 0 skipped;
   - the unbound catch, the 503 `user_store`, the round-trip cookie cleared with every flag, no session cookie and nothing logged;
   - the test checks the response, the log at DEBUG with the exception text, and stdout/stderr;
   - `assert_auth_flags` added at `:405` and `:498`;
   - sabotage `path='/auth'` gives 9 of 68 red at `:264`;
   - the docstring was reworded.

   Not checked one by one: "6 of 6 extra sabotages" (finding 2).
9. **Outside this task, noted only.** `make_engine` still builds without `hide_parameters` (`src/receipts/db/repo.py:71`). Other routes' database errors still carry their bound parameters, for example `/auth/me`'s `get(session.user_id)` at `routes.py:357`. That one carries our user id, not an email, a `sub` or a secret, so the rule at brief:15 is not broken.

At the finish, `git diff --exit-code -- src/` exits 0 and `git status --porcelain` prints nothing (exit 0) in the worktree, at head `2c13cc5`.

Sabotages red: (a), (b), (c), (d) (9 of 68), (e), plus 7 of 7 extras. The `%r` control stayed green, correctly.

VERDICT: PASS
