# ADR-0008: Optional Google sign-in, per-user History and daily run limits

**Status:** accepted · **Date:** 2026-11-15 · GitHub issue #41. The repository owner (`JayR1031`) decided on 2026-11-15, answering the brief's first question for issue #41, that sign-in is optional (option b): a signed-in visitor starts runs without the passcode under a per-user daily limit, and a signed-out visitor keeps the passcode path under a global daily cap on signed-out runs.

## Context

Issue #41 asks for "Sign in with Google", History that shows only the visitor's own runs, and a per-user daily run limit. The owner plans to post the app publicly, and hackathon judges may open it while the Google OAuth app is still in Testing mode, when only the owner can sign in. Mandatory sign-in would stop judges and visitors from starting any run. Keeping only the passcode, with nothing counting signed-out runs, would let anyone who sees a leaked passcode spend the Anthropic and Keenable budget, which the spec names as an anti-goal. Option (b) keeps both paths and counts each.

Sign-in needs three things the code does not have:

- an OAuth 2.0 authorization-code flow against Google with PKCE (Proof Key for Code Exchange: the browser never holds a reusable secret, because the code is bound to a one-time verifier the server keeps);
- verification of Google's ID token, a JSON Web Token signed with RS256 (RSA) whose public keys Google publishes as a JSON Web Key Set (JWKS);
- a signed session cookie that carries our user id and an expiry.

Python's standard library can compute an HMAC (enough for an HS256 cookie) but cannot verify an RSA signature, and no JOSE or cryptography package is in the lock today (`uv.lock` at `6e59412` has no `pyjwt`, `joserfc`, `python-jose`, `cryptography` or `itsdangerous` entry).

`pyproject.toml`, `uv.lock` and `src/receipts/settings.py` have been frozen since Wave 0 (AGENTS.md section 9, ADR-0006). The freeze matters because every lane builds against the same locked environment and the same lazy `Settings`, and `settings.py` is what lets the image boot with no secrets (ADR-0005; `tests/test_settings.py::test_create_app_boots_with_an_empty_environment` and CI's api-image boot both start the app with an empty environment). Changing any of the three needs the owner's approval on record.

## Decision

- **The freeze is lifted for issue #41 only**, on exactly three files: `pyproject.toml`, `uv.lock` and `src/receipts/settings.py`. `src/receipts/contracts.py`, `src/receipts/fakes/**` and `tests/conftest.py` stay frozen: `RunService.start(request)`, `RunRepo.list_runs()` and `RunSummary` do not change. Nothing else in the freeze changes.
- **One runtime dependency: `joserfc>=1.8.0`** (1.8.0 locked; PyPI upload 2026-11-03, the lock's `upload-time`), added with `uv add joserfc`. The lower bound is the version uv picked, as for the other dependencies; no exact pin, because nothing here relies on one release's internals. joserfc is a JOSE library: HS256 sign and verify for our session and OAuth round-trip cookies, and RS256 verification of Google's ID token against Google's published key set (`joserfc.jwk.KeySet.import_key_set`). It requires `cryptography>=45.0.1`, and the lock adds exactly joserfc 1.8.0, cryptography 50.0.2, cffi 2.1.1 and pycparser 3.12 (`uv tree --package joserfc --no-dev`). The brief's default was a larger OAuth library (first entry under Alternatives considered). joserfc replaced it on 2026-11-16, on the orchestrator's ruling, for three reasons:
  - **The default is untyped; joserfc is typed.** The default ships no type information, and pyright checks `src/receipts/auth/` in strict mode with `# type: ignore` forbidden (ADR-0006), so its functions come through as partially unknown types, which strict mode reports as errors (measured under Alternatives considered). joserfc ships `py.typed` (`joserfc/py.typed` in the installed 1.8.0).
  - **The default's own JOSE module is deprecated.** Importing it prints a warning that tells users to switch to joserfc.
  - **joserfc is what the default uses itself.** The default declares `joserfc>=1.6.8` as a requirement, and the two packages have the same author and licence (BSD-3-Clause). Depending on joserfc directly keeps the JOSE code and drops the untyped, deprecated layer on top of it.
- **The OAuth 2.0 client side uses the standard library and `httpx`; no OAuth package.** PKCE uses the standard library: the verifier comes from `secrets`, and the S256 challenge is the base64url SHA-256 of the verifier, without padding (`hashlib`, `base64`). The authorization URL is built with `urllib.parse`. The token exchange and the fetch of Google's key set use `httpx`, already locked (0.28.1; eight packages in the lock list it as a dependency, among them gradio, huggingface-hub, langchain-core and litellm). joserfc adds no path to `requests`: `uv tree --invert --package requests --depth 1 --no-dev` lists the same five direct users before and after this change (langchain-keenable, langsmith, mellea, requests-toolbelt, tiktoken).
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

- **More packages.** The lock grows from 159 to 163 packages (`grep -c '^\[\[package\]\]' uv.lock`, at `6e59412` and after `uv add joserfc`): joserfc, cryptography, cffi and pycparser (`git diff 6e59412 -- uv.lock | grep '^+name = '`). No package already in the lock changes version (`git diff 6e59412 -- uv.lock | grep '^-version'` prints nothing). `uv lock --check` exits 0. `uv run pip-audit --strict --vulnerability-service osv`, the command in `.github/workflows/security.yml`, printed `No known vulnerabilities found` and exited 0 on the new lock (run 2026-11-16 01:25–01:26 UTC, 2026-11-15 in Miami). No `--ignore-vuln` was added (`grep -c ignore-vuln .github/workflows/security.yml` prints `0`).
- **Recent releases.** joserfc 1.8.0 reached PyPI on 2026-11-03, 13 days before it was locked, and cryptography sits on the sign-in path. The audit covers known advisories only, so an upgrade of joserfc or cryptography re-runs it before it merges.
- **New stored data.** For a person who signs in, the app stores their Google subject id (`sub`) and email address, nothing else from the profile. The section 9 data rule, the spec's non-goals and ADR-0004 change in the same PR (the `records` task).
- **No new gate exceptions.** Pyright stays strict on `src/receipts/auth/`, and no `--ignore-vuln` flag is added.

## Alternatives considered

- **Standard library only.** HMAC covers an HS256 cookie, but nothing in the standard library verifies Google's RS256 signature, so the ID token check would need a cryptography package anyway. Rejected.
- **`authlib` (the brief's default).** It would cover JOSE and the OAuth 2.0 and OpenID Connect client helpers in one install, but measured on 1.9.6 (2026-11-16): the wheel has no `py.typed` (0 such files in either copy of the 1.9.6 wheel in the local uv cache), and a strict pyright probe outside the repository reports `create_s256_code_challenge` as partially unknown (`reportUnknownVariableType`) while the `joserfc` lines in the same probe report nothing; `import authlib.jose` prints `AuthlibDeprecationWarning: authlib.jose module is deprecated, please use joserfc instead. It will be compatible before version 2.0.0.`; and its JOSE support is joserfc, which it requires (`joserfc>=1.6.8`). The OAuth helpers it adds (the PKCE challenge, the authorization URL, an httpx client) are a few lines of standard library and httpx, and it would put one more package in the lock (164 rather than 163). Rejected.
- **PyJWT.** It also covers JSON Web Tokens and RS256 through `cryptography`. It was not measured against this lock or strict pyright; joserfc was, and it reads a JWK Set directly (`joserfc.jwk.KeySet.import_key_set`). Not chosen.
- **Gradio's `auth_dependency` on the `/ui` mount.** In the locked gradio 6.32.0 a mount with `auth_dependency` answers 401 whenever the dependency returns `None`, which would turn every signed-out visitor away from `/ui`, the opposite of option (b) (the brief for #41 records the probe). Rejected.
