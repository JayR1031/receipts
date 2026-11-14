Brief: Wave 0 foundations, plus the W1 lane outline (L1–L6).

Source: `docs/superpowers/specs/2026-11-14-receipts-design.md` (approved design, on branch `jay/1-spec-and-adrs`, PR #11). Standard: `AGENTS.md`, section 9 lane rules. Clock: 48 h hackathon, started; W0 is time-boxed H0–3.

## Goal

Every W1 lane can start in parallel against frozen typed contracts, lazy settings, a locked dependency set and in-memory fakes, with all five required checks (`gitleaks`, `leak-gate`, `dependency-audit`, `ci-python`, `api-image`) green on the W0 PR and the hackathon gate profile recorded in an ADR.

## Why it matters

Five builders (three Claude Code worktrees, Codex, Mel) start the moment W0 merges; anything W0 leaves vague becomes five divergent guesses that collide at merge time, and the spec forbids lanes from editing contracts or dependencies, so a gap in W0 blocks a lane outright. The `api-image` check boots the container with no secrets, so one eager `os.environ[...]` read turns the required checks red for every later PR. None of the real keys (Anthropic, Keenable, Neon) exist on the machine yet, so if W0's fakes are incomplete, W1 cannot be tested at all.

## Constraints

- **Typed boundaries** (AGENTS.md section 3): `RunEvent` is a discriminated union of one Pydantic model per kind; no `dict[str, Any]` crosses a module line. Receipts are `QuoteReceipt | SearchReceipt`, discriminated on a `kind` field.
- **Pure rules**: nothing in `src/receipts/contracts.py` or `src/receipts/settings.py` reads a database, the network or the clock. Timestamps are fields, supplied by the caller.
- **No secrets at import or startup** (spec, ADR-0005 Consequences): `Settings` is built lazily by `get_settings()`; importing `receipts.api.app` and calling `create_app()` with an empty environment must succeed. Today only `GIT_SHA` is read (`src/receipts/api/app.py:17`); W0 adds the five names `ANTHROPIC_API_KEY`, `KEENABLE_API_KEY`, `DATABASE_URL`, `DEMO_PASSCODE`, `MAX_CONCURRENT_SPECIALISTS` and nothing else.
- **Frozen after W0** (AGENTS.md section 9): `src/receipts/contracts.py`, `src/receipts/settings.py`, `src/receipts/fakes/**`, `tests/conftest.py`, `pyproject.toml`, `uv.lock`, so no two lanes edit shared contracts or fixtures. A lane that needs a change stops and asks.
- **Dependencies locked once**: `uv.lock` resolves everything W1 needs (see File scope); lanes may not run `uv add`. W0 absorbs the five open Dependabot pip bumps (#6 fastapi ≥0.162.5, #7 uvicorn ≥0.54.0, #8 pyright ≥1.1.414, #9 pytest ≥9.2.0, #10 pydantic ≥2.14.3) as lower bounds; those PRs are then closed as superseded by whoever merges W0. Actions bumps #2–#5 are out of scope.
- **Gates stay gates** (AGENTS.md sections 1, 6): `--exit-code 1`, `--strict`, no path filters. The hackathon profile may only (a) narrow pyright strict paths exactly as the spec says, and (b) add `--ignore-vuln <ID>` flags to the pip-audit command in `.github/workflows/security.yml:37`, one per advisory listed in ADR-0006 with package, reason and expiry date. Tests, lint and format are fully enforced.
- **Branch and PR** (AGENTS.md section 2, `docs/tracker.md`): one issue, one branch `jay/gh-<N>-w0-foundations` (new issue N), one PR. The ruleset is strict, so the branch must be rebased onto `main` after PR #11 merges and before W0 merges.
- **TDD** (AGENTS.md section 4): every new test file below is written first and watched failing.
- **Data** (section 9): no real keys in fixtures; fixture URLs and quotes are invented public-web-shaped text. `scripts/leak_gate/denylist.txt` stays as is.

## File scope

`Allowed:`
- `pyproject.toml`, `uv.lock`
- `src/receipts/contracts.py` (new), `src/receipts/settings.py` (new)
- `src/receipts/fakes/__init__.py` (new), `src/receipts/fakes/*.py` (new)
- `src/receipts/harness/__init__.py`, `src/receipts/verify/__init__.py`, `src/receipts/packs/__init__.py`, `src/receipts/db/__init__.py`, `src/receipts/ui/__init__.py` (all new, docstring only — the lane skeleton)
- `src/receipts/ui/app.py` (new; `build_ui() -> gr.Blocks` stub only, L5 owns it from W1)
- `src/receipts/api/app.py`, `src/receipts/api/models.py` (mount, redirect, remove `/echo`)
- `tests/conftest.py`, `tests/test_api.py`, `tests/test_openapi_export.py`, `tests/test_contracts.py` (new), `tests/test_settings.py` (new), `tests/test_fakes.py` (new)
- `docs/adr/0006-hackathon-gate-profile.md` (new), and this brief. (The Vercel row in ADR-0004, the landing-page bullets in ADR-0005 and the spec's must-ship and L6 edits already landed in PR #11, so W0 does not touch ADR-0004, ADR-0005 or the spec.)
- `.github/workflows/security.yml` line 37 only, and only to append `--ignore-vuln <ID>` flags enumerated in ADR-0006
- `Dockerfile` line `ENV ...` only, to add `GRADIO_ANALYTICS_ENABLED=False`

`Forbidden:` `AGENTS.md`, `CLAUDE.md`, `README.md`, `bin/**`, `scripts/**`, `.github/workflows/ci-python.yml`, `.github/workflows/api-image.yml`, `.github/dependabot.yml`, `.gitleaks.toml`, `.gitleaksignore`, `.pre-commit-config.yaml`, `docs/adr/000[0-3]-*.md`, `docs/api.md`, `docs/tracker.md`, any file under `src/receipts/{harness,verify,packs,db}/` other than `__init__.py`, any `.yaml` pack, anything outside this repository.

### What W0 builds (names the W1 lanes depend on; all `(new)` unless cited)

`src/receipts/contracts.py` (new), Pydantic v2, `frozen=True`, `extra="forbid"`:
- `Domain = Literal["pricing", "positioning_seo", "news_social", "product"]`; `About = Literal["subject", "rival"]`; `VerifyMethod = Literal["quote_exact", "quote_fuzzy", "search_log"]`; `RunStatus = Literal["queued", "running", "done", "error"]`.
- `QuoteReceipt{kind="quote", url, quote}`, `SearchReceipt{kind="search", query, rank, url, ts}`, `Receipt = Annotated[QuoteReceipt | SearchReceipt, Field(discriminator="kind")]`.
- `Claim{domain, about, text, receipt, verified: bool, verify_method: VerifyMethod | None, verify_note: str | None}`.
- `RunRequest{subject, rival, category: str | None}`; `RunId = NewType("RunId", str)`.
- `SearchResult{query, rank, url, title, snippet, ts}`; `FetchedPage{url, text, fetched_at, ok: bool}`.
- `RunEvent` union, discriminated on `kind`: `StartedEvent`, `SearchEvent`, `FetchEvent`, `ClaimEvent`, `VerifiedEvent`, `DroppedEvent`, `DoneEvent`, `ErrorEvent`; each carries `run_id`, `ts`, `domain: Domain | None`, plus kind-specific fields. `RUN_EVENT_ADAPTER = TypeAdapter(RunEvent)`.
- `Battlecard{run_id, subject, rival, claims: tuple[Claim, ...], verified_count, total_count, started_at, finished_at}`; `verified_count` and `total_count` are the "23 of 27" shown in the UI.
- `RunSummary{run_id, subject, rival, status, verified_count, total_count, started_at}`.
- `DomainPack{id, display_name, model, effort, system_prompt, query_templates: tuple[str, ...], source_allow, source_deny, max_searches=3, max_fetches=4, timeout_s, extra_fields, rubric}` — the YAML pack schema L1 loads and L3 writes.
- Protocols: `SearchClient.search(query) -> list[SearchResult]`, `FetchClient.fetch(url) -> FetchedPage`, `RunRepo` (`save_run`, `append_event`, `save_battlecard`, `get_run`, `list_runs`), `RunService` (`start(RunRequest) -> RunId`, `events(RunId) -> AsyncIterator[RunEvent]`, `get(RunId) -> Battlecard | None`, `list() -> list[RunSummary]`).

`src/receipts/settings.py` (new): `Settings(BaseSettings)` with `anthropic_api_key: SecretStr | None`, `keenable_api_key: SecretStr | None`, `database_url: str | None`, `demo_passcode: SecretStr | None`, `max_concurrent_specialists: int = 4`; `get_settings() -> Settings` (lazy, cached); pure `sqlalchemy_url(url: str) -> str` rewriting `postgresql://` → `postgresql+psycopg://`; `MissingSettingError(name)`; `require_keenable_key(settings) -> SecretStr` raising it.

`src/receipts/fakes/` (new): `InMemoryRunRepo` (implements `RunRepo`), `FakeRunService` (replays a scripted `list[RunEvent]` with a configurable delay, implements `RunService`), `FakeKeenable` (implements `SearchClient` and `FetchClient` from canned fixtures; an unknown URL returns `FetchedPage(ok=False)`), `fake_llm(responses)` returning `langchain_core.language_models.fake_chat_models.GenericFakeChatModel`. `tests/conftest.py` exposes fixtures `fake_repo`, `fake_run_service`, `fake_keenable`, `fake_llm`, `sample_pack`, `sample_claims`, `sample_events` (one of every event kind).

`src/receipts/api/app.py`: keep `git_sha()`, `healthz()`, `create_app()`; add `GET /` → 302 to `/ui`; mount `build_ui()` with `gr.mount_gradio_app(app, blocks, path="/ui")`; delete `echo` and `EchoIn`/`EchoOut`. API routes `/api/runs*` are L4's, not W0's.

Dependencies to add to `[project]` (W0 picks exact pins by `uv lock`; names verified on PyPI 2026-11-14): `gradio`, `langchain` (1.x), `langchain-core`, `langchain-anthropic`, `langchain-keenable`, `pydantic-settings`, `sqlalchemy` (2.x), `psycopg[binary]`, `aiosqlite`, `rapidfuzz`, `pyyaml`. Dev group adds `pytest-asyncio` (or uses anyio's pytest plugin already present via httpx — pick one, record it in ADR-0006).

`docs/adr/0006-hackathon-gate-profile.md` (new): pyright strict list = every `src/receipts/**` path except `src/receipts/ui/`; `ui/` files start with `# pyright: basic`; pip-audit triage table (advisory ID, package, why it does not apply to this app, expiry date) — empty table is a valid result and is written as "0 advisories ignored, audited at <commit>"; the async test plugin choice; the `langchain-anthropic` `effort` pass-through finding (confirmed or the fallback parameter chosen); the W1 lane rules restated with scope globs; the Aceternity license check as a pending item owned by L6.

## Acceptance tests

Each line exits 0 from the repo root on the W0 branch.

- `uv run pytest tests/test_contracts.py -q` — (new; watch it fail first with `ModuleNotFoundError: receipts.contracts`) every `RunEvent` kind round-trips through `RUN_EVENT_ADAPTER.dump_json` → `validate_json` unchanged; a payload with an unknown `kind` is rejected; `Claim` rejects an extra field; `DomainPack` applies defaults `max_searches=3`, `max_fetches=4`.
- `uv run pytest tests/test_settings.py -q` — (new; watch it fail first) `Settings()` under `monkeypatch.delenv` of all five names constructs with every secret `None` and `max_concurrent_specialists == 4`; `sqlalchemy_url("postgresql://u:p@h/db")` returns `postgresql+psycopg://u:p@h/db` and leaves `postgresql+psycopg://...` unchanged; `require_keenable_key` raises `MissingSettingError` naming `KEENABLE_API_KEY`; a subprocess `env -i PATH="$PATH" HOME="$HOME" uv run python -c "from receipts.api.app import create_app; create_app()"` exits 0.
- `uv run pytest tests/test_fakes.py -q` — (new; watch it fail first) `InMemoryRunRepo` returns what was saved and lists newest first; `FakeRunService.events()` yields the scripted events in order and ends with `DoneEvent`; `FakeKeenable.fetch("https://unknown.example/")` returns `ok=False`; `fake_llm(["hi"]).invoke("x").content == "hi"`.
- `uv run pytest tests/test_api.py -q` — `GET /` → 302 with `Location: /ui`; `GET /ui` → 200; `/healthz` unchanged; the three `echo` tests are gone.
- `uv run pytest tests/test_openapi_export.py -q` — asserts `{"/healthz"} <= set(doc["paths"])` and `"/echo" not in doc["paths"]`.
- `uv lock --check` — the lock matches `pyproject.toml` (the lane rule "no new deps" is testable).
- `uv sync --frozen && bin/jig` — format, lint, pyright, unit tests all `ok`.
- `uv run pip-audit --strict --vulnerability-service osv <same --ignore-vuln flags as .github/workflows/security.yml:37>` — matches the `dependency-audit` job.
- `python3 scripts/leak_gate/check_tracked.py` — prints `scanned N files against M patterns`, exit 0.
- `gitleaks detect --source . --redact --exit-code 1` — exit 0 (gitleaks is at `/opt/homebrew/bin/gitleaks`).
- `bin/red-test` — every gate `red→green`; any `skipped:` row is named in the PR description, not counted.
- `docker build --build-arg GIT_SHA=w0test -t receipts-api . && docker run -d --rm --name receipts-w0 -p 8000:8000 receipts-api && sleep 5 && curl -fsS http://127.0.0.1:8000/healthz | grep -q '"sha":"w0test"' && curl -fsS -o /dev/null http://127.0.0.1:8000/ui; docker stop receipts-w0` — mirrors `api-image` with no secrets in the container.
- `uv run pyright` reports `0 errors` with the ADR-0006 strict list in `pyproject.toml` `[tool.pyright]`.

## Verification

A reviewer who trusts nothing the implementer said:

1. `git diff origin/main...HEAD --stat` — every path is in `Allowed:` above. Any path in `Forbidden:` is a FAIL.
2. `grep -n 'exit-code\|--strict\|audit-level' .github/workflows/*.yml` — still `--exit-code 1`, still `--strict`, still `--audit-level high`; the only diff on `security.yml` is `--ignore-vuln` flags whose IDs all appear in `docs/adr/0006-hackathon-gate-profile.md`. `grep -c ignore-vuln .github/workflows/security.yml` equals the ADR table's row count.
3. `grep -rn 'os.environ\|getenv' src/receipts/` — only `src/receipts/api/app.py` (`GIT_SHA`) and `src/receipts/settings.py` (via `BaseSettings`, no module-level instance). A module-level `Settings()` or `get_settings()` call is a FAIL.
4. `grep -rn 'dict\[str, Any\]\|Any\b' src/receipts/contracts.py` — no output.
5. `uv run pyright --verifytypes` is not required; instead read `pyproject.toml` `[tool.pyright] strict` and confirm it lists `src/receipts/contracts.py`, `src/receipts/settings.py`, `src/receipts/fakes`, `src/receipts/harness`, `src/receipts/verify`, `src/receipts/db`, `src/receipts/api` and not `src/receipts/ui`.
6. Sabotage, one at a time, `bin/jig` or the named command must turn red, then revert and confirm green:
   - Remove `Field(discriminator="kind")` from `Receipt` → `tests/test_contracts.py` red (unknown kind accepted or round-trip ambiguous).
   - Add `SETTINGS = Settings()` at module level in `settings.py` and `assert SETTINGS.keenable_api_key` in `create_app()` → the `env -i` subprocess test red.
   - Delete the `gr.mount_gradio_app` line → `tests/test_api.py` red on `/ui`.
   - Add `def f(x): return x` to `contracts.py` → `uv run pyright` red; the same line in `src/receipts/ui/app.py` under `# pyright: basic` stays green — that asymmetry is the gate profile, and the reviewer notes it as a known, recorded gap.
   - `uv add requests==2.19.0` without committing the lock → `uv lock --check` red and `uv run pip-audit --strict ...` red; `git checkout pyproject.toml uv.lock` → green.
7. On GitHub, all five required checks are green on the PR head commit after the rebase onto `main`; read them from the Checks tab, not the PR description. Run `gh pr checks <W0-PR>`.
8. `git diff --name-only origin/main...HEAD -- docs/` lists only `docs/adr/0006-hackathon-gate-profile.md` and this brief.

## Do not

- Do not call W0 done without watching `tests/test_contracts.py`, `tests/test_settings.py`, `tests/test_fakes.py` fail first; "they pass" without a red run is not evidence.
- Do not loosen pyright by setting `typeCheckingMode = "basic"` globally, adding `# type: ignore`, or dropping `tests` from `include`. The only narrowing is the strict list and `# pyright: basic` in `src/receipts/ui/*.py`.
- Do not remove `--strict` or `--exit-code 1`, add a `paths:` filter, or ignore an advisory that is not in ADR-0006 with an expiry date.
- Do not read any secret at import, in `create_app()`, or in a FastAPI startup event. Do not add a `.env` file to the image or a default value for any key.
- Do not type an event as `dict[str, Any]`, `Mapping[str, object]` or a single `RunEvent` class with an optional-everything payload.
- Do not leave `uv.lock` out of the commit, pin with `==` in `pyproject.toml` (the lock is the pin), or let the Dockerfile stop using `--frozen`.
- Do not write YAML packs, Verifier code, DB tables, API routes or UI panels; those are W1. A stub that "just gets it working" in a lane folder is a scope defect.
- Do not edit `AGENTS.md`; section 9 already carries the lane rules. If a rule needs changing, stop and ask.
- Do not close Dependabot PRs #6–#10 from the W0 branch tooling; that happens after W0 merges, by the person merging.
- Do not report a `bin/red-test` skip as a pass; name the skipped gate and why.

## Open questions

None that change the W0 plan. (The L6 builder and the Aceternity license result are recorded below as assumptions and a pending item for L6, respectively.)

## Assumptions

- W0 branches from `main` after PR #11 (spec, ADRs, AGENTS.md section 9) merges, and stays up to date with `main`; the ruleset's strict up-to-date rule makes this mandatory, not optional.
- "Claude Code (main)" in the spec's fan-out table means the main Claude Code session builds W0, not that W0 commits to `main` directly; it goes through a PR like every other change.
- Fakes live in `src/receipts/fakes/` (importable by lanes and by the image, so `importlib` paths are uniform), not under `tests/`, and are frozen with `contracts.py`. A lane needing extra fake behaviour builds it inside its own folder's tests.
- `DomainPack` (the YAML schema) is a W0 contract because L1 (loader) and L3 (YAML files) both depend on it and run in parallel.
- `SearchClient`/`FetchClient` protocols decouple fakes from `langchain-keenable`'s API; L1 wraps them in LangChain tools named exactly `keenable_search` and `keenable_fetch` so `ToolCallLimitMiddleware` budgets bind to those names.
- The scaffold's `/echo` route is removed in W0; it is not in the spec's API and would otherwise ship on a public URL.
- pip-audit exceptions are implemented as `--ignore-vuln <ID>` flags on the one command at `.github/workflows/security.yml:37`, since the spec says advisories are "triaged ... instead of blocking merges" but fixes no mechanism. Expiry dates are no later than 2026-11-30; after that each ignore is removed or re-justified.
- `ui/` basic mode is implemented per file with `# pyright: basic` rather than changing the global `typeCheckingMode`, so tests keep their current level.
- `GRADIO_ANALYTICS_ENABLED=False` goes in the Dockerfile and `gr.Blocks(analytics_enabled=False)` in the stub so the `api-image` run makes no outbound call.
- `uvicorn` binding to `${PORT:-8000}` for Render is W2 (deploy) work; the `api-image` check expects port 8000 and W0 leaves `CMD` alone.
- `effort` pass-through in `langchain-anthropic` is checked by reading the installed package (`grep -rn effort .venv/lib/python3.*/site-packages/langchain_anthropic/`) and recorded in ADR-0006; no API call.
- The user's decision that the Vercel landing page is must-ship is folded in as lane L6; its doc edits landed in PR #11. Every other spec decision is unchanged.
- L6 is built by Claude Code (Mel holds L5 and Codex holds L4; Mel is installed and runs on an OpenAI key), in its own repository outside this one. Its only touch inside this repo is a README link in W3.
- Closing Dependabot PRs #6–#10 as superseded and the Actions bumps #2–#5 are handled outside W0's file scope.

### W1 lane outline (for `/orchestrate`; this is the brief's reading of the spec's fan-out table and is not part of W0's file scope)

Common to every lane: branch `jay/gh-<N>-<lane>`; one worktree under `.worktrees/`; reads `AGENTS.md`; imports only from `receipts.contracts`, `receipts.settings`, `receipts.fakes` and its own folder; no network in unit tests (`@pytest.mark.integration` for anything needing a key); `bin/jig` green → `/judge` → merge. Exit for every lane: judge verdict, not "done". Merge order L3 → L2 → L1 → L4 → L5; L6 is independent of all five.

| Lane | Builder | Scope (`Allowed:`) | Depends on | Builds | Must prove (unit, with fakes) |
|---|---|---|---|---|---|
| L1 Harness | Claude Code worktree | `src/receipts/harness/**`, `tests/test_harness*.py` | W0 | `load_pack(name) -> DomainPack` via `importlib.resources`; `SpecialistRunner` (one generic runner, `create_agent` + `ToolCallLimitMiddleware` on `keenable_search`/`keenable_fetch`, budgets from the pack); `Coordinator` (`asyncio.gather` over packs with a `Semaphore(max_concurrent_specialists)`); `InProcessRunService` implementing `RunService`, emitting `RunEvent`s to subscribers and to a `RunRepo` | Coordinator with `fake_llm` + `FakeKeenable` yields `StartedEvent` … `DoneEvent` in order; tool budget stops at `max_searches`; a pack with a bad field fails validation by name; `Semaphore` caps concurrency at the setting |
| L2 Verifier | Claude Code worktree | `src/receipts/verify/**`, `tests/test_verify*.py` | W0 | pure `verify_claim(claim, pages: Mapping[str, FetchedPage], searches: Sequence[SearchResult]) -> Claim`; `normalize(text)` (strip markdown, case, whitespace, quotes, dashes); exact substring then `rapidfuzz.partial_ratio >= 90`; search-log receipts match a logged row; `fetch ok=False` → fetch-failed, not "false"; optional Haiku `verify_note` injected as a callable that may only set `verify_note` | Cases: exact, fuzzy ≥90, miss, markdown-wrapped, fetch-failed, URL not fetched this run → dropped, search receipt with unlogged query → dropped; the note callable can never flip `verified` |
| L3 Packs + golden set | Claude Code worktree | `src/receipts/packs/*.yaml`, `tests/fixtures/**`, `tests/test_packs*.py` | W0 | the four YAML packs (`pricing`, `positioning_seo`, `news_social`, `product`) validated against `DomainPack`; three demo comparisons as fixture files (subject, rival, canned `SearchResult`s and `FetchedPage`s for `FakeKeenable`); golden expected claims | Every YAML loads as `DomainPack` with no extras; every `query_templates` entry formats with `{subject}`, `{rival}`, `{category}`; fixture URLs resolve inside the fixture set |
| L4 Persistence + API | **Codex** (`docs/superpowers/briefs/L4-api.md`, written by the orchestrator) | `src/receipts/db/**`, `src/receipts/api/**` except the W0 mount lines, `tests/test_db*.py`, `tests/test_api*.py`, `docs/api/openapi.json` | W0 (uses `FakeRunService` until W2) | SQLAlchemy 2 tables `runs, sources, search_results, claims, events` with portable types; `SqlRunRepo` implementing `RunRepo`, engine from `sqlalchemy_url(settings.database_url)` with `pool_pre_ping=True`, created lazily; routes `POST /api/runs` → 202 `{run_id}` (requires `DEMO_PASSCODE` header match and `require_keenable_key`, else 401 / 503), `GET /api/runs/{id}`, `GET /api/runs` | Round-trip on SQLite in-memory for every event kind; 202/401/503 paths with the fake service; History lists newest first; `uv run python scripts/export_openapi.py` committed |
| L5 Gradio UI | **Mel** (`docs/superpowers/briefs/L5-ui.md`); fallback: Claude Code if not judge-green by H20 | `src/receipts/ui/**`, `tests/test_ui*.py` | W0 (uses `FakeRunService`) | `build_ui(service: RunService) -> gr.Blocks`: input (subject, rival, category, passcode), live agent panel driven by a generator over `service.events()`, battlecard with receipts and "N of M verified", History tab; dark spotlight theme via `gr.Theme` + CSS, no Node | Generator renders one row per `RunEvent` kind from `sample_events`; battlecard shows `verified_count` of `total_count`; the UI module imports no secret and makes no network call under test |
| L6 Landing page (new, must-ship) | Claude Code, outside this repo | separate Next.js 16 project (Aceternity "cryptgen" template: hero + features only; testimonials, pricing, logo cloud removed), deployed on Vercel; in-repo: README link (W3) | none in W1; Render URL in W2/W3 | one page that explains "every claim carries a receipt" and links to the Render app URL | **Blocking before it is public:** confirm the Aceternity template license permits this public use and any redistribution involved; record the result (license name, source URL, date read, verdict) in ADR-0005 Consequences, replacing the "pending" note W0 leaves there. `pnpm build` exits 0; a Lighthouse or manual check that the two sections render; link to the Render URL verified after W2 |

Parallel safety: L1–L5 scopes are disjoint globs (plan-check `parallel_safe = true`); L4 and W0 both touch `src/receipts/api/app.py`, so L4 starts only after W0 is merged and must not move the mount or the redirect. L6 shares no files with anything. W2 (integration + Render) depends on L1–L5 merged; W3 (ship) depends on W2 and on L6's license result.
