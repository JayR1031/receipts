# Plan: Wave 0 foundations, then the W1 lanes in parallel

Brief: `docs/superpowers/briefs/2026-11-14-w0-foundations-and-w1-lanes.md`. Spec: `docs/superpowers/specs/2026-11-14-receipts-design.md`. Lane globs: `AGENTS.md` section 9. Written 2026-11-14 (hackathon H0–1); nothing dispatched yet.

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
| `l3` | #15 L3: domain packs (4 YAML) and golden fixture set (3 comparisons) | `jay/gh-15-l3-packs` | `type:task` |
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
state = "planned"

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
state = "running"

[[task]]
id = "l1"
title = "L1 harness: load_pack, SpecialistRunner, Coordinator, InProcessRunService (Claude Code worktree)"
scope = ["src/receipts/harness/**", "tests/test_harness*.py"]
deps = ["w0"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "planned"

[[task]]
id = "l2"
title = "L2 verifier: verify_claim, normalize, exact then rapidfuzz >= 90, search-log, dropped and fetch-failed rules; no Haiku note (Claude Code worktree)"
scope = ["src/receipts/verify/**", "tests/test_verify*.py"]
deps = ["w0"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "planned"

[[task]]
id = "l3"
title = "L3 packs and golden set: 2 YAML DomainPacks (pricing, positioning_seo), 1 fixture comparison, golden claims (Claude Code worktree)"
scope = ["src/receipts/packs/**", "tests/fixtures/**", "tests/test_packs*.py"]
deps = ["w0"]
parallel_safe = true
model = "sonnet"
exit = "bin/jig"
state = "planned"

[[task]]
id = "l4"
title = "L4 persistence and API: one runs table (SQLAlchemy 2), SqlRunRepo, POST/GET /api/runs, openapi.json (Claude Code worktree)"
scope = ["src/receipts/db/**", "src/receipts/api/**", "tests/test_db*.py", "tests/test_api*.py", "tests/test_openapi_export.py", "scripts/export_openapi.py", "docs/api/openapi.json"]
deps = ["w0"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "planned"

[[task]]
id = "l5"
title = "L5 Gradio UI: build_ui(service), live progress, battlecard with receipts and N of M verified, plain History list (Claude Code worktree)"
scope = ["src/receipts/ui/**", "tests/test_ui*.py"]
deps = ["w0"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "planned"

[[task]]
id = "l6-license"
title = "L6 license check: Aceternity cryptgen template license read and recorded in ADR-0005 Consequences, replacing the pending note"
scope = ["docs/adr/0005-app-architecture-and-hosting.md"]
deps = ["pr11"]
parallel_safe = true
model = "opus"
exit = "bin/jig"
state = "planned"

[[task]]
id = "l6-landing"
title = "L6 landing page: Next.js 16 site (hero + features) in its own repository; preview build only until l6-license passes"
scope = []
deps = []
parallel_safe = true
model = "opus"
exit = "pnpm --dir ../receipts-landing build"
state = "running"

[[task]]
id = "w2"
title = "W2 integration and Render deploy (PROVISIONAL scope; needs its own brief before dispatch)"
scope = ["Dockerfile", "src/receipts/api/app.py", "tests/test_e2e*.py", "tests/test_integration*.py", "docs/runbooks/**"]
deps = ["l1", "l2", "l3", "l4", "l5"]
parallel_safe = false
model = "opus"
exit = "bin/jig"
state = "planned"

[[task]]
id = "w3"
title = "W3 ship: README + diagram, submission text through /verify-claims; demo video by the user; no OG image (PROVISIONAL scope; needs its own brief)"
scope = ["README.md", "docs/submission/**", "docs/assets/**"]
deps = ["w2", "l6-license", "l6-landing"]
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
- **`w2`, `w3`** — do not dispatch from this plan. Run `/improve-prompt` for each when its deps are `merged`, then update the scope here from that brief before `bin/plan-check --ready` is trusted for it.

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
| pr11 | planned (judge round 3 in progress, main session; no longer gates w0) | #11 | — |
| w0 | running (dispatched 2026-11-14 from da06dd5, `.worktrees/w0`) | #12 — PR opened by implementer | — |
| l1 | planned (#13) | — | — |
| l2 | planned (#14) | — | — |
| l3 | planned (#15) | — | — |
| l4 | planned (#16) | — | — |
| l5 | planned (#17) | — | — |
| l6-license | planned (#18) | — | — |
| l6-landing | running (dispatched 2026-11-14) | — (separate repo, local only) | — |
| w2 | planned (#19) | — | — |
| w3 | planned (#20) | — | — |
