Brief: Wave 2 — integration and Render deploy (lean, scope cut 2026-11-14).

Source: plan `docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md` ("Scope cut 2026-11-14", "W2 facts", "W1 wiring convention", "Coordinator rulings"); spec `docs/superpowers/specs/2026-11-14-receipts-design.md` (Architecture, Models, Keenable, Neon, Public URL safety, Deploy); ADR-0005 (hosting), ADR-0006 (gate profile, contract decisions). Standard: `AGENTS.md`. Written by the orchestrator 2026-11-15 01:25 UTC on the main session's instruction. Clock: submission ~05:30 UTC; **W2 merged and live on Render by 02:45 UTC.**

## Goal

One real comparison runs end to end: `POST /api/runs` (or the `/ui` form with the passcode) starts a run that uses the real Anthropic model and real Keenable search/fetch through the L1 harness, verifies claims with the L2 verifier, persists to Neon through the L4 `SqlRunRepo`, streams events to the L5 UI, and leaves a battlecard in History — on https://receipts-h745.onrender.com, with `/healthz` reporting the deployed sha. Fakes stay the unit-test path; nothing reads a secret at import or startup.

## Why it matters

Every lane was built and judged against fakes. W2 is the first time the pieces meet real services, and the demo depends on it: no live run, no submission. Render autoDeploys from `main`, so each W2 merge is also a deploy.

## Constraints

- **No secrets at import/startup** (ADR-0005, W0 test `test_create_app_boots_with_an_empty_environment` must keep passing): real clients are built lazily, inside request/start paths, from `get_settings()`.
- **Frozen files stay frozen:** `src/receipts/contracts.py`, `src/receipts/settings.py`, `src/receipts/fakes/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`. `greenlet` is NOT in the lock; L4's `SqlRunRepo` wraps a sync engine via `asyncio.to_thread` — keep that; do not `uv add`.
- **Wiring convention** (plan): `create_app()` stays zero-arg. It sets `app.state.run_service` to the real `InProcessRunService` **only when** `get_settings()` has `database_url` and `keenable_api_key` and `anthropic_api_key`; otherwise it leaves the L4/L5 `FakeRunService` fallbacks in place. Decide where that happens (a lazy resolver called on first request is acceptable; a startup event that reads settings and *falls back* on missing keys is acceptable; raising on missing keys at startup is not).
- **Public URL safety** (spec): History and stored runs are readable by anyone; starting a run requires `DEMO_PASSCODE` (compare with `secrets.compare_digest`) and `require_keenable_key`. L4's routes already do this; the L5 UI passes the typed passcode to a `starter(request, passcode)` callable — W2 injects a starter that enforces the same two checks in-process (or POSTs to `/api/runs`), so the UI cannot start a run the API would refuse.
- **Verifier**: call `receipts.verify.verify_claim` (L2's public function; signature `verify_claim(claim, pages: Mapping[str, FetchedPage], searches: Sequence[SearchResult]) -> Claim`, dropped convention `verify_note="dropped: …"`, helpers `is_dropped`, `dropped_reason`). L2 (PR #25) may merge after W2 starts: build against the branch's contract from the plan, and when it merges, `git merge origin/main` and re-run.
- **Gates stay gates**: `bin/jig` green; pyright strict on `src/` (`ui/` basic per file); no `# type: ignore`; `uv lock --check` green.
- **Render**: service `srv-dbsf8q0n74is739mv2jg`, URL https://receipts-h745.onrender.com, autoDeploy from `main`, Docker from `./Dockerfile`, `PORT=8000`, env `ANTHROPIC_API_KEY`, `KEENABLE_API_KEY`, `DATABASE_URL`, `DEMO_PASSCODE`, `MAX_CONCURRENT_SPECIALISTS=2` set on the service. `RENDER_API_KEY` is in `~/.zshenv` for logs/deploys. Do not create another service.
- **Local shell** has the same keys in `~/.zshenv` (`DATABASE_URL` points at the real Neon database the service uses): unit tests run with `env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY`; integration tests are `@pytest.mark.integration` and may use them.
- **Data**: live runs store quotes from public pages (ADR-0004); fixtures stay synthetic. Never commit a key; `.env` files are forbidden.

## File scope

`Allowed:`
- `src/receipts/harness/live.py` (new: real `SearchClient`/`FetchClient` over `langchain-keenable`, real `model_factory`), `src/receipts/harness/__init__.py` (exports only)
- `src/receipts/api/app.py` (wiring: `app.state.run_service` resolution; keep `git_sha()`, `healthz()`, `mount_ui(app)`, the `/` redirect and the routers), `src/receipts/api/wiring.py` (new, if you prefer the resolver in its own module)
- `src/receipts/ui/app.py` only to pass the passcode-enforcing `starter` into `build_ui` from `mount_ui`/`resolve_service` (no other UI changes)
- `src/receipts/api/app.py:git_sha()` fallback to `RENDER_GIT_COMMIT` (Render sets it; not a secret)
- `Dockerfile`: `CMD` → shell form binding `${PORT:-8000}`; delete the stale `infra/terraform` comment; nothing else
- `docs/api.md`: the Deploy bullet → Render per ADR-0005 (no registry push, no fixed port)
- `docs/runbooks/render.md` (new, short: deploy, logs via `RENDER_API_KEY`, env var names, wake-up before judging)
- `scripts/seed_demo_runs.py` (new: starts N live runs via the API or in-process and waits for `done`; prints verified/total and wall time per run; uses env keys; never commits output)
- `tests/test_integration_live.py` (new, `@pytest.mark.integration`), `tests/test_wiring.py` (new, unit: wiring falls back to fakes with no keys; real service chosen when settings present — with `monkeypatch.setenv` and stub factories, no network), `tests/test_api.py` only if the Dockerfile/port change needs a test (it should not)

`Forbidden:` the frozen files above; `src/receipts/verify/**`, `src/receipts/db/**`, `src/receipts/packs/**`, `src/receipts/ui/render.py`, `src/receipts/ui/demo.py` (lane code — if a wiring need requires a lane change, stop and report); `.github/**`, `bin/**`, `scripts/leak_gate/**`, `AGENTS.md`, ADRs other than a one-line correction in ADR-0006 if the orchestrator approves it (ask), the spec, `tests/fixtures/**`.

## What W2 builds

1. `harness/live.py`: `KeenableSearchClient(SearchClient)` and `KeenableFetchClient(FetchClient)` wrapping `langchain-keenable` (read its installed API: `uv run python -c "import langchain_keenable, inspect; print(dir(langchain_keenable))"`), sync methods returning `list[SearchResult]` / `FetchedPage`; a non-dict/non-string fetch result or an exception → `FetchedPage(ok=False)` (spec: fetch failed ≠ claim false). Built from an explicit key argument; the caller passes `require_keenable_key(settings).get_secret_value()`. `live_model_factory(pack)` = L1's `default_model_factory` (already lazy) — reuse, don't duplicate.
2. Wiring: `build_live_service(settings) -> InProcessRunService` = `InProcessRunService(Coordinator([load_pack("pricing"), load_pack("positioning_seo")], SpecialistRunner(search, fetch, verify=verify_claim), max_concurrent=settings.max_concurrent_specialists), SqlRunRepo())` with `await create_schema(repo.engine)` on first use; `resolve_run_service(app)` sets `app.state.run_service` once, lazily, when the three settings are present; otherwise leaves the fakes. `create_app()` wires the resolver so L4's `get_run_service` and L5's `resolve_service` see it (check how each reads `app.state` — set it before `mount_ui(app)` runs if L5 reads at mount time; if L5 captures the service at mount time and the real one must be lazy, mount with a thin proxy `RunService` that resolves on first call — document the choice).
3. Passcode-enforcing `starter` for the UI, injected via `build_ui(service, starter=...)`.
4. `git_sha()`: `os.environ.get("GIT_SHA") or os.environ.get("RENDER_GIT_COMMIT", "unknown")[:7]`.
5. Dockerfile `CMD` in shell form: `uvicorn receipts.api.app:app --host 0.0.0.0 --port ${PORT:-8000}` (keep `--frozen` installs; `GRADIO_ANALYTICS_ENABLED=False` stays).
6. `docs/api.md` Deploy bullet; `docs/runbooks/render.md`.
7. `scripts/seed_demo_runs.py` and the live integration test.

## Acceptance tests

Each exits 0 from the worktree root.

- `env -u DATABASE_URL -u ANTHROPIC_API_KEY -u KEENABLE_API_KEY uv run pytest -q -m "not integration"` — every unit test, including W0's empty-environment boot and L4/L5's fake fallbacks, passes; `tests/test_wiring.py` proves: no keys → `app.state.run_service` absent/fake; all three settings present (monkeypatched, with stubbed `SqlRunRepo`/`Keenable*` factories) → the real service type is chosen and no network call is made (watch both tests fail first).
- `bin/jig` — four rows `ok`.
- `uv lock --check` — 0.
- `env -i PATH="$PATH" HOME="$HOME" uv run python -c "from receipts.api.app import create_app; create_app()"` — 0.
- `uv run pytest tests/test_integration_live.py -q -m integration -rs` — with keys from `~/.zshenv`: ONE live run for one invented-but-real-world pair (pick two real public companies in one category; this is a live web search), asserting the event stream ends with `DoneEvent`, `total_count >= 1`, every verified claim's receipt URL is in the run's fetched pages or its search log, and printing `verified/total` and wall time (target < 90 s; report the actual number with its run id). Record the printed line in the PR body.
- `docker build --build-arg GIT_SHA=w2test -t receipts-w2 . && docker run -d --rm --name receipts-w2 -e PORT=8123 -p 8123:8123 receipts-w2 && sleep 6 && curl -fsS http://127.0.0.1:8123/healthz | grep -q '"sha":"w2test"'; docker stop receipts-w2` — the shell-form `CMD` honours `PORT`. If Docker is unavailable locally, say so; CI `api-image` covers the default port.
- After merge (orchestrator or main session runs it): `curl -fsS https://receipts-h745.onrender.com/healthz` shows a 7-char sha (from `RENDER_GIT_COMMIT`); one live run via `POST /api/runs` with `X-Demo-Passcode` returns 202 and `GET /api/runs/{id}` eventually shows a battlecard; History lists it. `scripts/seed_demo_runs.py` leaves 1–3 completed runs in Neon.

## Verification (reviewer who trusts nothing)

1. `git diff origin/main...HEAD --name-only` ⊆ Allowed; no frozen file; no lane file beyond the two UI lines allowed.
2. `grep -rn 'os.environ\|getenv' src/receipts/` — `api/app.py` (`GIT_SHA`, `RENDER_GIT_COMMIT`) and `settings.py` only; no module-level `get_settings()`/client construction (`grep -n '^[A-Za-z_]* = .*(get_settings\|Keenable\|SqlRunRepo\|ChatAnthropic)' src/receipts/**/*.py` → nothing).
3. Sabotage: make `resolve_run_service` raise when `keenable_api_key` is None → the empty-env boot test or `test_wiring` goes red; revert. Delete the `starter` injection → a `test_wiring`/UI test proving the UI refuses a wrong passcode goes red; revert.
4. `grep -n 'CMD' Dockerfile` — shell form with `${PORT:-8000}`; `grep -c terraform Dockerfile` → 0.
5. `gh pr checks <W2 PR>` — five required checks green on the head; after merge, Render deploy event for that sha succeeded (`RENDER_API_KEY` → `GET /v1/services/srv-dbsf8q0n74is739mv2jg/deploys?limit=1`) and `/healthz` sha matches `git rev-parse --short origin/main`.
6. The live-run line in the PR body carries run id, verified/total, wall time, and the UTC time it ran.

## Do not

- Do not read any key at import, in `create_app()` unconditionally, or in a startup event that fails without keys.
- Do not `uv add`, edit the lock, or add `greenlet`; do not touch frozen files.
- Do not change lane logic (verifier rules, repo schema, UI rendering, packs). A wiring need that requires a lane change is reported, not made.
- Do not create a Render service, change its env vars, or trigger manual deploys; merges to `main` deploy.
- Do not commit run output, fixtures with real quotes, or anything containing a key; `python3 scripts/leak_gate/check_tracked.py` and gitleaks must stay green.
- Do not count a skipped integration test as a pass; name it.

## Items collected from lane verdicts (do what fits in the time box; report the rest)

(i) Constraint-rejection integration test for the `runs` table on Neon (L4 #3; allowed as `@pytest.mark.integration`, inserts rows the constraints reject so nothing persists) — if time allows. (ii) Guard test that the UI stream stops after `DoneEvent` with the real service (L5 MEDIUM) — cover via the live run: assert the stream ended. (iii) `golden_claims.json` row 3 vs L2's convention — compare `verified` only in any golden test; do not edit `tests/fixtures/**`. (iv) `_search_ts` rank matching (L1 LOW) — not W2's; note. (v) ADR-0006:33 (`create_async_engine`) and spec:48 (five tables) are stale — report; a one-line ADR-0006 correction needs orchestrator approval. (vi) `git_sha()` fallback — in scope above.

## Assumptions

- `langchain-keenable` 0.1.x exposes search and fetch callables usable synchronously with an explicit API key; if its API requires an env var only, set it on the client object or via a documented adapter, never at import.
- The Render free tier sleeps after 15 min; the post-merge live check first hits `/healthz` and waits for 200.
- `MAX_CONCURRENT_SPECIALISTS=2` on Render with two packs means both specialists run concurrently.
- L2 merges during W2; W2's integration test asserts receipts-on-fetched-pages regardless of L2's exact fuzzy rule.
