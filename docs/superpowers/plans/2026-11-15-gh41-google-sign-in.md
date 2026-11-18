# Plan: GitHub issue #41 — Sign in with Google, per-user History, per-user daily run limit

Brief: `docs/superpowers/briefs/2026-11-15-gh41-google-sign-in.md`. Standard: `AGENTS.md` (sections 2 to 6, 9). Format: the kit's `docs/plan-graph-format.md`. Written 2026-11-15 ~19:50 UTC by the orchestrator; **Final state (recorded 2026-11-18): approved 2026-11-16 01:06 UTC; every task terminal; merged to `main` as PR #52 (`949741f`, 2026-11-16 10:45:46 UTC).**

Base revision for every fact and every worktree: `origin/main` = `a9eeb61` (also the sha Render serves at `/healthz`, read by the main session at 19:40 UTC). Mellea (#46) and the verifier rules (#35) are merged, so the brief's sequencing condition is met. The ADR for this ticket is **0008** (`docs/adr/0007-mellea.md` exists on main).

## Shape

One ticket, one PR, nine tasks. The brief says the records "change in the same PR or the repo lies about what it stores", so the feature and its records land together. The brief's diff is well over the one-task size (new `auth/` package of eight modules, schema change, API scoping, UI seam, five new test files, eleven record files), so it is split into nine tasks that each fit one agent and one judge, stitched together on an **integration branch**:

- Integration branch `jay/gh-41-google-sign-in`, cut from `a9eeb61`, worktree `.worktrees/gh41`. Its first commit is the brief (as PRs #22 and #29 did). It becomes the single PR against `main`.
- Each task: worktree `.worktrees/gh41-<id>`, branch `jay/gh-41-<id>`, cut from the integration branch's head at dispatch. On a passing judge verdict the orchestrator merges the task branch into the integration branch (fast-forward when possible, else a plain merge; never a rebase of a pushed branch), and the task is `merged`. **This needs the owner's delegation (question 1 below).** Without it, each PASS waits for the owner to merge the task branch into the integration branch by hand.
- Dependent tasks are cut only after their dependencies are `merged`; they therefore see the judged contract, not a report of it.
- The final task (`records`) is judged on the **whole** integration-branch diff against `origin/main`, with the brief's full Verification list; that verdict is the PR's judge verdict. The owner opens or approves the PR after it.

Waves (a wave starts when every task it depends on is `merged`):

| Wave | Tasks | Why this order |
|---|---|---|
| A | `contract` | Produces every shared type, the `Gate` protocol, the five settings, the dependency, ADR-0008's first version. Everything else imports from it. |
| B | `oidc`, `limits`, `db`, `ui` (parallel, disjoint scopes) | Pure rules, persistence and the UI seam all consume only `contract`. |
| C | `provider` | Needs `oidc`'s `validate_claims`; the real provider wraps it with token exchange and signature verification. |
| D | `routes` | Needs `provider` (fake and real) and `db` (`SqlUserRepo`). |
| E | `wiring` | Needs `routes` (router to include), `limits` (`may_start`) and `db` (counts, `claim_run`). Also edits `api/app.py`, so it must land after nothing else touches that file. |
| F | `records` | Needs the final code so every record states what shipped. Judged on the whole PR. |

`ui` is in wave B, not E: it consumes only the `Gate` protocol from `contract`, is tested against a fake `Gate`, and reads the live one from `app.state.gate` (name fixed in `contract`). It can land before `wiring`; until `wiring` sets `app.state.gate`, `mount_ui` behaves exactly as today.

### Line numbers re-located on `a9eeb61`

The brief's citations come from `b8ed8d6`. On `a9eeb61`: `src/receipts/api/wiring.py` `_check_passcode` is at **288-294** (brief: 278-284) and `make_starter` at **297-314** with the demo-replay branch at **306-312** (brief: 296-302); `src/receipts/api/app.py` `create_app` 58-66 and the `app.state.run_starter` line at 64 (unchanged); `src/receipts/api/routes.py` `check_passcode` 37-43 (unchanged); `src/receipts/harness/service.py` `start` 72-78 (unchanged); spec lines 18 and 51 (unchanged); `README.md` passcode sentences at **22-23, 54, 140, 369-378, 390** and the environment table at **457-467** (brief: 54, 140, 319-340, 416). `uv.lock` has **159** `[[package]]` entries on `a9eeb61` (ADR-0007 recorded 118 → 159); `contract` records the count after adding the dependency.

### Conflict risks (flagged, not blocking)

- **PR #49 (`jay/gh-48-ui-test-gaps`, Mel, worktree `.worktrees/ui-gaps`)** changes `tests/test_ui_theme.py` and `tests/test_ui_render.py` only. The `ui` task's scope is `src/receipts/ui/**` and `tests/test_ui_app.py` only, so there is no file overlap. There is a **semantic** risk: #49's tests assert on `theme.py` (`HEADER_HTML`) and `render.py`; if `ui` edits those two files, #49's tests may go red once both are on `main`. Mitigation written into the `ui` dispatch: put the account line, sign-in link and logout form in `ui/app.py` as their own components; touch `theme.py`/`render.py` only if unavoidable, and if so stop and ask. Before the `records` judge, the integration branch merges `origin/main` (which will then contain #49 if merged) and re-runs the whole suite.
- **Other worktrees** (`claim-numbers`, `mellea`, `ui-status`, `ui-theme`, `voice-docs`, `voice-followup`, `w2`, `w3-credits`, `w3-readme`, `w3-records`) are merged or docs-only; none is touched by this plan.
- `src/receipts/api/wiring.py` and `pyproject.toml`/`uv.lock` were last changed by #46, already on `a9eeb61`; no open branch edits them.

### Decisions carried from the owner and the main session (do not re-ask)

Sign-in optional, passcode stays for signed-out visitors (option b). Settings in `settings.py` under ADR-0008. `users` table plus nullable `runs.user_id`. `SIGNED_OUT_RUNS_PER_DAY=20`. Deletion channel "by contacting the repository owner". README and runbook say only the owner can sign in while the OAuth app is in Testing mode.

### Limits for every agent (from the main session, 19:40 UTC)

No live runs against the deployed app. No paid model or Keenable calls except the brief's named acceptance steps. The Neon integration test may run with `DATABASE_URL` from `~/.zshenv`. Never print a secret value. No force-push; merge `origin/main` instead of rebasing a pushed branch. Three repair attempts, then escalate. Touch only the paths in your scope. Run `bin/jig` before reporting. Report the jig summary line verbatim.

`UNSET` below means `env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE`; the brief requires unit tests to run with the live names unset, and the implementer's shell has several of them from `~/.zshenv`.

## Human steps

| When | Who | Step |
|---|---|---|
| On approval of this plan | owner | Answer the questions below (or accept the defaults). |
| On approval | orchestrator | Create the integration branch and worktree from `a9eeb61`; commit the brief as its first commit; dispatch `contract`. |
| Before `ui` is judged, or at the latest before `records` | owner | Merge or close PR #49 so the integration branch can take `origin/main` with it. |
| After `records` PASS | owner | Open (or approve) the PR `jay/gh-41-google-sign-in` → `main`; merge after the five checks are green. |
| After the Render deploy | owner | The brief's last acceptance item: one real Google sign-in, one live run under that account visible signed in and not signed out, one signed-out passcode run visible signed out and not signed in, and `curl -fsS -D - https://receipts-h745.onrender.com/auth/me` answering 401 without a cookie. Recorded in the PR or the issue by the owner. |
| After the deploy | owner | Confirm on Neon that `runs.user_id` exists (the `records` task names the check in `docs/runbooks/render.md`). |

## Task graph

```toml plan-graph
[[task]]
id = "contract"
title = "Contract: joserfc dependency (coordinator ruling; was authlib) under ADR-0008 (first version), five Settings fields + docstring, test_settings NAMES = ten, auth/models.py (User, SessionUser, IdTokenClaims, StartDecision, AccountStatus, AuthError), auth/gate.py (Gate protocol; app.state.gate convention)"
scope = [
  "pyproject.toml",
  "uv.lock",
  "src/receipts/settings.py",
  "src/receipts/auth/__init__.py",
  "src/receipts/auth/models.py",
  "src/receipts/auth/gate.py",
  "tests/test_settings.py",
  "tests/test_auth_models.py",
  "docs/adr/0008-google-sign-in.md",
]
deps = []
parallel_safe = false
model = "opus"
exit = "uv lock --check && uv sync --frozen && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -i PATH=\"$PATH\" HOME=\"$HOME\" uv run python -c 'from receipts.api.app import create_app; create_app()' && uv run pip-audit --strict --vulnerability-service osv"
state = "merged"

[[task]]
id = "oidc"
title = "Pure OIDC and session: validate_claims, callback_url, authorization-URL builder, PKCE helpers (auth/oidc.py); signed session and round-trip cookies, 7 days / 10 minutes (auth/session.py); tests red first"
scope = [
  "src/receipts/auth/oidc.py",
  "src/receipts/auth/session.py",
  "tests/test_auth_oidc.py",
  "tests/test_auth_session.py",
]
deps = ["contract"]
parallel_safe = true
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_auth_oidc.py -q && env -u DATABASE_URL -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_auth_session.py -q"
state = "merged"

[[task]]
id = "limits"
title = "Pure start rule: may_start(user, passcode_ok, user_runs_today, signed_out_runs_today, per_user_limit, signed_out_cap) -> StartDecision with Rule Zero refusal text ('3 of 5 runs used today (UTC)'); the six-row table test red first"
scope = [
  "src/receipts/auth/limits.py",
  "tests/test_auth_limits.py",
]
deps = ["contract"]
parallel_safe = true
model = "sonnet"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_auth_limits.py -q"
state = "merged"

[[task]]
id = "db"
title = "Persistence: UserRow (sub UNIQUE NOT NULL, email NOT NULL, created_at) and nullable runs.user_id FK in schema.py; SqlRunRepo.claim_run / list_runs_for / count_runs_since; SqlUserRepo.get_or_create (db/users.py); create_schema adds user_id to an existing Postgres runs table (ADD COLUMN IF NOT EXISTS); test_db_users (SQLite) and two Neon constraint cases + claim_run round trip, red first"
scope = [
  "src/receipts/db/schema.py",
  "src/receipts/db/repo.py",
  "src/receipts/db/users.py",
  "src/receipts/db/__init__.py",
  "tests/test_db_users.py",
  "tests/test_db_constraints.py",
  "tests/test_db.py",
]
deps = ["contract"]
parallel_safe = true
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL uv run pytest tests/test_db_users.py -q && uv run pytest tests/test_db_constraints.py -q -m integration -rs"
state = "blocked"

[[task]]
id = "db-repair"
title = "db repair 1 of 3 (judge FAIL, same branch jay/gh-41-db): make test_a_claim_survives_the_later_save_run_and_save_battlecard call append_event and save_battlecard after the claim (sabotage of each must go red); give _assert_rejected a finally that deletes by id (LOW 3); tests only"
scope = [
  "tests/test_db_users.py",
  "tests/test_db_constraints.py",
]
deps = ["contract"]
parallel_safe = false
model = "sonnet"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL uv run pytest tests/test_db_users.py -q && uv run pytest tests/test_db_constraints.py -q -m integration -rs"
state = "merged"

[[task]]
id = "ui"
title = "UI seam: build_ui/mount_ui take a Gate from app.state.gate when present (fallback unchanged); account line ('0 of 5 runs used today (UTC)' or signed-out text), 'Sign in with Google' link hidden when sign-in is unavailable, logout form, passcode field hidden when signed in, History and Run panels go through the Gate; gr.Request -> Starlette request to gate.identify; no auth_dependency; # pyright: basic headers stay; tests red first"
scope = [
  "src/receipts/ui/**",
  "tests/test_ui_app.py",
]
deps = ["contract"]
parallel_safe = true
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u DEMO_PASSCODE uv run pytest tests/test_ui_app.py tests/test_ui_render.py tests/test_ui_theme.py -q && ! grep -rnE 'os\\.environ|getenv|get_settings|receipts\\.settings' src/receipts/ui/ && ! grep -rn auth_dependency src/"
state = "merged"

[[task]]
id = "provider"
title = "Identity provider edge: GoogleIdentityProvider protocol and the real one (token exchange over httpx, ID-token signature verification against Google's published keys, then validate_claims) in auth/provider.py; FakeIdentityProvider in auth/fake.py selected only by explicit injection; tests with a stubbed transport, no network, red first"
scope = [
  "src/receipts/auth/provider.py",
  "src/receipts/auth/fake.py",
  "tests/test_auth_provider.py",
]
deps = ["oidc"]
parallel_safe = true
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_auth_provider.py -q"
state = "merged"

[[task]]
id = "provider-pin"
title = "provider follow-up (judge MEDIUM accepted): add the kty-as-list case to REFUSED_KEY_SETS so the TypeError catch in _rsa_keys has a test that goes red when the catch is removed; optional empty-kid warm-cache case (LOW 3); tests only"
scope = [
  "tests/test_auth_provider.py",
]
deps = ["provider"]
parallel_safe = false
model = "sonnet"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_auth_provider.py -q"
state = "merged"

[[task]]
id = "routes"
title = "Auth routes: GET /auth/login (302 to Google with state, nonce, code_challenge, registered callback; 503 naming the missing variable), GET /auth/callback (state check, token exchange via the injected provider, SqlUserRepo.get_or_create, session cookie HttpOnly Secure SameSite=Lax Path=/), POST /auth/logout, GET /auth/me; provider and user repo read from app.state, never built at import; tests with FakeIdentityProvider + SQLite, red first"
scope = [
  "src/receipts/auth/routes.py",
  "tests/test_auth_routes.py",
]
deps = ["provider", "db-repair"]
parallel_safe = true
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_auth_routes.py -q"
state = "merged"

[[task]]
id = "routes-dbfail"
title = "routes follow-up (judge MEDIUM accepted): a database error while writing the users row in /auth/callback becomes 503 'from None' with the round-trip cookie cleared and no email or sub in any exception text or log; deleted-cookie attributes asserted on failure paths (LOW 2); docstring at routes.py:14-16 reworded"
scope = [
  "src/receipts/auth/routes.py",
  "tests/test_auth_routes.py",
]
deps = ["routes"]
parallel_safe = false
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_auth_routes.py -q"
state = "merged"

[[task]]
id = "wiring"
title = "Live wiring: the real Gate in api/wiring.py (identify from cookie; start = may_start with repo counts, passcode constant-time, require_keenable_key, claim_run after InProcessRunService.start; history = list_runs_for; account = AccountStatus), stored on app.state.gate in create_app before mount_ui; auth router included; GET /api/runs scoped by session cookie else NULL-user runs; POST /api/runs unchanged and counted as signed-out; demo mode uncounted; openapi.json regenerated; tests red first"
scope = [
  "src/receipts/api/app.py",
  "src/receipts/api/wiring.py",
  "src/receipts/api/routes.py",
  "src/receipts/api/models.py",
  "tests/test_api*.py",
  "tests/test_wiring.py",
  "tests/test_openapi_export.py",
  "docs/api/openapi.json",
]
deps = ["routes", "limits"]
parallel_safe = false
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_api_runs.py tests/test_wiring.py tests/test_ui_app.py tests/test_settings.py -q && uv run python scripts/export_openapi.py && git diff --exit-code docs/api/openapi.json && env -i PATH=\"$PATH\" HOME=\"$HOME\" uv run python -c 'from receipts.api.app import create_app; create_app()' && ! grep -rn auth_dependency src/"
state = "blocked"

[[task]]
id = "gate-docstring"
title = "Re-plan after ui exit 1: reword src/receipts/auth/gate.py:9 so the literal auth_dependency no longer appears in src/ (the brief's Verification 2 grep is the standard); docstring only"
scope = [
  "src/receipts/auth/gate.py",
]
deps = ["contract"]
parallel_safe = true
model = "sonnet"
exit = "! grep -rn auth_dependency src/ && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig"
state = "merged"

[[task]]
id = "wiring-repair"
title = "wiring repair 1 of 3 (judge FAIL, same branch jay/gh-41-wiring): HIGH, LiveGate.start must read the user row and treat a missing one as signed out (deleted user's cookie no longer bypasses passcode and cap); MEDIUM 2, tests for the half-configured start path the UI now uses (DEMO_PASSCODE set, live setting missing: passcode enforced, no live repo refusal); MEDIUM 3, merge the integration head into the branch and regenerate openapi.json; LOW 5, demo and half-configured account line shows the real cap (20), never '0 of 0'; LOW 4 docstring on two pools; LOW 6 dead patches"
scope = [
  "src/receipts/api/app.py",
  "src/receipts/api/wiring.py",
  "src/receipts/api/routes.py",
  "src/receipts/api/models.py",
  "tests/test_api*.py",
  "tests/test_wiring.py",
  "tests/test_openapi_export.py",
  "docs/api/openapi.json",
]
deps = ["routes-dbfail"]
parallel_safe = false
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest tests/test_api_runs.py tests/test_wiring.py tests/test_ui_app.py tests/test_settings.py -q && uv run python scripts/export_openapi.py && git diff --exit-code docs/api/openapi.json && env -i PATH=\"$PATH\" HOME=\"$HOME\" uv run python -c 'from receipts.api.app import create_app; create_app()' && ! grep -rn auth_dependency src/"
state = "merged"

[[task]]
id = "gate-docstring-2"
title = "gate.py docstring follow-up (wiring judge LOW 8): the refusal convention now says a missing key raises PermissionError naming the variable (the live Gate converts MissingSettingError); docstring only"
scope = [
  "src/receipts/auth/gate.py",
]
deps = ["wiring-repair"]
parallel_safe = false
model = "sonnet"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && ! grep -n MissingSettingError src/receipts/auth/gate.py"
state = "merged"

[[task]]
id = "records"
title = "Records on the final code: ADR-0008 completed (dependency, lifted files, 159 -> N packages, pip-audit result + date, signature-check choice, user_id column path, non-atomic count-then-claim, sub-second unclaimed window); ADR-0004 Google sign-in row + Neon sentence; ADR-0005 auth on the app's domain; ADR-0006 frozen-files line -> ADR-0008; AGENTS.md section 9 (Data bullet, L7 lane, Frozen line); spec lines 18 and 51; threat-model rows; runbook (env names, user_id column check, Testing-mode note); docs/api.md; README (passcode sentences 22-23, 54, 140, 369-378, 390; env table 457-467; who can sign in); brief committed; merge origin/main; whole-suite run with -rs"
scope = [
  "docs/adr/0008-google-sign-in.md",
  "docs/adr/0004-approved-ai-vendors.md",
  "docs/adr/0005-app-architecture-and-hosting.md",
  "docs/adr/0006-hackathon-gate-profile.md",
  "AGENTS.md",
  "docs/superpowers/specs/2026-11-14-receipts-design.md",
  "docs/security/threat-model.md",
  "docs/runbooks/render.md",
  "docs/api.md",
  "README.md",
  "docs/superpowers/briefs/2026-11-15-gh41-google-sign-in.md",
]
deps = ["wiring-repair", "ui", "routes-dbfail", "gate-docstring-2"]
parallel_safe = false
model = "opus"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE uv run pytest -q -m 'not integration' -rs && ! grep -n 'no accounts' AGENTS.md && ! grep -n 'user accounts' docs/superpowers/specs/2026-11-14-receipts-design.md && grep -q Google docs/adr/0004-approved-ai-vendors.md && ls docs/adr/0008-*.md && uv lock --check && grep -c ignore-vuln .github/workflows/security.yml | grep -qx 0"
state = "blocked"

[[task]]
id = "records-repair"
title = "records repair 1 of 3 (whole-PR judge FAIL, same branch jay/gh-41-records): ADR-0008 records the unique=True sabotage substitution (the duplicate-insert Neon test cannot go red once users_sub_key exists; test_users_unique_on_neon_matches_the_mapping is the guard; SQLite goes red via the concurrent-sign-in test); spec line ~50 no longer claims every constraint is proven on Neon or a dev branch and lists the real tables; the routes.py:14-15 docstring gap deferred in ADR-0008; records only"
scope = [
  "docs/adr/0008-google-sign-in.md",
  "docs/superpowers/specs/2026-11-14-receipts-design.md",
]
deps = ["wiring-repair", "ui", "routes-dbfail", "gate-docstring-2"]
parallel_safe = false
model = "sonnet"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && grep -q matches_the_mapping docs/adr/0008-google-sign-in.md && ! grep -n 'user accounts' docs/superpowers/specs/2026-11-14-receipts-design.md"
state = "blocked"

[[task]]
id = "records-repair-2"
title = "records repair 2 of 3 (re-judge FAIL on a sentence the first repair added): spec :50 Neon sentence narrowed to what the records support (same database as the deployed app, the one DATABASE_URL names; no dev branch in use; no count or name asserted); claim_run round trip described as column evidence not a rejected insert; users.id primary key added to the not-yet-proven list; ADR-0008:64 'row read or write'; ADR-0008:63 names its source runs; records only"
scope = [
  "docs/adr/0008-google-sign-in.md",
  "docs/superpowers/specs/2026-11-14-receipts-design.md",
]
deps = ["wiring-repair", "ui", "routes-dbfail", "gate-docstring-2"]
parallel_safe = false
model = "sonnet"
exit = "env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY -u GOOGLE_CLIENT_ID -u GOOGLE_CLIENT_SECRET -u SESSION_SECRET -u DEMO_PASSCODE bin/jig && grep -q matches_the_mapping docs/adr/0008-google-sign-in.md && ! grep -n 'user accounts' docs/superpowers/specs/2026-11-14-receipts-design.md && ! grep -n 'One Neon database' docs/superpowers/specs/2026-11-14-receipts-design.md"
state = "merged"
```

## Per-task dispatch notes and judge gates

Every dispatch carries the brief in full, this file's Shape, Limits and the task's TOML block, and the sentence: *"Touch only the paths in your scope. Run `bin/jig` before reporting. Report the jig summary line verbatim."* Every task also gets: *"Cut from the integration branch head; commit the failing test before the code that makes it pass, and name the red run (file, exit code, one line of the failure) in your report. Never print a value from the environment. If a frozen or forbidden path seems necessary, stop and ask."*

Each judge gets the brief, the task's block, `git diff <integration-head>...HEAD` for that task, and the rubric below; its verdict goes to `docs/superpowers/plans/verdicts/2026-11-15-gh41-<id>.md`. A PASS moves the task to `merged` (after the merge into the integration branch); a FAIL moves it to `blocked` and the fix is re-planned as `<id>-repair` (attempt 1 of 3).

- **`contract`** — The only task that touches the three ADR-0008-lifted files; it writes ADR-0008's first version before editing them (dependency `joserfc` per the coordinator ruling below, originally `authlib`; why one dependency covers JOSE for the cookie and the ID token; lifted files; `uv.lock` 159 → N; `pip-audit` result with date). Token exchange uses `httpx`, already locked; no `requests`. `tests/test_settings.py::NAMES` grows to ten; `empty_env` and the construct test cover the new defaults (`runs_per_user_per_day == 5`, `signed_out_runs_per_day == 20`). `gate.py` documents the `app.state.gate` attribute name that `ui` and `wiring` both use, and the `Gate` methods from the brief (`identify`, `start`, `history`, `account`). `tests/test_auth_models.py` is a small frozen-model test (new file; `tests/test_auth*.py` is in the brief's Allowed list). **Judge:** brief Verification 1 (settings diff shows only five fields and the docstring; `pyproject.toml` adds exactly one runtime dependency, the one ADR-0008 names); `uv lock --check` 0; `pip-audit` 0 with no `--ignore-vuln`; empty-environment boot 0; sabotage "make `create_app()` call `get_settings()`" turns `test_create_app_boots_with_an_empty_environment` red — **note from the implementer at `039f346`, to be confirmed by the judge:** with all ten settings optional, `get_settings()` succeeds in an empty environment, so the original test could not go red on this sabotage; the implementer tightened the test (commit `4b12f02`) to assert `get_settings`'s cache is still empty after `create_app()`, and the judge must run the real sabotage in `api/app.py` to see that tightened test red; no `# type: ignore`; pyright strict on `src/receipts/auth/`.
- **`oidc`** — JOSE through `joserfc` (coordinator ruling above); PKCE with `secrets`/`hashlib`/`base64`; the authorization URL with `urllib.parse`. Pure: no clock (`now` is a parameter), no network, no database. `AuthError` names the failed check. `callback_url` returns exactly the two registered URIs for `localhost:8000`/`127.0.0.1` and `receipts-h745.onrender.com`. Session constants: 7 days and 10 minutes, in `session.py`, not settings. The cookie carries the internal user id and expiry only. **Judge:** Verification 4 sabotages a–d, each separately (nonce dropped → red; `aud == client_id` → `True` → red; `exp` check dropped or `>=` with `exp == now` → red; verifier ignores the signature → tampered-cookie case red); Verification 3 on `get_secret_value()` hits; no email or token in any cookie payload.
- **`limits`** — The six-row table from the brief's `test_auth_limits.py` bullet, as a parametrised test. Refusal text carries count, denominator and window: `5 of 5 runs used today (UTC)`, `20 of 20 ...`, and says the limit resets at 00:00 UTC. A signed-in user is never counted against the signed-out cap and the reverse. A correct passcode does not make a signed-in user. **Judge:** sabotage e (`allowed` unconditionally → `5 of 5` and `20 of 20` cases red); `grep -n "limit reached"` prints nothing; purity (no imports of settings, db, datetime.now).
- **`db`** — `create_schema` keeps `Base.metadata.create_all` (adds `users`) and, on the Postgres dialect only, runs an idempotent `ALTER TABLE runs ADD COLUMN IF NOT EXISTS user_id ...` with the FK, because `create_all` never adds a column to an existing table and SQLite does not support `IF NOT EXISTS` on `ADD COLUMN` (SQLite gets the column from `create_all` on a fresh file). `tests/test_db_constraints.py` adds, in the `_assert_rejected` style: duplicate `users.sub` rejected with zero leftover rows; `runs.user_id` naming no user rejected; one `claim_run` round trip proving the column exists on Neon, with the row deleted in a `finally`. All identities synthetic (`fake-sub-0001`, `*@example.com`). The frozen `RunRepo.list_runs()` and `RunSummary` do not change. **Judge:** sabotage f (drop the `user_id` filter in `list_runs_for` → `test_db_users.py` red) and h (`unique=True` off `UserRow.sub` → Neon case red; SQLite cannot prove this); the integration run with `-rs` reports zero skips when `DATABASE_URL` is set and names the skip when it is not; `SELECT count(*)` of test rows left on Neon is 0. **See question 2** on which database the integration run may touch.
- **`ui`** — Mitigation for PR #49 (Conflict risks above): new components live in `ui/app.py`; `theme.py` and `render.py` untouched unless unavoidable (then stop and ask). Handlers that need identity take `gr.Request` and pass `request.request` (Starlette) to `gate.identify`. With no `Gate` on `app.state`, behaviour is today's (`test_mount_ui_on_a_bare_app_falls_back_to_the_demo_service` stays green and so do `tests/test_ui_render.py` and `tests/test_ui_theme.py`, which the task runs but does not edit). Account line text after sign-in: `0 of 5 runs used today (UTC)`; signed out: the passcode field shows and the sign-in link shows only when `gate.account(None)` says sign-in is available. **Judge:** Verification 2 (`grep -rnE "os\.environ|getenv|get_settings|receipts\.settings" src/receipts/ui/` empty; `grep -rn auth_dependency src/` empty); every `src/receipts/ui/*.py` starts with `# pyright: basic`; a test with a fake `Gate` shows the passcode field hidden when signed in and present when signed out; a test proves the `Gate` is read from `app.state.gate`.
- **`provider`** — Token exchange and the JWKS fetch over `httpx`; signature verification with `joserfc` (coordinator ruling above). **Carried from `oidc`:** joserfc 1.8.0 raises `TypeError` (not its own error) on some malformed JWS headers (`crit` not a list; header a JSON list) before any signature check, so the provider's decode must catch `TypeError` as `session._verify` does; `IdTokenClaims` has no `email_verified` field (records to note). The real provider verifies the ID token's signature against Google's published keys (JWKS) before `validate_claims`; skipping it is a Do-not item unless ADR-0008 records the choice. Unit tests use a stubbed `httpx` transport (`httpx.MockTransport`) and a locally generated RSA key pair for the JWKS; no network. `FakeIdentityProvider` is chosen only by injection, never by an environment variable. **Judge:** Verification 3 (`get_secret_value()` only inside the token-exchange call); a test where the ID token is signed by a different key fails verification; no log line prints a token, a code or an email; `grep -rn "os.environ\|getenv" src/receipts/auth/provider.py src/receipts/auth/fake.py` empty.
- **`routes`** — The router reads its provider and `SqlUserRepo` from `app.state` (set by `wiring`, or by the test) and `get_settings()` per request; nothing is built at import. `GET /auth/login` is 503 naming the first missing one of `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`, `DATABASE_URL`, never a value. State compared for equality with the round-trip cookie, not for presence. **Carried from the `oidc` judge:** `session.sign_*` raises `ValueError` on an empty secret, so the 503 availability check runs before any signing; `now` must be timezone-aware; a request whose host is `127.0.0.1` is redirected to `localhost:8000` before the round-trip cookie is set (the cookie is host-only and `callback_url` maps both to `localhost`), or the runbook says to start local sign-in at `localhost:8000`. Tests: the full `test_auth_routes.py` bullet of the brief (`1 of 1` rows on a second sign-in; cookie flags; 401/200 on `/auth/me`; 400 and no cookie on a wrong `state`). **Carried from the `provider` judge:** `exchange` hands back unvalidated claims of the same type `validate_claims` returns, so tests must show that fake claims with a wrong nonce, a wrong `aud` and an expired `exp` each set no cookie and write no `users` row (then a route that skips `validate_claims` goes red); `FakeIdentityProvider.claims_by_code` is mutable so a test can register the code once the login redirect has produced the nonce; build the provider only after the 503 check (`google_client_secret` may be `None`). **Judge:** each listed case present and red-first recorded; the 503 detail contains the variable name and no value; `Set-Cookie` carries `HttpOnly; Secure; SameSite=Lax; Path=/`; the cookie payload decodes to user id and expiry only.
- **`wiring`** — The live `Gate` is built lazily like `LazyRunService` (nothing in `create_app()` reads settings); `start` order: identify → `may_start` (passcode constant-time as `_check_passcode` at `wiring.py:288-294`) → `require_keenable_key` → `service.start` → `claim_run` (the brief's accepted sub-second unclaimed window). Demo mode (`make_starter`'s branch at 306-312) stays passcode-free and uncounted. `POST /api/runs` keeps `X-Demo-Passcode` and now counts against `SIGNED_OUT_RUNS_PER_DAY`; `GET /api/runs` lists the session user's runs when a valid cookie is present, else NULL-user runs; `GET /api/runs/{run_id}` unchanged. `scripts/seed_demo_runs.py` is forbidden and must keep working. `docs/api/openapi.json` regenerated by `scripts/export_openapi.py`. Keep `app.state.run_starter` for the UI's fallback path (`ui` still reads it when no `Gate` is set). **Carried from `ui`:** (i) `tests/test_wiring.py::test_create_app_injects_the_starter_into_the_ui` spies `build_ui(service, starter=None)`; once `create_app()` sets `app.state.gate`, `mount_ui` calls `build_ui(service, starter=starter, gate=gate)` and that spy raises `TypeError` — update it; (ii) the UI cannot import `receipts.settings`, so it recognises `MissingSettingError` by class name; prefer the live `Gate.start` raising `PermissionError` for a missing key too, or have `receipts.auth` re-export the error (the latter is `auth/__init__.py`, outside wiring's scope, so pick the former unless a stop-and-ask is cheaper). **`ui` judge LOW 8:** the `RunId` returned by `Gate.start` must come from the same service the UI follows for events (`app.state.run_service`); `wiring`'s test covers it. **Judge:** Verification 2 and 3; `test_api_runs.py` gains the two scoping cases and sabotage f turns the API case red; `/healthz` body and header unchanged; `test_create_app_boots_with_an_empty_environment` green under `UNSET`; a signed-in start does not increment the signed-out count (test); **carried from the `limits` judge:** a test at the call site proves `user_runs_today` and `signed_out_runs_today` reach `may_start` in the right slots (they are two adjacent positional ints).
- **`records`** — Edits where the lines stand, no footnotes (the brief's Do-not). Only the owner can sign in while the OAuth app is in Testing mode (README and runbook). Deletion channel: "by contacting the repository owner". The AGENTS.md section 9 Data bullet reads in substance as the brief's last Assumption; `grep -n "no accounts" AGENTS.md` prints nothing. ADR-0008 is completed with the facts from `contract` (package counts, `pip-audit` date) and from `db`/`provider` (column path, signature check). Before its judge, the integration branch merges `origin/main` (never rebases). **Judge (whole PR):** `git diff --name-only origin/main...HEAD | sort` every path in Allowed and none in Forbidden; Verification 1, 2, 3, 5 (whole suite with `-rs`, every skip named, no new file skips; then each new test file alone) and 7; the PR body's numbers carry their set; Verification 6 (a real Google sign-in in a local boot) is the **owner's** step, not the judge's, since only the owner can sign in.

## Approval and answers (owner, 2026-11-16 01:06 UTC, relayed by the main session, Claude Code session `477932e0`)

Plan **approved**. Answers: (1) intra-branch merges **delegated** to the orchestrator (ff or plain merge on each task's judge PASS; never rebase or force-push); the final PR to `main` still needs the whole-PR judge PASS plus green CI, and the main session merges it. (2) Neon option **(a) accepted**: the `db` integration test may run against the live `DATABASE_URL` from `~/.zshenv`; additive changes only (create `users`, add nullable `runs.user_id`), nothing existing altered or dropped, test rows deleted, URL never printed. (3) `ui` starts **now**; the integration branch merges `origin/main` before the `records` judge. Reporting rule: when a wave finishes or a task escalates, report to "main" with task ids, verdict paths and the integration head sha; do not wait on the main session between delegated merges.

Dispatch log: `origin/main` re-checked at dispatch, still `a9eeb61`. Integration branch `jay/gh-41-google-sign-in` created in `.worktrees/gh41` from `a9eeb61`; first commit `6e59412` (the brief). `contract` cut from `6e59412`.

## Interruption and resume (2026-11-16 05:11 UTC, read from `date -u`)

The orchestrator hit the API usage limit around 04:4x UTC. Casualties, read from the worktrees at 05:11 UTC: the `routes-dbfail` judge died before writing a verdict (no file; re-dispatched, not counted as a FAIL or a repair attempt); the `wiring` implementer died before its first commit (`.worktrees/gh41-wiring` clean at `bdbf418`; re-dispatched with the same brief). The `routes-dbfail` branch itself is intact at `2c13cc5`. **Clock correction:** every "~HH:MM UTC" stamp written before this section was an estimate, not a clock reading, and ran ahead of real time by up to about 90 minutes (the row that says "~06:05 UTC" was written before 04:45 UTC). Stamps from here on are read from `date -u`. Order of events and the sha chain are unaffected.

## Coordinator rulings

### 2026-11-16 01:3x UTC — the one dependency is `joserfc`, not `authlib`

Raised by the `contract` implementer at `039f346`; verified by the orchestrator in `.worktrees/gh41-contract`: `authlib` 1.9.6 ships no `py.typed` (pyright strict on `src/receipts/auth/` would report unknown types with no `# type: ignore` allowed), `import authlib.jose` prints `AuthlibDeprecationWarning: authlib.jose module is deprecated, please use joserfc instead`, and `joserfc` (typed, `py.typed` present) is authlib's own dependency in the lock. The brief says "`authlib` unless ADR-0008 justifies another". Ruling: the single runtime dependency is **`joserfc`** (HS256 for our cookies; RS256 + JWKS for Google's ID token). PKCE (`secrets`, `hashlib`, `base64`) and the authorization URL (`urllib.parse`) use the standard library; the token exchange and the JWKS fetch use `httpx`, already locked. `contract` applies this on its own branch before its judge (`uv remove authlib`, `uv add joserfc`, ADR-0008 Decision rewritten with the reason above, lock count re-recorded). Binding for `oidc`, `provider` and `records`.

### 2026-11-16 03:50 UTC — `httpx` stays undeclared; ADR-0008 records how it is reached

Raised by the `provider` implementer: `provider.py` is the first `src/` module to import `httpx`, which `pyproject.toml:33` lists only in the dev group. Verified by the orchestrator: `uv tree --invert --package httpx --no-dev` shows httpx 0.28.1 reached at runtime through 8 locked packages (gradio, gradio-client, huggingface-hub, langchain-core, langgraph-sdk, litellm, ollama, safehttpx). Ruling: not declared as a direct dependency (the brief's Verification 1 allows exactly one added runtime dependency, `joserfc`, and declaring httpx adds no package); **`records`** adds one sentence to ADR-0008 naming the eight parents and the risk (if every parent dropped httpx, the image would break at import of `receipts.auth.provider`). The owner may reverse this in a later PR by declaring `httpx`.

### 2026-11-16 01:3x UTC — `Gate.start` refusal convention (from `contract`'s `gate.py` docstring)

A refusal raises `PermissionError` whose message is `StartDecision.reason`; a missing key raises `MissingSettingError`; the live `Gate` is on `app.state.gate`. Binding for `ui`, `limits` (reason text) and `wiring`.

## Questions for the owner (answered above; kept for the record)

1. **Integration branch and delegated merges.** The plan uses one integration branch (`jay/gh-41-google-sign-in`) so #41 lands as one PR, and the orchestrator merges each task branch into it after that task's judge PASS (fast-forward or plain merge; no rebase, no force-push). Do you delegate those nine intra-branch merges to the orchestrator, as you delegated PR merges on 2026-11-14? If not, each PASS waits for you, and the critical path (A → B → C → D → E → F, six sequential waves) stalls at each step. Alternative if you prefer: stacked PRs per task against `main`; that costs six approval clicks on a strict up-to-date ruleset and the records would land after the code, which the brief forbids.
2. **Which Neon database the `db` integration test may change.** `DATABASE_URL` in `~/.zshenv` is the deployed app's database (the W1 plan recorded "tests hit the demo DB, not a `dev` branch", accepted by the coordinator). Running `create_schema` from the `db` worktree will create the `users` table and add the nullable `runs.user_id` column on **production Neon before the code is deployed**. The deployed `a9eeb61` never names that column, so its inserts and selects keep working, and the test deletes every row it writes. Options: (a) accept, as the W1 constraint tests did; (b) create a Neon branch and point the test run at it with a separate URL (adds an owner step and a second connection string in `~/.zshenv`, name only). Default if unanswered: (a).
3. **PR #49 ordering.** The `ui` task avoids #49's two files, but both touch the UI. Merge #49 first (then `ui` cuts from a `main` that contains it), or let `ui` start now and take `origin/main` before its judge? Default if unanswered: start `ui` now; merge `origin/main` before the `records` judge.

## Resume

A new session reads this file, runs `bin/plan-check docs/superpowers/plans/2026-11-15-gh41-google-sign-in.md --ready`, and proceeds with what it lists. State changes are written here before any dispatch. `stop`: every `running` task goes to `blocked` and its worktree is listed here.

## Final state (2026-11-16 10:14 UTC, read from the head `dd3c10a` in `.worktrees/gh41` by the orchestrator, exit codes captured directly)

- `bin/jig` (live names unset): exit 0, 4 of 4 rows `ok`. `uv run pytest -q -m "not integration" -rs`: exit 0, **687 passed, 14 deselected, 0 skipped** of 701 collected (the 14 deselected are the `integration` marker: 12 `test_db_constraints.py`, 1 `test_db.py`, 1 `test_integration_live.py`).
- Neon: `uv run pytest tests/test_db_constraints.py -q -m integration -rs --tb=short` exit 0, **12 passed of 12, 0 skipped**; output screened, 0 lines matching a connection-string pattern.
- `uv lock --check` exit 0; lock **159 → 163** packages (`cffi`, `cryptography`, `joserfc`, `pycparser`; 0 existing versions changed). `uv run pip-audit --strict --vulnerability-service osv` exit 0, `No known vulnerabilities found`; `grep -c ignore-vuln .github/workflows/security.yml` = 0. `scripts/export_openapi.py && git diff --exit-code docs/api/openapi.json` exit 0.
- Live Neon catalogue (read-only, URL never printed): tables `runs`, `users`; `runs.user_id` `character varying(64)`, nullable; FK `runs_user_id_fkey`; `users_sub_key` UNIQUE; index `ix_runs_user_id`. Counts: `runs` 3, `users` 0, `runs where user_id is not null` 0, `constraint-test-%` 0. The column and table reached Neon through `create_schema` run by the `db` task's integration test on 2026-11-16 under the owner's answer (a) (additive DDL: `CREATE TABLE users`, `ALTER TABLE runs ADD COLUMN IF NOT EXISTS user_id VARCHAR(64) REFERENCES users(id)`, `CREATE INDEX IF NOT EXISTS ix_runs_user_id`); the deployed `a9eeb61` code keeps working on the altered table (the `db` judge ran `test_neon_round_trip` against it).
- Branch: 66 commits over `origin/main` `c5d0114`, 9 merges, 45 files; all 45 in the brief's Allowed list, 0 Forbidden. Not pushed; no PR opened (the main session does both).
- 17 tasks: 12 PASS and merged; 4 FAIL (`db`, `wiring`, `records`, `records-repair`) each repaired within the three-attempt rule (`db` 1 of 3, `wiring` 1 of 3, `records` 2 of 3); 0 escalations; 1 API interruption with no lost work.

## Verdicts and PRs

| Task | State | Branch / worktree | Judge verdict |
|---|---|---|---|
| contract | **merged** ~01:50 UTC: ff into the integration branch, head `1e7b0a5` (9 commits). Judge PASS: 0 HIGH, 1 MEDIUM accepted (no test that `google_client_secret`/`session_secret` are `SecretStr`; pyright strict catches misuse; **carried to `oidc`**: add the assertion in `tests/test_auth_session.py`), 6 LOW carried: `.strip()` in `StartDecision.refuse` untested (`models.py:71`); boot test proves only that `get_settings()` was not called, docstring and ADR-0008:27 overclaim (**`records`** narrows the ADR sentence); ADR-0008:22 says authlib is the "first" Alternatives entry, it is the second (**`records`**); ADR-0008:41 placeholder says "whether" the provider checks the signature, ruling settled it as "how" (**`records`**); the nine model sabotages are unlisted (PR body); plan title/notes said authlib (fixed). Exit 0, jig 4 of 4 ok, pip-audit clean, 352 passed / 9 deselected / 0 skipped of 361, sabotages a–e all red. | `jay/gh-41-contract` / `.worktrees/gh41-contract` | PASS `verdicts/2026-11-15-gh41-contract.md` |
| oidc | **merged** ~03:12 UTC into the integration branch (merge commit, head `fd2f166`). Judge PASS: 0 HIGH, 0 MEDIUM, 6 LOW carried: HS256-pin removal unobservable on joserfc 1.8.0 (a widened list is caught by the `hs512-our-secret` case; PR body); `OAuthRoundTrip` lives in `oidc.py` not `models.py` (**`records`**: name it in ADR-0008's shared-types list); docstring overclaims "no exception escapes" (naive `now` raises `TypeError`; PR body or a later pass); **for `routes`:** `callback_url("127.0.0.1:8000")` → `localhost`, and the host-only round-trip cookie would be lost, so redirect `127.0.0.1` to `localhost` before `/auth/login` or the runbook says start at `localhost:8000`; second-red message was 2 of 4 `'bool' object is not iterable` + 2 of 4 `list indices...`; fuzz counts uncommitted (PR body labels them). 32 of 33 sabotages red (the 33rd is the pin, LOW 1); 458 passed / 9 deselected / 0 skipped of 467. | `jay/gh-41-oidc` / `.worktrees/gh41-oidc` | PASS `verdicts/2026-11-15-gh41-oidc.md` |
| limits | **merged** ~02:15 UTC: ff into the integration branch, head `ec772dc`. Judge PASS: 0 HIGH, 1 MEDIUM accepted (the rubric's `limit reached` grep hits the test's own negative assertion at `tests/test_auth_limits.py:62`; `limits.py` has no hit), 2 LOW carried: counts are positional ints, a swapped call site would type-check (**`wiring`** must test that each count reaches its slot; optionally keyword-only); second parametrize lacks ids (PR body). 11 of 11 sabotages red; 368 passed / 9 deselected / 0 skipped. | `jay/gh-41-limits` / `.worktrees/gh41-limits` | PASS `verdicts/2026-11-15-gh41-limits.md` |
| db | **blocked** ~03:05 UTC — judge FAIL: 0 HIGH, 1 MEDIUM not accepted (`tests/test_db_users.py:172-181` `test_a_claim_survives_the_later_save_run_and_save_battlecard` never calls `save_battlecard` or `append_event`; sabotaging either to clear `user_id` left 29 of 29 green; the code is correct, the test overclaims), 5 LOW: commit message said 3 `UndefinedColumn` failures, judge saw 2 + 1 `AssertionError`; `_assert_rejected` has no `finally` (`test_db_constraints.py:112-120`); a failing Neon test prints the engine repr with user and host, password masked (pre-existing at base; **`records`/runbook note**); `ALTER` text duplicates the mapping; `users` NOT NULLs untested on Neon. Passed: scope, freeze (contracts/fakes/conftest 0 bytes), exit 0, 13 of 13 + 12 of 12 on Neon, 365/14/0, Neon counts unchanged before/after (runs 3, users 0), catalogue shows one FK, one index, `users_sub_key`; sabotage (e) cannot go red on Neon (column exists) so the judge proved it on a throwaway local Postgres 15: 3 of 12 red. Re-planned as `db-repair` (attempt 1 of 3). **→ Final:** superseded by `db-repair` (same branch), re-judge PASS `verdicts/2026-11-15-gh41-db-repair.md`, merged into the integration branch at `9a942a1`. | `jay/gh-41-db` / `.worktrees/gh41-db` | FAIL `verdicts/2026-11-15-gh41-db.md` |
| db-repair | **merged** ~03:40 UTC into the integration branch (head `9a942a1`; brings the whole `jay/gh-41-db` branch: schema, repo, users, tests). Re-judge PASS: previous MEDIUM resolved (three harness writes each red at its own checkpoint `tests/test_db_users.py:185`, `:196`, `:210`), LOW 3 resolved by behaviour (FK-off SQLite: old helper left 1 of 1 rows, new 0 of 0). 1 new LOW (red-run record lacks test name and exit codes; PR body), 4 carried LOWs (**`records`/PR body:** commit body says 3 `UndefinedColumn`, it was 2 + 1 assertion; engine repr shows user and host on failure; DDL restates the mapping, drift check covers `users` UNIQUE only; `users` NOT NULLs untested on Neon). Neon counts unchanged before/after (runs 3, users 0, all test patterns 0); 365 passed / 14 deselected / 0 skipped. | `jay/gh-41-db` / `.worktrees/gh41-db` | PASS `verdicts/2026-11-15-gh41-db-repair.md` |
| ui | **merged** ~03:30 UTC into the integration branch (head `5b94add`). Judge PASS: 0 HIGH, 0 MEDIUM, 8 LOW carried: `MissingSettingError` matched by class name (**`wiring`**: raise `PermissionError` for a missing key from the live Gate, then the UI drops `_is_missing_setting`); recount fires on early return too (harmless); `/ui/gradio_api/run/account` shows the email to the cookie holder like `/auth/me` (**`records`**: threat model or ADR-0008); Gradio's `dict[str, Any]` in `gr.update` return types (basic mode); no test pins the no-Gate component set (sabotage m stayed green, 1 of 15); `login_check` unasserted (probe 200); commit `a598c93` lists no sabotages (PR body); **`wiring` judge:** the `RunId` from `gate.start` must belong to `app.state.run_service`, which the UI follows for events. 14 of 15 sabotages red incl. h2 (auth hook without the literal → 6 red); option (b) probed: 200 on `/ui`, `/ui/`, `/ui/config`, `login_check` with no Gate and with a signed-out Gate, 401 control. 387 passed / 9 deselected / 0 skipped. | `jay/gh-41-ui` / `.worktrees/gh41-ui` | PASS `verdicts/2026-11-15-gh41-ui.md` |
| provider | **merged** ~04:25 UTC into the integration branch (head `7f72a15`). Judge PASS: 0 HIGH, 1 MEDIUM accepted (`TypeError` catch in `_rsa_keys` at `provider.py:192` untested: a JWKS key with `kty: ["RSA"]` makes joserfc raise a bare `TypeError`; fails closed; **`provider-pin`** adds the case), 10 LOW: pin removal/HS256 widening unobservable on joserfc 1.8.0 with an RSA-only key set (PR body); `_Header.kid: NonEmpty` untested (`provider-pin`, optional); sabotage record partly unverifiable, commit title says four pinned, 3 of 4 true (PR body); "57 failed" only for the `async with` form, 5 for `aclose` (PR body); green commit re-wrapped 3 test lines, AST identical (PR body); **`routes`:** `exchange` returns the same type as `validate_claims`, so tests must show wrong nonce / wrong aud / expired exp each set no cookie and write no `users` row; **`wiring`/`records`:** per-request vs per-process provider (cache has no expiry) recorded in ADR-0008; **`records`:** httpx sentence (8 parents), `email_verified` dropped, protocol is `IdentityProvider` + real `GoogleIdentityProvider`. 34 of 38 sabotages red (greens: b, c pin; g2 the MEDIUM; u kid). 541 passed / 9 deselected / 0 skipped of 550; network-off plugin: 0 blocked attempts. | `jay/gh-41-provider` / `.worktrees/gh41-provider` | PASS `verdicts/2026-11-15-gh41-provider.md` |
| provider-pin | **merged** ~05:00 UTC into the integration branch (head `0ebc6ef`). Judge PASS, 0 findings: both sabotages red by test id (`_rsa_keys` catch → `[key-type-as-a-list]`; `kid: str` → `test_an_empty_kid_is_rejected_without_a_refetch`); 69 of 69. Closes the `provider` verdict's accepted MEDIUM and LOW 3. | `jay/gh-41-provider-pin` / `.worktrees/gh41-provider-pin` | PASS `verdicts/2026-11-15-gh41-provider-pin.md` |
| routes | **merged** ~05:35 UTC into the integration branch (head `bdbf418`). Judge PASS: 0 HIGH, 1 MEDIUM accepted and carried (a DB failure during `get_or_create` → 500 whose exception text carries email and `sub`, logged by uvicorn; round-trip cookie not cleared on that path; `routes.py:273-274`; **`routes-dbfail`**), 4 LOW: deleted-cookie attributes unchecked on failure paths (sabotage `hh` green, 1 of 44; `routes-dbfail`); `get_secret_value()` blank check at `:135` accepted as practised at `wiring.py:103` and `api/routes.py:40` (**`records`/PR body** states Verification 3 as practised); "38 of 38" unlistable (PR body); consent-screen cancel gives raw JSON 400 (optional later). Required sabotages a–n 14 of 14 red; 43 of 44 overall; provider finding 7 proven (wrong nonce/aud/exp/iss → 400, no cookie, 0 rows); import hygiene `0` and `False False`; 0 network attempts under a socket guard. 639 passed / 14 deselected / 0 skipped of 653. | `jay/gh-41-routes` / `.worktrees/gh41-routes` | PASS `verdicts/2026-11-15-gh41-routes.md` |
| routes-dbfail | **merged** 05:20 UTC into the integration branch (head `2c13cc5`). Judge PASS: 0 HIGH, 0 MEDIUM, 2 LOW carried to **`records`**/PR body: docstring `routes.py:14-15` names less than the code covers (the `except` also wraps repo construction and `create_schema`; reword to "a database error from the users store (building it, its schema, or the row)"); the "6 of 6" extra sabotages unlisted. Required sabotages 5 of 5 red (path-`/auth` sabotage 9 of 68 red, was 0 of 66 before), extras 7 of 7 red; the `raise ... from None` alternative would have left the round-trip cookie in place (red at `tests/test_auth_routes.py:579`). Note for a later pass: `make_engine` has no `hide_parameters`, so a DB error in `/auth/me` is still a 500 carrying only our user id (within brief:15). 643 passed / 14 deselected / 0 skipped of 657. | `jay/gh-41-routes-dbfail` / `.worktrees/gh41-routes-dbfail` | PASS `verdicts/2026-11-15-gh41-routes-dbfail.md` |
| wiring | **blocked** 05:56 UTC — judge FAIL: 1 HIGH (`wiring.py:469-481` + `routes.py:209-212`: `identify` trusts the cookie without reading the row; a deleted user's valid cookie is treated as signed in with count 0, the run starts, `claim_run` then fails on the FK on Postgres, so the person gets uncapped passcode-free runs for up to 7 days; probe on FK-on SQLite: 4 of 4 attempts started; `account` already treats this as signed out, `start` does not), 2 MEDIUM (the half-configured start path the UI now uses has no test — two sabotages stayed green on 674 of 674; the merged tree `2c13cc5`+`6df1b7f` fails `test_openapi_export` because `routes-dbfail` changed the callback 503 description), 6 LOW (two pools persist until restart, docstring at `wiring.py:50-51` overclaims; **Rule Zero:** demo/half-configured account line says `0 of 0 signed-out runs` where the cap is 20; dead patches at `tests/test_wiring.py:987-991`; `wiring.py:58` cites ADR-0008 for the per-process provider before ADR-0008 says it (`records`); `gate.py:34-35` stale on `MissingSettingError` (`records`); exit command has six clauses, not seven). Passed: scope 7 of 7, frozen diff 0 bytes, exit 0 on all clauses, 674/14/0, pyright 0, empty-env boot 0 with cache size 0, V3 clean, red-first reproduced (19 failed + 13 errors), passcode tests 22 of 22, seed script unchanged, 32 of 34 sabotages red (23 of 23 required). Re-planned as `wiring-repair` (attempt 1 of 3). **→ Final:** superseded by `wiring-repair` (same branch), re-judge PASS `verdicts/2026-11-15-gh41-wiring-repair.md`, merged at `e5435b7`. | `jay/gh-41-wiring` / `.worktrees/gh41-wiring` | FAIL `verdicts/2026-11-15-gh41-wiring.md` |
| gate-docstring | **merged** ~02:57 UTC into the integration branch, head `528e450`. Judge PASS, 0 findings (sonnet judge could not write the file; the orchestrator transcribed its hand-back verbatim). | `jay/gh-41-gate-docstring` / `.worktrees/gh41-gate-docstring` | PASS `verdicts/2026-11-15-gh41-gate-docstring.md` (transcribed) |
| wiring-repair | **merged** 06:23 UTC: ff of `jay/gh-41-wiring` to `e5435b7`, then `origin/main` `c5d0114` (#51, docs only, no overlap) merged → integration head `3253fe2`. Re-judge PASS: HIGH 1, MEDIUM 2, MEDIUM 3 resolved (row check sabotages 4/6/3/1 of 92 red; previous probe now starts 0 of 4; the two half-configured sabotages now 5 of 687 red each; openapi clean, ff-able); LOW 4/5/6 resolved. 4 new LOW for **`records`/PR body**: a deleted user's cookie still lists History/`GET /api/runs` under its id (FK without `ON DELETE` means the runs go first, so 0 rows in practice); half-configured with all four sign-in settings set still hides sign-in while `/auth/login` is 302 and `/auth/me` 200 (ADR-0008 or PR body); HIGH red run was 3 `DID NOT RAISE` + 1 claims-list, not 4; merge commit `23d2492` has a default message, no trailer. 687 passed / 14 deselected / 0 skipped. | `jay/gh-41-wiring` / `.worktrees/gh41-wiring` | PASS `verdicts/2026-11-15-gh41-wiring-repair.md` |
| gate-docstring-2 | **merged** 06:28 UTC: ff into the integration branch, head `1029451`. Judge PASS, 0 HIGH/MEDIUM, 2 LOW (judge's own pyright exit code read through a pipe; uv VIRTUAL_ENV warning). `gate.py:32-36` now matches `wiring.py:430-435` and `:505-506`. | `jay/gh-41-gate-docstring-2` / `.worktrees/gh41-gate-docstring-2` | PASS `verdicts/2026-11-15-gh41-gate-docstring-2.md` |
| records | **blocked** 06:58 UTC — whole-PR judge FAIL: 0 HIGH, 1 MEDIUM open (ADR-0008 does not record the `unique=True` sabotage substitution: on Neon `test_duplicate_user_sub_is_rejected` stays green because `users_sub_key` already exists and `create_all` never alters a table; `test_users_unique_on_neon_matches_the_mapping` fails 1 of 12 instead; SQLite fails 1 of 13 via the concurrent-sign-in test), 8 LOW: `routes.py:14-15` docstring gap not deferred anywhere; `users` NOT NULLs untested on Neon while spec :50 says every constraint is proven; spec :50 still says Neon `dev` branch and old table names (pre-existing); session docstring vs naive `now`; `.strip()` untested; `dict[str, Any]` in `account_view` (accepted earlier); 6 of 9 merge commits default message, trailers 49 Fable / 9 Opus / 6 none of 64; red-first count 15 of 64 covering 7 of 7 new test files. **Everything else passed:** 8 of 8 brief sabotages red; 687 passed / 14 deselected / 0 skipped of 701; each new file alone green; Neon 12 of 12, counts unchanged (users 0, runs 3, test patterns 0); all gates 0 incl. pip-audit 06:46 UTC; 45 of 45 paths Allowed, 0 Forbidden, no plan/verdict file in the diff; 11 `get_secret_value()` hits classified, none reaches output; synthetic boots behave (503 names `DATABASE_URL`, 302 to Google with the flagged cookie); every record statement checked matches the code; 35 of 35 cited test names exist; 25 of 28 carried items recorded. Re-planned as `records-repair` (attempt 1 of 3). **→ Final:** superseded by `records-repair` → `records-repair-2` (same branch), whole-PR re-judge PASS `verdicts/2026-11-15-gh41-records-repair-2.md`, merged at `dd3c10a` (final head). | `jay/gh-41-records` / `.worktrees/gh41-records` | FAIL `verdicts/2026-11-15-gh41-records-whole-pr.md` |

| records-repair | **blocked** 07:10 UTC — re-judge FAIL: previous MEDIUM **resolved** (judge reproduced 1 of 13 SQLite and 1 of 12 Neon under the `unique=True` sabotage; `test_duplicate_user_sub_is_rejected` still green; Neon counts unchanged); previous LOWs 1–3 addressed. **New MEDIUM, not accepted:** spec :50 now says "One Neon database, `main`" — unsupported (spec :67 still asks for a `dev` branch; `current_database() = 'main'` is false on Neon; the records show only that tests and the deployed app share the `DATABASE_URL` database). 5 new LOW: `claim_run` round trip listed as a rejected insert (it inserts a valid row); `users.id` PK missing from the not-proven list (1 of 5 `users` constraints proven); ADR-0008:64 "row write only" should be "row read or write"; ADR-0008:63 numbers have no source run; `tests/test_db_constraints.py:20-22` cites a spec :48 list that no longer exists (PR body). Re-planned as `records-repair-2` (attempt 2 of 3). Judge note: run Neon with `--tb=short` (a failing traceback writes the masked connection string). **→ Final:** superseded by `records-repair-2`, PASS `verdicts/2026-11-15-gh41-records-repair-2.md`, merged at `dd3c10a`. | `jay/gh-41-records` / `.worktrees/gh41-records` | FAIL `verdicts/2026-11-15-gh41-records-repair.md` |
| records-repair-2 | **merged** 2026-11-16 07:21 UTC: ff into the integration branch, head `dd3c10a`. Re-judge PASS: previous MEDIUM and LOWs 2–5 resolved; 0 HIGH, 0 MEDIUM, 5 LOW for the PR body or a later records pass: the new citations in spec :50 and ADR-0008:63 point at the gh41 plan and verdict files, which are untracked (the brief forbids `docs/superpowers/plans/**`; tracked support exists at runbook :103-104 and the `l4-constraints` verdicts); "the integration tests" is 13 of 14 (`test_integration_live.py` uses SQLite); "writes one valid row through `claim_run`" should read "inserts one valid run, claims it"; spec :98 and `tests/test_db.py:211` still say `dev` (pre-existing drift); `tests/test_db_constraints.py:20-22` cites a spec list that no longer exists. 687 passed / 14 deselected / 0 skipped of 701; 45 paths, 0 Forbidden. | `jay/gh-41-records` / `.worktrees/gh41-records` | PASS `verdicts/2026-11-15-gh41-records-repair-2.md` |

Integration branch: `jay/gh-41-google-sign-in` / `.worktrees/gh41`, **final head `dd3c10a`** (every task; contains `origin/main` `c5d0114`). **All tasks terminal 2026-11-16 07:21 UTC.** PR: #52, merged 2026-11-16 10:45:46 UTC as `949741f` (squash).
