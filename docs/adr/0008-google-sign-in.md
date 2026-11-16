# ADR-0008: Optional Google sign-in, per-user History and daily run limits

**Status:** accepted · **Date:** 2026-11-15 · GitHub issue #41. The repository owner (`JayR1031`) decided on 2026-11-15, answering the brief's first question for issue #41, that sign-in is optional (option b): a signed-in visitor starts runs without the passcode under a per-user daily limit, and a signed-out visitor keeps the passcode path under a global daily cap on signed-out runs.

## Context

Issue #41 asks for "Sign in with Google", History that shows only the visitor's own runs, and a per-user daily run limit. The owner plans to post the app publicly, and hackathon judges may open it while the Google OAuth app is still in Testing mode, when only the owner can sign in. Mandatory sign-in would stop judges and visitors from starting any run. Keeping only the passcode, with nothing counting signed-out runs, would let anyone who sees a leaked passcode spend the Anthropic and Keenable budget, which the spec names as an anti-goal. Option (b) keeps both paths and counts each.

Sign-in needs three things the code does not have:

- an OAuth 2.0 authorization-code flow against Google with PKCE (Proof Key for Code Exchange: the browser never holds a reusable secret, because the code is bound to a one-time verifier the server keeps);
- verification of Google's ID token, a JSON Web Token signed with RS256 (RSA) whose public keys Google publishes as a JSON Web Key Set (JWKS);
- a signed session cookie that carries our user id and an expiry.

Python's standard library can compute an HMAC (enough for an HS256 cookie) but cannot verify an RSA signature, and no JOSE or cryptography package is in the lock today (`uv.lock` at `6e59412` has no `authlib`, `pyjwt`, `joserfc`, `python-jose`, `cryptography` or `itsdangerous` entry).

`pyproject.toml`, `uv.lock` and `src/receipts/settings.py` have been frozen since Wave 0 (AGENTS.md section 9, ADR-0006). The freeze matters because every lane builds against the same locked environment and the same lazy `Settings`, and `settings.py` is what lets the image boot with no secrets (ADR-0005; `tests/test_settings.py::test_create_app_boots_with_an_empty_environment` and CI's api-image boot both start the app with an empty environment). Changing any of the three needs the owner's approval on record.

## Decision

- **The freeze is lifted for issue #41 only**, on exactly three files: `pyproject.toml`, `uv.lock` and `src/receipts/settings.py`. `src/receipts/contracts.py`, `src/receipts/fakes/**` and `tests/conftest.py` stay frozen: `RunService.start(request)`, `RunRepo.list_runs()` and `RunSummary` do not change. Nothing else in the freeze changes.
- **One runtime dependency: `authlib>=1.9.6`** (1.9.6 locked; PyPI upload 2026-11-14), added with `uv add authlib`. The lower bound is the version uv picked, as for the other dependencies; no exact pin, because nothing here relies on one release's internals. authlib requires `cryptography>=45.0.1` and `joserfc>=1.6.8`, and the lock adds exactly those plus their own requirements: `joserfc` 1.8.0, `cryptography` 50.0.2, `cffi` 2.1.1 and `pycparser` 3.12 (`uv tree --package authlib --no-dev`). One install covers both needs: JOSE (HS256 sign and verify for our session and OAuth round-trip cookies; RS256 verification against a JWKS for Google's ID token) and the OAuth 2.0 and OpenID Connect client helpers, including the PKCE S256 challenge (`authlib.oauth2.rfc7636`) and an httpx-based client (`authlib.integrations.httpx_client`).
- **JOSE goes through `joserfc`, not `authlib.jose`.** Measured on the locked 1.9.6: `import authlib.jose` emits `AuthlibDeprecationWarning: authlib.jose module is deprecated, please use joserfc instead. It will be compatible before version 2.0.0.` `joserfc` is authlib's own JOSE library (same maintainer, BSD-3-Clause) and one of its declared requirements, so using it adds no package. It is not listed separately in `pyproject.toml`, because that would be a second direct dependency; it is present for as long as authlib requires it.
- **Typing under pyright strict.** `joserfc` ships `py.typed`; `authlib` does not. A scratch probe outside the repository, in strict mode against this lock, gave 0 errors on `joserfc.jwt`/`joserfc.jwk` lines and 3 on one use of `authlib.oauth2.rfc7636.create_s256_code_challenge` (`reportUnknownVariableType`, `reportUnknownArgumentType`). `src/receipts/auth/` is strict with no `# type: ignore` (ADR-0006), so an untyped authlib call needs a typed wrapper or a standard-library equivalent (the S256 challenge is the base64url SHA-256 of the verifier).
- **HTTP for the token exchange uses `httpx`**, already locked (through gradio, gradio-client, huggingface-hub, langchain-core, litellm and others). authlib has no path to `requests`: `uv tree --invert --package requests --depth 1 --no-dev` lists the same five direct users before and after this change (langchain-keenable, langsmith, mellea, requests-toolbelt, tiktoken), and the full inverted tree names no authlib. `requests` was already in the lock and authlib does not add a path to it.
- **Five settings, all optional**, on the existing lazy `Settings` in `src/receipts/settings.py`. They are read per request through `get_settings()`, never at import and never in `create_app()`. Because every field is optional, reading them in an empty environment would not fail, so `tests/test_settings.py::test_create_app_boots_with_an_empty_environment` also asserts that import and `create_app()` leave `get_settings`'s cache empty:

  | Variable | Field | Default |
  |---|---|---|
  | `GOOGLE_CLIENT_ID` | `google_client_id: str \| None` | `None` |
  | `GOOGLE_CLIENT_SECRET` | `google_client_secret: SecretStr \| None` | `None` |
  | `SESSION_SECRET` | `session_secret: SecretStr \| None` | `None` |
  | `RUNS_PER_USER_PER_DAY` | `runs_per_user_per_day: int` | `5` |
  | `SIGNED_OUT_RUNS_PER_DAY` | `signed_out_runs_per_day: int` | `20` |

  The client id is a plain `str` because it is not a secret: it appears in the authorization URL every visitor's browser sees. The module docstring's list of names grows from five to ten. Sign-in needs `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET` and `DATABASE_URL`; with any of them missing, sign-in is unavailable and everything else works as before.
- **Shared types and one seam for the UI.** `src/receipts/auth/models.py` holds the frozen domain types (`User`, `SessionUser`, `IdTokenClaims`, `StartDecision`, `AccountStatus`, `AuthError`). `src/receipts/auth/gate.py` holds the `Gate` protocol, the only way identity reaches `src/receipts/ui/`. `create_app()` stores the live `Gate` on `app.state.gate` before `mount_ui(app)`; with no `Gate` there, the UI behaves as it did before this ADR.
- **To be recorded by the `records` task** (facts later tasks decide; not decided here):
  - how the `runs.user_id` column reaches the deployed Neon `runs` table;
  - whether the real provider checks the ID token's signature against Google's published keys, and how;
  - that counting a user's runs and then claiming a new one is not atomic, and what that allows;
  - the sub-second window in which a just-started run belongs to no user.

## Consequences

- **More packages.** The lock grows from 159 to 164 packages (`grep -c '^\[\[package\]\]' uv.lock`, at `6e59412` and after `uv add authlib`): authlib, joserfc, cryptography, cffi and pycparser. `uv lock --check` exits 0. `uv run pip-audit --strict --vulnerability-service osv`, the command in `.github/workflows/security.yml`, printed `No known vulnerabilities found` and exited 0 on the new lock (2026-11-16 01:12 UTC, 2026-11-15 in Miami). No `--ignore-vuln` was added (`grep -c ignore-vuln .github/workflows/security.yml` prints `0`).
- **A new release.** authlib 1.9.6 reached PyPI the day before it was locked. The audit covers known advisories only; an upgrade past 1.9.6 re-runs it and re-reads the deprecation note above, since authlib 2.0.0 may remove `authlib.jose`.
- **New stored data.** For a person who signs in, the app stores their Google subject id (`sub`) and email address, nothing else from the profile. The section 9 data rule, the spec's non-goals and ADR-0004 change in the same PR (the `records` task).
- **No new gate exceptions.** Pyright stays strict on `src/receipts/auth/`, and no `--ignore-vuln` flag is added.

## Alternatives considered

- **Standard library only.** HMAC covers an HS256 cookie, but nothing in the standard library verifies Google's RS256 signature, so the ID token check would need a cryptography package anyway. Rejected.
- **PyJWT.** It covers JSON Web Tokens, but not the OAuth 2.0 client or PKCE, which would then be written by hand. Rejected in favour of one package that covers both.
- **Gradio's `auth_dependency` on the `/ui` mount.** In the locked gradio 6.32.0 a mount with `auth_dependency` answers 401 whenever the dependency returns `None`, which would turn every signed-out visitor away from `/ui`, the opposite of option (b) (the brief for #41 records the probe). Rejected.
