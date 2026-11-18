# Plan: Wave 0 foundations, then the W1 lanes in parallel

Brief: `docs/superpowers/briefs/2026-11-14-w0-foundations-and-w1-lanes.md`. Spec: `docs/superpowers/specs/2026-11-14-receipts-design.md`. Lane globs: `AGENTS.md` section 9. Written 2026-11-14 (hackathon H0–1). Final state (recorded 2026-11-18): W0 and lanes L1 to L5 merged; W2 merged in PR #29 (2026-11-15 03:00 UTC); W3 shipped through PRs #50 and #51. The `w2` and `w3` rows below stop at `judging` and `planned`, as the coordinator last wrote them.

## Shape

One serial gate, then a fan-out of five disjoint lanes plus one lane outside the repo:

1. `pr11` — a human precondition, not an agent task: PR #11 (spec, ADRs, AGENTS.md section 9) merges to `main`. **Changed 2026-11-14 (user: "I need to submit ASAP", relayed by the main session):** W0 no longer waits for it. W0 branches from the PR #11 head (`origin/jay/1-spec-and-adrs` = `da06dd5`), whose diff against `origin/main` is exactly `AGENTS.md`, `docs/adr/0004-*`, `docs/adr/0005-*`, the spec and `scripts/leak_gate/denylist.txt` — no file in W0's scope. When #11 merges, W0 brings itself up to date with `git merge origin/main` (never rebase + force-push). `pr11` stays in the graph as the gate for `l6-license` (which edits ADR-0005, a #11 file) and as the precondition for *merging* W0.
2. `w0` — the only task before W1. One issue (#12), one branch (`jay/gh-12-w0-foundations`), one PR (the brief requires this). Dispatched 2026-11-14 from `da06dd5` in `.worktrees/w0`. It produces every contract the lanes consume: `contracts.py`, `settings.py`, `fakes/`, `tests/conftest.py`, the locked dependency set, the lane skeleton, the `/ui` mount and ADR-0006.
3. `l1`–`l5` — start together the moment `w0` is `merged`. Their scopes are the AGENTS.md section 9 globs and are pairwise disjoint, so `parallel_safe = true`. Merge order is fixed by the spec: **L3 → L2 → L1 → L4 → L5**; that is a merge order for the human, not a start order, so it is not encoded as `deps`.
4. `l6-license` and `l6-landing` — the landing page. The license check edits `docs/adr/0005-app-architecture-and-hosting.md:22` (the pending note), so it waits for `pr11`; the page build lives in a separate repository and touches nothing here, so it can start now. Publishing the page on a public URL waits for the license verdict (enforced via `w3`'s deps).
5. `w2`, `w3` — integration/deploy and ship. Listed so the dependency chain is visible and a resumed session sees them; **both need their own `/improve-prompt` brief before dispatch**, and their scopes below are provisional (taken from the spec, not from an approved brief).

### Why W0 is one task despite its size

The orchestrator's size heuristic is roughly 300 changed lines per task; W0 will be larger (contracts ≈200, fakes ≈150, three new test files ≈200, settings, ADR, lock). The brief fixes "one issue, one branch, one PR" for W0, and the alternative (two stacked PRs under a strict up-to-date ruleset, each needing its own judge pass) costs more of a 3-hour time box than it saves. Mitigation written into the dispatch: the implementer commits in the brief's order, one slice per commit, in this sequence: (a) `pyproject.toml` + `uv.lock` + `[tool.pyright]` strict list; (b) `contracts.py` with `tests/test_contracts.py` red first; (c) `settings.py` with `tests/test_settings.py` red first; (d) `fakes/` + `conftest.py` with `tests/test_fakes.py` red first; (e) lane skeleton `__init__.py` files + `ui/app.py` stub + `api/app.py` mount and redirect + `test_api.py`/`test_openapi_export.py`; (f) `docs/adr/0006-hackathon-gate-profile.md`, `security.yml:37`, `Dockerfile` `ENV`. If the implementer hits a third jig failure, the task is blocked and re-planned as the split above, not retried.


## Scope cut 2026-11-14

Deadline change from the user (relayed by the main session 2026-11-14 ~23:00 UTC): **submission is due about 05:30 UTC 2026-11-15, roughly six hours away.** The user chose "cut hard". This section overrides the brief and the spec where they differ; the spec's Goals section carries a one-line pointer here (W0 adds it; the only spec edit allowed in W0).

| # | Area | Was | Now |
|---|---|---|---|
| 1 | Builders | Claude Code W0/L1/L2/L3; Codex L4; Mel L5 | **Claude Code builds W0 and L1–L5**, all five lanes in parallel worktrees after W0 merges. No Codex lane; no `L4-api.md`/`L5-ui.md` briefs. Mel is off the critical path (user drives it for QA and docs; main session handles that). |
| 2 | Packs (L3) | 4 YAML packs | **2 packs: `pricing`, `positioning_seo`.** Still YAML on the `DomainPack` schema so more can be added if time is left. `Domain` literal in contracts keeps all four values. |
| 3 | Persistence + API (L4) | 5 tables `runs, sources, search_results, claims, events` | **One `runs` table**: `id, created_at, subject, rival, category, status, battlecard` (JSON), `events` (JSON), SQLAlchemy 2, portable types, SQLite in unit tests, Neon in W2. API unchanged: `POST /api/runs` (passcode + `require_keenable_key`; 202/401/503), `GET /api/runs/{id}`, `GET /api/runs`. |
| 4 | Verifier (L2) | exact + fuzzy + search-log + fetch-failed + Haiku `verify_note` callable | **Drop the Haiku note.** `verify_note` stays a field (set to a short rule-derived string or `None`); no LLM in the verifier. |
| 5 | UI (L5) | live panel, battlecard, History tab, spotlight theme | Input, live progress, battlecard with receipts and "N of M verified", **a plain History list**. Minimal dark theme, no polish. |
| 6 | Golden set (L3) | 3 synthetic comparisons | **1 synthetic comparison fixture** plus golden expected claims. |
| 7 | W0 | full brief, H0–3 | **Lean, ~45 min:** contracts, settings, locked deps, minimal fakes, mount stub, a short ADR-0006, CI green. One test per acceptance bullet; skip anything no lane needs. The brief's acceptance list still defines done. |
| 8 | L6 | hero + features, Vercel | Keep, minimal (hero + features); **local build only** until the license check and the user's go-ahead. |
| 9 | Dropped | OG image, FAL/Skillry, stretch goals | Gone. |

**Time box (UTC, 2026-11-15):** W0 merged by ~00:45 · lanes merged by ~02:45 · W2 integration + Render deploy by ~03:45 (deploy as soon as one comparison works end to end) · W3 (README + diagram, demo video by the user, submission text through `/verify-claims`) by ~05:00.

**Unchanged (correctness rules):** `bin/jig` green; tests watched failing first; a blind `/judge` before each merge; merge on PASS + 5 green checks with a merge of `main` into the branch (no rebase, no force-push); three repairs then escalate; no secrets at import; frozen files stay frozen.

## Preconditions and human steps

| When | Who | Step |
|---|---|---|
| Before `w0` *merges* (no longer before it starts) | Jay / main session | Merge PR #11 after its judge PASS. Then set `pr11` to `merged` in this file (verified by `gh pr view 11 --json state -q .state` printing `MERGED`), and W0 merges `origin/main` into its branch. |
| On approval of this plan | orchestrator | Done 2026-11-14: issues #12–#20 created (table below); each task's branch is `jay/gh-<issue>-<slug>`. User chose "Approve, start L6 now": `l6-landing` dispatched; everything else waits on `pr11`. |
| After `w0` merges | Jay (the person merging) | Close Dependabot PRs #6–#10 as superseded (W0 absorbs them as lower bounds). Actions bumps #2–#5 are already merged; nothing to do. |
| Before `l6-landing` goes public | `l6-license` verdict | License name, source URL, date read, verdict recorded in ADR-0005 Consequences, replacing the pending note. |

Real keys (Anthropic, Keenable, Neon) are not needed for W0 or any W1 unit test; every lane tests against the W0 fakes. Keys are first needed in `w2`.

## Issues (created 2026-11-14 on approval; labels `type:task`, `type:decision` created to match `docs/tracker.md`)

| Task | Issue title | Branch (`N` = issue number) | Labels |
|---|---|---|---|
| `w0` | #12 W0: foundations — contracts, settings, fakes, locked deps, ADR-0006 | `jay/gh-12-w0-foundations` | `type:task` |
| `l1` | #13 L1: harness — pack loader, SpecialistRunner, Coordinator, InProcessRunService | `jay/gh-13-l1-harness` | `type:task` |
| `l2` | #14 L2: verifier — verify_claim, normalize, fuzzy match, dropped rules | `jay/gh-14-l2-verifier` | `type:task` |
| `l3` | #15 L3: domain packs (2 YAML: pricing, positioning_seo) and golden fixture set (1 comparison) | `jay/gh-15-l3-packs` | `type:task` |
| `l4` | #16 L4: persistence and API — one runs table, SqlRunRepo, /api/runs routes (Claude Code; was Codex) | `jay/gh-16-l4-api` | `type:task` |
| `l5` | #17 L5: Gradio UI — build_ui, live progress, battlecard, History list (Claude Code; was Mel) | `jay/gh-17-l5-ui` | `type:task` |
| `l6-license`, `l6-landing` | #18 L6: landing page — Aceternity license check (ADR-0005) and Next.js site on Vercel | `jay/gh-18-l6-license` (this repo); the site is its own repository `/Users/jay/Projects/receipts-landing` | `type:task`, `type:decision` |
| `w2` | #19 W2: integration and Render deploy (brief required) | `jay/gh-19-w2-integration` | `type:task` |
| `w3` | #20 W3: ship — README, diagram, demo video, OG image, submission text (brief required) | `jay/gh-20-w3-ship` | `type:task` |

No issue for `pr11`; it is issue #1 / PR #11, already open.

## Task graph

```toml plan-graph
[[task]]
id = "pr11"
title = "Precondition: PR #11 (spec, ADRs, AGENTS.md section 9) merged to main — human step, no agent dispatched"
scope = []
deps = []
parallel_safe = false
model = "opus"
exit = "gh pr view 11 --json state -q .state | grep -qx MERGED"
state = "merged"

[[task]]
id = "w0"
title = "W0 foundations (lean): contracts, settings, minimal fakes, conftest, locked deps, lane skeleton, /ui mount, short ADR-0006, one-line spec pointer"
scope = [
  "pyproject.toml",
  "uv.lock",
  "src/receipts/contracts.py",
  "src/receipts/settings.py",
  "src/receipts/fakes/__init__.py",
  "src/receipts/fakes/*.py",
  "src/receipts/harness/__init__.py",
  "src/receipts/verify/__init__.py",
  "src/receipts/packs/__init__.py",
  "src/receipts/db/__init__.py",
  "src/receipts/ui/__init__.py",
  "src/receipts/ui/app.py",
  "src/receipts/api/app.py",
  "src/receipts/api/models.py",
  "tests/conftest.py",
  "tests/test_api.py",
  "tests/test_openapi_export.py",
  "tests/test_contracts.py",
  "tests/test_settings.py",
  "tests/test_fakes.py",
  "docs/adr/0006-hackathon-gate-profile.md",
  "docs/superpowers/briefs/2026-11-14-w0-foundations-and-w1-lanes.md",
  "docs/superpowers/specs/2026-11-14-receipts-design.md",
  ".github/workflows/security.yml",
  "Dockerfile",
]
deps = []
parallel_safe = false
model = "opus"
exit = "uv lock --check && uv sync --frozen && bin/jig"
state = "blocked"

[[task]]
id = "w0-repair"
title = "W0 repair (re-plan after judge FAIL, same branch/PR #22): fake_llm.bind_tools, pyright strict = [\"src\"] + per-file basic in ui/, merge main, ADR-0006 fixes (licence status, protocol sync/async, mount_ui), canned data into fakes/"
scope = [
  "pyproject.toml",
  "uv.lock",
  "src/receipts/contracts.py",
  "src/receipts/settings.py",
  "src/receipts/fakes/__init__.py",
  "src/receipts/fakes/*.py",
  "src/receipts/harness/__init__.py",
  "src/receipts/verify/__init__.py",
  "src/receipts/packs/__init__.py",
  "src/receipts/db/__init__.py",
  "src/receipts/ui/__init__.py",
  "src/receipts/ui/app.py",
  "src/receipts/api/app.py",
  "src/receipts/api/models.py",
  "tests/conftest.py",
  "tests/test_api.py",
  "tests/test_openapi_export.py",
  "tests/test_contracts.py",
  "tests/test_settings.py",
  "tests/test_fakes.py",
  "docs/adr/0006-hackathon-gate-profile.md",
  "docs/superpowers/briefs/2026-11-14-w0-foundations-and-w1-lanes.md",
  "docs/superpowers/specs/2026-11-14-receipts-design.md",
  ".github/workflows/security.yml",
  "Dockerfile",
]
deps = []
parallel_safe = false
model = "opus"
exit = "uv lock --check && uv sync --frozen && bin/jig"
state = "merged"

[[task]]
id = "l1"
title = "L1 harness: load_pack, SpecialistRunner, Coordinator, InProcessRunService (Claude Code worktree)"
scope = ["src/receipts/harness/**", "tests/test_harness*.py"]
deps = ["w0-repair"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "blocked"

[[task]]
id = "l1-repair"
title = "L1 repair (re-plan after judge FAIL, same branch/PR #28): search receipt ts always from the logged row (HIGH), fetch-budget test, tool events in call order"
scope = ["src/receipts/harness/**", "tests/test_harness*.py"]
deps = []
parallel_safe = false
model = "sonnet"
exit = "bin/jig"
state = "merged"

[[task]]
id = "l2"
title = "L2 verifier: verify_claim, normalize, exact then rapidfuzz >= 90, search-log, dropped and fetch-failed rules; no Haiku note (Claude Code worktree)"
scope = ["src/receipts/verify/**", "tests/test_verify*.py"]
deps = ["w0-repair"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "blocked"

[[task]]
id = "l2-repair"
title = "L2 repair (re-plan after judge FAIL, same branch/PR #25): fuzzy match must cover the whole quote (short-page false positive), numbers in a quote must appear on the page, normalize idempotent on linked images"
scope = ["src/receipts/verify/**", "tests/test_verify*.py"]
deps = []
parallel_safe = false
model = "opus"
exit = "bin/jig"
state = "blocked"

[[task]]
id = "l2-repair2"
title = "L2 repair 2 of 3 (same branch/PR #25): number tokens per the ruling — [$€£]?\\d+(?:[.,]\\d+)?%? must appear verbatim in the page; tests for $19.99/$19.49+$99, 19%/19, $19/€19"
scope = ["src/receipts/verify/**", "tests/test_verify*.py"]
deps = []
parallel_safe = false
model = "sonnet"
exit = "bin/jig"
state = "merged"

[[task]]
id = "l3"
title = "L3 packs and golden set: 2 YAML DomainPacks (pricing, positioning_seo), 1 fixture comparison, golden claims (Claude Code worktree)"
scope = ["src/receipts/packs/**", "tests/fixtures/**", "tests/test_packs*.py"]
deps = ["w0-repair"]
parallel_safe = true
model = "sonnet"
exit = "bin/jig"
state = "merged"

[[task]]
id = "l4"
title = "L4 persistence and API: one runs table (SQLAlchemy 2), SqlRunRepo, POST/GET /api/runs, openapi.json (Claude Code worktree)"
scope = ["src/receipts/db/**", "src/receipts/api/**", "tests/test_db*.py", "tests/test_api*.py", "tests/test_openapi_export.py", "scripts/export_openapi.py", "docs/api/openapi.json"]
deps = ["w0-repair"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "blocked"

[[task]]
id = "l4-repair"
title = "L4 repair (re-plan after judge FAIL, same branch/PR #27): tests for event→row update and done-count fallback, placeholder rows disclosed+tested, empty passcode = unconfigured, engine-creation lock, PR body gaps"
scope = ["src/receipts/db/**", "src/receipts/api/**", "tests/test_db*.py", "tests/test_api*.py", "tests/test_openapi_export.py", "scripts/export_openapi.py", "docs/api/openapi.json"]
deps = []
parallel_safe = false
model = "sonnet"
exit = "bin/jig"
state = "merged"

[[task]]
id = "l4-constraints"
title = "L4 follow-up (accepted MEDIUM #3): integration tests that insert rows the runs-table constraints reject (duplicate id, NULL subject/rival/status/created_at) on Neon via DATABASE_URL; nothing persists"
scope = ["tests/test_db_constraints.py"]
deps = ["l4-repair"]
parallel_safe = false
model = "sonnet"
exit = "bin/jig"
state = "blocked"

[[task]]
id = "l4-constraints-repair"
title = "L4 constraints repair 1 of 3 (same branch/PR #32): right-reason sabotage for the duplicate-PK test, NULL-id case, docstring scope note, PR body to template"
scope = ["tests/test_db_constraints.py"]
deps = []
parallel_safe = false
model = "sonnet"
exit = "bin/jig"
state = "merged"

[[task]]
id = "l5"
title = "L5 Gradio UI: build_ui(service), live progress, battlecard with receipts and N of M verified, plain History list (Claude Code worktree)"
scope = ["src/receipts/ui/**", "tests/test_ui*.py"]
deps = ["w0-repair"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "merged"

[[task]]
id = "l6-license"
title = "L6 license check: Aceternity cryptgen template license read and recorded in ADR-0005 Consequences, replacing the pending note"
scope = ["docs/adr/0005-app-architecture-and-hosting.md"]
deps = ["pr11"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "merged"

[[task]]
id = "l6-license-followup"
title = "L6 licence wording follow-up (judge #1 MEDIUMs accepted at merge): label the private-repo condition as the author's reading, record the pricing FAQ's narrower reading, reconcile /terms, fix 'lists only'; dispatch only if time allows after W1"
scope = ["docs/adr/0005-app-architecture-and-hosting.md"]
deps = ["l6-license"]
parallel_safe = false
model = "sonnet"
exit = "bin/jig"
state = "merged"

[[task]]
id = "l6-landing"
title = "L6 landing page: Next.js 16 site (hero + features) in its own repository; preview build only until l6-license passes"
scope = []
deps = []
parallel_safe = true
model = "opus"
exit = "pnpm --dir ../receipts-landing build"
state = "blocked"

[[task]]
id = "l6-landing-fix"
title = "L6 landing fix (re-plan of l6-landing after FAIL verdict): two-pack copy, empty-env-safe app URL, Budgets/README wording, LICENSE-TEMPLATE file list"
scope = []
deps = []
parallel_safe = true
model = "sonnet"
exit = "NEXT_PUBLIC_APP_URL= pnpm --dir /Users/jay/Projects/receipts-landing build && pnpm --dir /Users/jay/Projects/receipts-landing build && pnpm --dir /Users/jay/Projects/receipts-landing lint"
state = "merged"

[[task]]
id = "w2"
title = "W2 integration + Render: live Keenable/Anthropic clients behind the protocols, SqlRunRepo + InProcessRunService wired into create_app when keys exist, passcode-enforcing UI starter, Dockerfile CMD ${PORT:-8000}, docs/api.md Deploy, runbook, seed script, one live run (brief: docs/superpowers/briefs/W2-integration.md)"
scope = ["src/receipts/harness/live.py", "src/receipts/harness/__init__.py", "src/receipts/api/app.py", "src/receipts/api/wiring.py", "src/receipts/ui/app.py", "Dockerfile", "docs/api.md", "docs/runbooks/**", "scripts/seed_demo_runs.py", "tests/test_integration_live.py", "tests/test_wiring.py", "tests/test_api.py", "docs/superpowers/briefs/W2-integration.md"]
deps = ["l1-repair", "l3", "l4-repair", "l5"]
parallel_safe = false
model = "opus"
exit = "bin/jig"
state = "judging"

[[task]]
id = "w3"
title = "W3 ship: README + Mermaid architecture, submission text through /verify-claims (claims-judge), landing page env/alias/copy fixes; demo video by the user; no OG image (brief: docs/superpowers/briefs/W3-ship.md)"
scope = ["README.md", "docs/assets/**", "docs/submission/**", "docs/superpowers/briefs/W3-ship.md"]
deps = ["w2", "l6-license", "l6-landing-fix"]
parallel_safe = false
model = "opus"
exit = "bin/jig"
state = "planned"
```

## Per-task dispatch notes

Every dispatch carries the brief, the task's TOML block, and the sentence: *"Touch only the paths in your scope. Run `bin/jig` before reporting. Report the jig summary line verbatim."* Every lane also gets: *"Import only from `receipts.contracts`, `receipts.settings`, `receipts.fakes` and your own folder. No network in unit tests; mark anything needing a key `@pytest.mark.integration`. If you need a frozen file changed, stop and ask."*

- **`w0`** — worktree `.worktrees/w0`, branch `jay/gh-12-w0-foundations` from `da06dd5` (PR #11 head; see Shape item 1). The orchestrator committed the brief and a snapshot of this plan as the branch's first commit; the live plan is the copy in the main checkout until a docs PR carries the final state. The implementer does not edit the plan. Before opening the PR: `git fetch origin && git merge origin/main` if `main` has moved; never rebase or force-push. Commit in the six slices above. The brief's Acceptance list is the full exit; `exit` here is the subset an agent runs locally, and the judge runs the rest (docker build, `bin/red-test`, pip-audit, gitleaks, `gh pr checks`). Deliberate asymmetry the judge must note, not fail: `# pyright: basic` in `src/receipts/ui/app.py` lets a bad def through where `contracts.py` would not. Dependabot #6–#10 are absorbed as lower bounds; the implementer does not touch those PRs.
- **`l1`–`l5`** — one Claude Code worktree each (`.worktrees/l1` … `.worktrees/l5`), branched from `main` after `w0` is merged. All five go out in one message with the brief's lane row, the Scope cut table, and the task block.
- **`l4`** — Claude Code (scope cut #1; no Codex brief). Scope mirrors the PR #11 update to AGENTS.md section 9 (adds `tests/test_openapi_export.py` and `scripts/export_openapi.py`). One `runs` table (scope cut #3). The W0 mount and redirect lines in `src/receipts/api/app.py` are not moved. L4 uses `FakeRunService` until W2. `l4` and `w0` both touch `src/receipts/api/app.py`; that is why `l4` depends on `w0` and is not a plan-check conflict (`w0` is not `parallel_safe`).
- **`l5`** — Claude Code (scope cut #1; no Mel brief, no H20 fallback needed). `build_ui(service: RunService)` replaces the W0 stub; `# pyright: basic` per file; `gr.Blocks(analytics_enabled=False)`; plain History list, minimal dark theme (scope cut #5).
- **`l6-license`** — tiny, but it is a go/no-go decision: read the template's license at its source, record license name, URL, date read and verdict in ADR-0005 Consequences. A "cannot confirm" verdict blocks `w3`'s public deploy, not the build.
- **`l6-landing`** — separate repository `/Users/jay/Projects/receipts-landing` (local `git init` only; no GitHub repo, no Vercel link until Jay takes the deploy step). Nothing in this repo is in scope. Hero + features only; testimonials, pricing and logo cloud removed. Preview deploy only until `l6-license` is `merged`. Its README link into this repo is `w3` work.
- **W2 facts (main session, 2026-11-14 ~23:50 UTC) — do NOT create another Render service:** web service exists: id `srv-dbsf8q0n74is739mv2jg`, URL https://receipts-h745.onrender.com, owner `tea-dbsf6i61egvs73dm3eug` (workspace mel-hackathon), region ohio (Neon is us-east-2), free plan, Docker from `./Dockerfile`, branch `main`, autoDeploy on (every merge to `main` redeploys — W0's merge will trigger one), healthCheckPath `/healthz`. Env vars set on the service (values also exist in the local `~/.zshenv` — `DATABASE_URL` is set locally, so integration tests run for real unless `env -u DATABASE_URL`): `ANTHROPIC_API_KEY`, `KEENABLE_API_KEY`, `DATABASE_URL`, `DEMO_PASSCODE`, `PORT=8000`, `MAX_CONCURRENT_SPECIALISTS=2`. `RENDER_API_KEY` is in `~/.zshenv` for API calls (logs, deploys, env). The first deploy of the stub app is running as a pipeline check. W2's Dockerfile `CMD` change to bind `${PORT:-8000}` stays compatible with `PORT=8000`. L6/W3: the landing page's `NEXT_PUBLIC_APP_URL` becomes https://receipts-h745.onrender.com. **W2 brief items collected from lane verdicts:** (i) constraint-rejection integration test on Neon `dev` for the `runs` table (L4 #3); (ii) guard test that the UI stream stops after `DoneEvent` with the real service (L5 MEDIUM); (iii) align `golden_claims.json` row 3 with L2's dropped/miss convention or compare `verified` only (L3 MEDIUM); (iv) decide on adding `greenlet` to the lock for a true async engine (L4 deviation); (v) ADR-0006:33 says `create_async_engine` and spec:48 lists five tables — correct both; (vi) `git_sha()` fallback to `RENDER_GIT_COMMIT`. **Observed 00:00 UTC after the W0 merge:** `GET /healthz` → `{"status":"ok","sha":"unknown","version":"0.1.0"}` — Render's build does not pass `--build-arg GIT_SHA`; W2 item: have `git_sha()` fall back to Render's `RENDER_GIT_COMMIT` env var (not a secret) so the deployed sha is visible, and confirm the autoDeploy picked up fbc8ae5.
- **`w2`, `w3`** — do not dispatch from this plan. Run `/improve-prompt` for each when its deps are `merged`, then update the scope here from that brief before `bin/plan-check --ready` is trusted for it.

## PR #11 round-3 judge notes folded into this plan (2026-11-14, all LOW)

1. **Fakes and their canned data live under `src/receipts/fakes/**`** (frozen): fake LLM responses, `FakeKeenable` pages and search results. Nothing W0 owns goes in `tests/fixtures/**`; that folder is L3's. — W0 judge rubric item.
2. **ADR-0006 pip-audit exceptions:** no `--ignore-vuln` may cover a direct dependency listed in `pyproject.toml` (fastapi, uvicorn, pydantic, …), even when gradio also pulls it in. A re-justified ignore keeps an expiry no later than 2026-11-30; after that date the flag is removed. — W0 judge rubric item.
3. **W2's scope gains `docs/api.md`** (its Deploy bullet still describes a registry push and fixed port 8000). — Applied to the `w2` block above.


## Escalations to the user

**Resolved 2026-11-14 ~23:25 UTC (relayed by the main session):** the user confirmed "Yes, I bought All-Access". PR #21's bullet was amended at `a5e3edf` (verdict now *permitted*, one condition: the landing-page repository stays private; pronoun fixed to "the repository owner"). The main session authorised the Vercel PREVIEW deploy (no `--prod`, no domain, no GitHub repo); dispatched ~23:30 UTC. Production deploy still waits for the main session's go-ahead. The record of the original escalation follows.

### RESOLVED 23:42 UTC — user accepted the production deployment ("It's ok, we need to move quickly", relayed by the main session)

L6 may deploy to production from now on. Constraint for W3: the public production alias must NOT be `receipts-landing.vercel.app` (owned by another account); W3 gives the project a free alias and links the page to the Render URL. Action taken on acceptance: promoted the judged build `d8179a3` (preview `dpl_2MGEpSGVSLUzCGGbuV9ww7S7CCJg`) to production with `vercel promote` (exit 0 → new production deployment `onif59s98`), so https://receipts-landing-nine.vercel.app serves the PASSed copy once that build is Ready. Investigation below kept for the record.

### (archived) landing deploy went to production, not preview (2026-11-14 23:27 UTC)

**Root cause, from the captured CLI output (`scratchpad/deploy-stderr.txt`, `deploy-stdout.txt`; verified token-free):** the command was `CI=1 npx -y vercel@65.16.0 deploy --token "$VERCEL_TOKEN" --yes </dev/null` run in `/Users/jay/Projects/receipts-landing` — **no `--prod` flag** (the only `--prod` string in the logs is inside Vercel's hint text). stderr, verbatim:
```
! This is the project's first deployment, so it will go to production.
✓ Created         jay-rodriguezs-projects/receipts-landing
  Production      https://receipts-landing-9xzczcjlh-jay-rodriguezs-projects.vercel.app
▲ Aliased         https://receipts-landing-nine.vercel.app
```
stdout JSON `hint`: "This is the project's first deployment, so it was assigned to production. Future deployments will be preview deployments unless you use --prod." The second run of the identical command (23:37 UTC, `ej6i6d4p1`) produced `environment: preview, target: null`, confirming the first-deployment rule. Lesson recorded: on a brand-new Vercel project, create the project first (`vercel project add` / `vercel link`) or accept that the first `deploy` is production; the orchestrator's dispatch did not anticipate this.

The authorised action was a PREVIEW deploy. `vercel deploy` was run without `--prod`, but Vercel CLI 65.16.0 assigns a project's **first** deployment to production regardless (CLI stderr verbatim: "This is the project's first deployment, so it will go to production."). Result, verified by the orchestrator with curl at 23:27 UTC:

- Project `jay-rodriguezs-projects/receipts-landing` (new; no Git link, no GitHub repo, no custom domain; source uploaded from the local directory).
- Deployment `dpl_HyofRSS3CGpJ5pxKPnWojxUXPzKf`, target `production`.
- Public alias **https://receipts-landing-nine.vercel.app → HTTP 200**, page text "Every claim carries a receipt" present.
- Unique URL https://receipts-landing-9xzczcjlh-jay-rodriguezs-projects.vercel.app → 302 to Vercel SSO (deployment protection on).
- Token not printed or written anywhere (captured deploy logs grep 0 for the name and the literal value).

**Also for the user (one line, LOW-4 from the #21 judge):** post a one-line comment on issue #18 confirming the All-Access purchase, so the ADR's "confirmed on 2026-11-14" has a citable place rather than a relayed message.

**Preview of the fixed build (23:40 UTC):** `d8179a3` deployed as a true preview — `environment: preview`, `target: null` — at https://receipts-landing-ej6i6d4p1-jay-rodriguezs-projects.vercel.app (id `dpl_2MGEpSGVSLUzCGGbuV9ww7S7CCJg`; inspect https://vercel.com/jay-rodriguezs-projects/receipts-landing/2MGEpSGVSLUzCGGbuV9ww7S7CCJg). It returns 302 to Vercel SSO for anonymous visitors (deployment protection), so only a logged-in Vercel user can view it; the fixed copy is therefore judged (PASS) but not curl-confirmed on Vercel. `vercel ls`: preview `ej6i6d4p1` Ready, production `9xzczcjlh` Ready (the old copy).

**Decision needed from the user** — one of: (a) promote the fixed preview to production (`CI=1 npx -y vercel@65.16.0 promote dpl_2MGEpSGVSLUzCGGbuV9ww7S7CCJg --token "$VERCEL_TOKEN" --yes </dev/null`; the alias https://receipts-landing-nine.vercel.app then serves the judged copy); (b) remove the production deployment (command below) and keep only the protected preview until W3; (c) leave both as they are. No further Vercel action by the orchestrator until then. Original note: (a) accept the production deployment as-is (the `l6-landing` judge returned **FAIL** at 23:29 UTC — the live page says "four domain specialists" where the scope cut ships two; fix in progress as `l6-landing-fix`), or (b) remove it with `CI=1 npx -y vercel@65.16.0 remove dpl_HyofRSS3CGpJ5pxKPnWojxUXPzKf --token "$VERCEL_TOKEN" --yes </dev/null`, after which any later `vercel deploy` without `--prod` is a true preview because the project now exists. Note: the app link on the page is `#` because `NEXT_PUBLIC_APP_URL` is unset until W2.

### (archived) Aceternity licence conditions, as first raised

1. **Aceternity licence conditions (from `l6-license`, PR #21, 2026-11-14):** verdict *permitted with conditions*. (a) The landing-page repository must stay **private** — the licence page (https://ui.aceternity.com/licence) forbids redistributing "source files, regardless of modifications", and a public repo would do that; this is the implementer's inference, stated as such in the ADR bullet. (b) The cryptgen template is sold only with Aceternity All-Access; **whether Jay holds that licence is for Jay to confirm** before any public deploy. Neither the orchestrator nor the judge can resolve (b). Effect on the graph: `w3`'s public deploy of `l6-landing` waits on Jay's confirmation of (b) and on the landing repo being created private.

   **Updated L6 rule (main session, 2026-11-14 ~23:40 UTC):** Vercel access exists (`VERCEL_TOKEN` in `~/.zshenv`; non-interactive form `CI=1 npx -y vercel@65.16.0 <cmd> --token "$VERCEL_TOKEN" --yes </dev/null`). Order: licence check first → if the verdict allows public deployment, a PREVIEW deploy (`vercel deploy`, no `--prod`) may run → production deploy, custom domain or a GitHub repo wait for the main session's go-ahead from the user. "Not allowed" or unclear → no deploy.
   **Orchestrator decision:** no preview deploy yet. The licence allows public deployment *for a licence holder*; condition (b) leaves open whether Jay is one, so the deploy's permissibility is unresolved until he confirms. Preview deploy runs as soon as (1) Jay confirms All-Access and (2) the `l6-landing` judge verdict is PASS. A `vercel deploy` from the local directory uploads source to Vercel only; it creates no GitHub repository, so condition (a) is not triggered by a preview.

## W1 wiring convention (set at dispatch, 23:56 UTC)

`create_app()` (W0, zero-arg, boots with an empty environment) stays. The run service is looked up at request/mount time from `app.state.run_service: RunService`; when absent, both L4's routes and L5's `mount_ui` fall back to a `FakeRunService` built from `receipts.fakes` sample events (demo mode). W2 sets `app.state.run_service = InProcessRunService(...)` and wires `SqlRunRepo`. L1 exposes the Verifier as an injected callable `verify_claim(claim, pages, searches) -> Claim` defaulting to a pass-through; W2 wires `receipts.verify.verify_claim`. These are conventions, not frozen contracts; a lane that needs them changed stops and asks.

## Coordinator rulings 2026-11-15 01:11 UTC

- **Merge order is now first-PASS-first** (L3 and L5 merged; scopes disjoint), replacing L3 → L2 → L1 → L4 → L5.
- **L2 finding 2 decided:** a `quote_fuzzy` match also requires every number token in the quote (digits, with any currency sign, decimal point or %) to appear verbatim in the normalized page text; exact-substring matches unaffected; recorded in the L2 PR body as a deliberate tightening of spec line 41. Implemented in `l2-repair` as digit-run containment (`\d+`); the re-judge checks it against the ruling's wording.
- **L4 constraint tests** may run against `DATABASE_URL` as `@pytest.mark.integration` (rows the constraints reject leave no data). The `l4-repair` re-judge was already running with #3 accepted; the constraint test is added as a small follow-up after #27 merges rather than moving the head mid-review.

### Coordinator spec for L2 repair attempt 2 (01:20 UTC) — binding for `l2-repair2` and its re-judge

- Number token = regex `[$€£¥]?\d+(?:[.,]\d+)*%?` applied to the normalized quote and the normalized page text (same `normalize()` for both).
- A `quote_fuzzy` match additionally requires: every number token in the quote appears as a whole token in the page's token list (compare as strings, after stripping only thousands-separator commas, so "1,000" == "1000"; keep the currency sign and % as part of the token; "19.99" is ONE token, never split).
- Exact-substring matches are unchanged.
- Tests (write first, watch them fail): must NOT verify — `19%` vs page `19`; `$19.99` vs page `$19.49` with a `$99` tier also on the page; `19%` vs page `10%` with `19` elsewhere; `$19` vs page `€19`. Must verify — `$19.99/mo` vs page `$19.99 per month` (fuzzy); "1,000 seats" vs page "1000 seats"; the earlier 19-vs-14 dollars case still fails.
- Third failure → stop and escalate to the main session with the trace (three-repair rule).
- Execution note: `l2-repair2` was dispatched at 01:19 with a near-identical spec (regex without `¥`, single decimal group, no thousands-separator handling, four negative tests, one positive). Its deltas against this spec are applied as a follow-up within the same attempt before the re-judge.

## W1 complete — 01:30 UTC

All five lanes merged to `main`: L3 (#24), L5 (#26), L4 (#27), L1 (#28), L2 (#25). Nine blind verdicts: 4 first-pass FAILs (W0, L1, L2, L4), 1 second FAIL (L2), all repaired within the three-attempt rule; no lane needed a third repair. W2 (#19) was dispatched at 01:27 from `main` before L2 landed and must merge `main` before its judge.

## Status sync 01:45 UTC (user has SUBMITTED; goal now: live runs on Render)

- Judge A (started 01:39) reviews **#29 W2** at lane head 9907644 (branch head 21958f6 after a README-only `main` merge at 01:43). Judge B (started 01:44) reviews **#32 l4-constraints** at 7583d85. Both branches up to date with `main` (2244225); no force-push anywhere.
- Orchestrator is not mid-merge. The main session may merge #29 on PASS; the orchestrator then records it, checks Render `/healthz` sha, and dispatches W3. #32 is lower priority and shares no resource with #29.

### W2 second opinion (orchestrator's judge, 01:39–01:52 UTC) — FAIL, posted on #29, no action taken on the branch

File `verdicts/2026-11-15-w2-orchestrator-judge.md` (copied from `2026-11-15-w2.md` to avoid colliding with the main session's judge at that path). H1: `git_sha()` fallback unreachable because the Dockerfile always sets `GIT_SHA=unknown` → production `/healthz` stays `unknown`; M1: partial config (no Anthropic key) yields a fake battlecard on a public URL silently; M2: PR body omits two carried items; 9 LOW. Clean on secrets, passcode, gates. Live run `run-6a5fe9499c4d 25/25 27.4s`, 12/12 spot-checked quotes on-page. Decision on #29 belongs to the main session.

## Merging (delegated) and judging

**Delegation, 2026-11-14:** the user delegated merging to the orchestrator (relayed by the main session: "are you merging them as well I need to submit ASAP"). A PR is squash-merged without waiting for the user when, and only when, both are true and read from GitHub, not from a report: (1) the blind `/judge` verdict is PASS, and (2) all five required checks (`gitleaks`, `leak-gate`, `dependency-audit`, `ci-python`, `api-image`) are green on the PR head (`gh pr checks <PR>`). Before merging, the branch is brought up to date with `git merge origin/main` (no rebase, no force-push). Order: W0 → L3 → L2 → L1 → L4 → L5. A FAIL verdict follows the three-repair rule and escalates to the main session; it never bypasses the judge.

- Each lane: `bin/jig` green → `judging` → `judge` dispatched with the task id → PASS + 5 green checks → orchestrator squash-merges → `merged`. Dependents (`w2`) wait for `merged`, not for a report of done.
- Human merge order for W1: L3 → L2 → L1 → L4 → L5, each rebased onto `main` first (strict ruleset). L6 is independent.
- Third jig failure on any task → `blocked`, last trace pasted here, escalate. Never widen a scope to make a task pass; return it to `planned` with a split.

## Resume

A new session reads this file, runs `bin/plan-check docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md --ready`, and proceeds with what it lists. The `pr11` sentinel is flipped to `merged` only after `gh pr view 11 --json state -q .state` prints `MERGED`.

## Verdicts and PRs

| Task | State | PR | Judge verdict |
|---|---|---|---|
| pr11 | merged (PR #11 squash-merged as bd42bc9, judge round 3 PASS; read via `gh pr view 11` 2026-11-14 23:1x UTC) | #11 | main session's round-3 verdict |
| w0 | **blocked** — judge FAIL 23:42 UTC: 0 HIGH, 3 MEDIUM (M1 `fake_llm` lacks `bind_tools` → `create_agent` raises; M2 pyright strict list omits `src/receipts/__init__.py`/future top-level modules; M3 branch behind main). All else passed (scope, gates, secrets, types, sabotage a–d, 24 tests 0 skipped, 5/5 checks on dbc46d8). Re-planned as `w0-repair`. | [#22](https://github.com/JayR1031/receipts/pull/22) | FAIL `verdicts/2026-11-14-w0.md` |
| w0-repair | **merged** 23:55 UTC as fbc8ae5 (squash). Judge PASS on 2804935: M1–M3 fixed with sabotage confirmation, 3 LOW (ADR-0006 wording on `events()` being a plain def returning AsyncIterator; PR body file count 73→74; brief step 5 stale vs ADR-0006). Dependabot #6–#10 closed as superseded. | [#22](https://github.com/JayR1031/receipts/pull/22) | PASS `verdicts/2026-11-14-w0-repair.md` |
| l1 | **blocked** — judge FAIL 01:11 UTC: 1 HIGH (model-supplied `ts` overwrites the logged search row's `ts`, `specialist.py:130,161-163`; probe showed an invented 2001 timestamp on a verified claim), 8 LOW. Rulings: dynamic `importlib` of `langchain.agents` PASS-with-LOW (hides only library-side `Unknown`s, not L1 errors); `ChatAnthropic(model_name=, effort=)` PASS. All gates green. Re-planned as `l1-repair`. | [#28](https://github.com/JayR1031/receipts/pull/28) | FAIL `verdicts/2026-11-14-l1.md` |
| l1-repair | **merged** 01:23 UTC as 9a2054d (squash). Re-judge PASS on bb8d738 (head 0d636bf incl. main): HIGH fixed (two sabotages red), LOWs #2 #3 #4 fixed, 5 LOW carried — **W2 items:** `_search_ts` should also match `rank` (a claim can be verified by one row and carry another's `ts`); `ToolLog` lists should derive from `calls`; event `ts` is replay-time. | [#28](https://github.com/JayR1031/receipts/pull/28) | PASS `verdicts/2026-11-14-l1-repair.md` |
| l2 | **blocked** — judge FAIL 00:14 UTC: 1 HIGH (`partial_ratio` slides the shorter string: a page shorter than the quote verifies a made-up quote at 100), 1 MEDIUM (changed price 19→14 still verifies at 97.8), 2 LOW (normalize not idempotent on `[![alt](img)](url)`; sabotage restore not evidenced). All else passed (scope, purity, rule order, 29 tests, 5/5 checks). Re-planned as `l2-repair`. | [#25](https://github.com/JayR1031/receipts/pull/25) | FAIL `verdicts/2026-11-14-l2.md` |
| l2-repair | **blocked** — re-judge FAIL 01:18 UTC: 0 HIGH, 1 MEDIUM (digit-run numbers check weaker than the coordinator's ruling: `19%` vs `19`, `$19.99` vs `$19.49` with a `$99` tier on the page, `$19` vs `€19` still verify as `quote_fuzzy`); HIGH #1 confirmed fixed (coverage held in 0 of 92,814 shorter-page probe pairs); LOW #3 fixed; 5/5 checks. Repair attempt 2 of 3 → `l2-repair2`. | [#25](https://github.com/JayR1031/receipts/pull/25) | FAIL `verdicts/2026-11-14-l2-repair.md` |
| l2-repair2 | **merged** 01:30 UTC as 45bf333 (squash). Attempt-2 verdict PASS on ee909a0: 0 HIGH; 3 MEDIUM accepted by the judge with reason (coverage/evidence gaps, behaviour correct by probe): no test exercises `¥` or multi-group separators; no red-first record for repair 2b; PR body lacked final-state evidence. 4 LOW incl. **LOW 7 for the owner:** exact-substring match verifies a cut-off number (`$19` in `$199`) — follows spec line 41 literally, contradicts the receipts rationale; fix would be a word/number-boundary check on exact matches. Spec note: `$19.99/mo` passes only with enough context (92.1 at 98 chars). Follow-ups queued for W3/time-permitting. | [#25](https://github.com/JayR1031/receipts/pull/25) | PASS `verdicts/2026-11-14-l2-repair2.md` |
| l3 | **merged** 00:10 UTC as a6fe91a (squash; first in order). Judge PASS: 0 HIGH, 1 MEDIUM accepted (golden_claims row 3 has `verify_method: quote_exact` + a meaning-based note on an unverified claim; L2's convention is `None` + rule note — **W2 aligns the golden row or compares `verified` only**), 6 LOW carried (positioning_seo `timeout_s: 150` > 120 default; prompts don't state budgets; search-result URL subset untested; PR body omits red-test line; `fixtures` package name relies on pytest default import mode; plan issue-table row stale). | [#24](https://github.com/JayR1031/receipts/pull/24) | PASS `verdicts/2026-11-14-l3.md` |
| l4 | **blocked** — judge FAIL 00:19 UTC: 0 HIGH, 3 MEDIUM (#1 event→row update and done-count fallback untested — sabotage left 67 tests green; #2 placeholder rows on early events undisclosed/untested; #3 no constraint-rejection test), 6 LOW. All else passed (scope, startup, schema, to_thread deviation, compare_digest, OpenAPI, 5/5 checks). **#3 accepted with reason:** scope cut row 3 puts Neon in W2; the constraint-rejection integration test is a W2 brief item. Re-planned as `l4-repair`. | [#27](https://github.com/JayR1031/receipts/pull/27) | FAIL `verdicts/2026-11-14-l4.md` |
| l4-repair | **merged** 01:16 UTC as 58e8e06 (squash). Re-judge PASS on a95a7ec: M1/M2 fixed (sabotage 6/10 and 2/14 red), #3 accepted → follow-up, 5 LOW carried (PR-body sabotage counts from an earlier commit; integration docstring says `dev`; two placeholder claims untested; #3 home settled below; ADR/spec wording open). **#3 home settled: a small `l4-constraints` follow-up PR (integration test on Neon, allowed by the coordinator 01:11) — dispatched after W1 merges complete if time allows, else W2.** | [#27](https://github.com/JayR1031/receipts/pull/27) | PASS `verdicts/2026-11-14-l4-repair.md` |
| l4-constraints | **blocked** — judge FAIL 01:47 UTC: 0 HIGH, 1 MEDIUM (dup-PK test never seen red for the right reason), 4 LOW (NULL-id case missing; varchar lengths out of scope but docstring overclaims; tests hit the demo DB not a `dev` branch — accepted by the coordinator; PR body not template-shaped). Neon run 6 passed; leftover 0; `runs` has 1 row total. | [#32](https://github.com/JayR1031/receipts/pull/32) | FAIL `verdicts/2026-11-15-l4-constraints.md` |
| l4-constraints-repair | **merged** 01:56 UTC as 46d9d11 (squash). Re-judge PASS on 6d261ec: MEDIUM resolved (sabotage reproduced: `DID NOT RAISE` at :89, exit 1), LOWs #2 #3 #5 resolved; 4 new LOW carried (NULL-id test counts the whole table on a shared DB and has no `finally`; docstring pronoun; two reds lack exit codes; verdict path untracked in the repo). | [#32](https://github.com/JayR1031/receipts/pull/32) | PASS `verdicts/2026-11-15-l4-constraints-repair.md` |
| l5 | **merged** 00:17 UTC as 75f17b3 (squash). Judge PASS on 1644bde: 0 HIGH, 1 MEDIUM accepted with reason (no test that `run_stream` stops after `DoneEvent`; judge's probe showed it does; **W2 item:** add that guard test when wiring the real service), 5 LOW carried (History load/select handlers untested; `fetch failed` render branch untested; demo-fallback test weak; Refresh/row-select slightly beyond 'plain list'; PR body numbers lack their set). **Order deviation:** merged before L1/L4 — disjoint scope, L2 in repair, L1 had no PR; recorded for the main session. | [#26](https://github.com/JayR1031/receipts/pull/26) | PASS `verdicts/2026-11-14-l5.md` |
| l6-license | **merged** 23:33 UTC as 6628208 (squash, edited message). Judge #2 on merge head a5e3edf: PASS, 0 HIGH, 0 MEDIUM, 6 LOW. Judge #1 (dispatched on 4efd4dd): FAIL, 3 MEDIUM — accepted at merge with reason: judge #2 rated the same labelling point LOW-5; the unlabelled condition is the more cautious reading; `/terms` opens "Unless otherwise stated" so the item licence governs; the stale PR body was superseded by the edited squash message. Wording fixes queued as `l6-license-followup`. | [#21](https://github.com/JayR1031/receipts/pull/21) | PASS `verdicts/2026-11-14-l6-license-a5e3edf.md`; FAIL (superseded head) `verdicts/2026-11-14-l6-license.md` |
| l6-license-followup | **merged** 23:4x UTC as d5e43e1 (squash). Judge PASS on e234631: 0 HIGH, 0 MEDIUM, 5 LOW carried (clause source page unnamed after edit; `/terms` sentence thin; owner-confirmation location; PR body inaccuracies). | [#23](https://github.com/JayR1031/receipts/pull/23) | PASS `verdicts/2026-11-14-l6-license-followup.md` |
| l6-landing | **blocked** (judge FAIL: 2 HIGH, 2 MEDIUM; re-planned as `l6-landing-fix`) | — (separate repo; production deploy exists, see Escalations) | `docs/superpowers/plans/verdicts/2026-11-14-l6-landing.md` |
| l6-landing-fix | **merged** (judge PASS 23:38 UTC; d8179a3 is `main` of `/Users/jay/Projects/receipts-landing`, no PR — external repo). LOWs carried for a later pass: live-panel wording (L1), 'adding a domain means adding a file' overstates (L2), 'quote is found' omits fuzzy ≥90 (L3), four template files unlisted in LICENSE-TEMPLATE.md (L4), old local path in git history (L5), illustration row 3's search receipt cannot support a page-title claim (L6). Recheck copy after L3/L5 merge. Preview deploy of d8179a3 dispatched 23:39 UTC. | — | PASS `verdicts/2026-11-14-l6-landing-fix.md` |
| w2 | judging (lane head 9907644 incl. L2, README-only main merge → 21958f6; orchestrator observed 01:38 UTC: CLEAN, 5/5 checks incl. api-image, 12 files in scope, shell-form CMD `${PORT:-8000}`, 38 targeted tests pass, pyright 0, empty-env boot 0). Implementer's live run: `run-f817acdb7ff6 22/22 22.0s` (Mel vs Warp, 01:34 UTC, temp SQLite). Not done: Docker locally (daemon down; CI api-image green), Neon seed, Render run (no deploy yet). Design: `LazyRunService` proxy on `app.state.run_service`, resolves per call under a lock; `app.state.run_starter` enforces passcode + key for the UI. | [#29](https://github.com/JayR1031/receipts/pull/29) | pending |
| w3 | planned (#20) — brief written 01:35 UTC at `docs/superpowers/briefs/W3-ship.md` (untracked in the main checkout; committed with the W3 branch at dispatch). Dispatch when `w2` is merged and Render serves it. Landing-page work (env var, `--prod` redeploy, free alias ≠ receipts-landing.vercel.app, copy fixes from the L6 LOWs) is in W3's scope, outside this repo. | — | — |
