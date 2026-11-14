# Receipts — verified competitive-intel crew (Miami AI Hackathon, 48 h, solo)

> "Receipts" (every claim shows its receipt) is Claude's working name; rename freely.

## Context

Jay is entering the Miami AI Hackathon solo with ~48 hours to submit. Tracks: **02 Agentic Marketing** (competitive intelligence, SEO/AEO/GEO: search, answer-engine and generative-engine optimization, meaning how a brand shows up in search engines and in AI assistants' answers) and **08 Research, Productivity & Developer Agents** (research bots, result verification). Jay's stack decisions: Gradio UI, LangChain, Keenable web search, FastAPI/Starlette, Neon Postgres, and an **agent harness that makes each agent domain-specific**. The build fans out across three builders: **Claude Code** worktree agents, **Codex** (Jay's other terminal), and **Mel** (the hackathon-promoted agentic terminal; Jay chose to split work between Claude Code and Mel).

The product: a founder/marketer/sales rep types "Us vs. Rival" and gets a one-page battlecard where **every line carries a receipt** — a source URL plus a verbatim quote re-checked against the fetched page, or a logged search result. Claims without a receipt are dropped and counted ("23 of 27 verified"). That answers the judges' first question about any research agent: "how do you know it didn't make that up?"

## Goals / non-goals / anti-goals
> Scope cut 2026-11-14: see `docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md`, section "Scope cut 2026-11-14"; it overrides this spec and the W0 brief where they differ.

- **Must ship:** 4 specialists + Verifier on one harness; live agent progress in Gradio; battlecard with receipts and a verified/total score; runs in Neon with a History tab; public URL; 2-min demo video; README with architecture diagram; a landing page on Vercel (below).
- **Landing page (must ship, lane L6; Jay's decision 2026-11-14):** a one-page site built from the Aceternity "cryptgen" template (Next.js 16), kept in its own repository outside this one, using only its hero and features sections, deployed on Vercel and linking to the Render app. Before it is published, confirm the Aceternity license allows a public deployment, and record the answer in ADR-0005. Its fake testimonials, pricing and logo cloud are cut, because invented social proof contradicts a product about receipts.
- **Stretch (only if ahead at H30):** "what changed since last run" diff; adding a 5th pack live during the demo.
- **UI look (L5 brief):** the dark spotlight/glow style of that template, done with a Gradio theme and custom CSS. No Node build.
- **Non-goals:** user accounts, scheduling, scraping behind logins, PDF export, voice.
- **Anti-goals:** any claim shown without a receipt; a demo that hangs >2 min or dies on a rate limit; specialists written as copy-pasted code instead of config; secrets in git; strangers burning Jay's API budget on the public URL.

## Architecture

```
Gradio Blocks at /ui ─┐   FastAPI: POST /api/runs → run_id (202), GET /api/runs/{id}, GET /api/runs, /healthz, / → 302 /ui
                      ▼
RunService (in-process): starts run as background task, exposes async event stream per run_id
                      ▼
Coordinator → asyncio.gather(4 × SpecialistRunner(DomainPack)) → Verifier → Battlecard
                      ▼                                    events ──► RunRepo subscriber (Neon)
LangChain 1.x create_agent + ToolCallLimitMiddleware; tools: KeenableSearch / KeenableFetch (langchain-keenable)
```
One uvicorn process; Gradio mounted with `gr.mount_gradio_app` (FastAPI is Starlette underneath). The UI reads the **in-process** event stream (Gradio generator), not HTTP polling.

**Harness = domain packs** (`src/receipts/packs/*.yaml`, loaded with `importlib.resources` so they ship in the image): `id, display_name, model, effort, system_prompt, query_templates[] ({subject}/{rival}/{category}), source_allow/deny, max_searches=3, max_fetches=4, timeout_s, extra_fields, rubric`. One generic `SpecialistRunner`; adding a specialist = adding a YAML file. Packs:
- `pricing` — pricing pages, plan comparisons.
- `positioning_seo` — (a) messaging claims quoted from each brand's own pages and review sites; (b) **AI-search visibility**: rank of each brand across N category queries in Keenable's index (what AI agents see when they search), receipt = the logged search result. *Claude's call; no external chatbot is called.*
- `news_social` — press and Reddit, last 90 days.
- `product` — docs and changelogs.

**Wave 0 contracts (frozen; only W0 edits them):** `Claim{domain, about: subject|rival, text, receipt: QuoteReceipt{url, quote} | SearchReceipt{query, rank, url, ts}, verified, verify_method: quote_exact|quote_fuzzy|search_log, verify_note}`; `RunEvent` as a **typed union per kind** (started/search/fetch/claim/verified/dropped/done/error — no `dict[str, Any]`, per the kit's AGENTS.md); `Battlecard`; `RunService` and `RunRepo` protocols **with in-memory fakes**; fake LLM + fake Keenable fixtures. Every lane builds and tests against fakes; real wiring happens in W2.

**Verifier rules:** a claim may only cite a URL fetched in this run, or a search row logged in this run. Full page text is cached per run; agents see a truncated copy. Strip markdown → normalize (case, whitespace, quotes, dashes) → exact substring, else `rapidfuzz.partial_ratio ≥ 90`. A Haiku call may only add `verify_note`; it never marks a claim verified. A non-dict/string result from `KeenableFetch` counts as **fetch failed**, not "claim false".

**Models (Claude's call):** `claude-sonnet-5-5` for specialists with `effort` set per pack (W0 confirms `langchain-anthropic` passes it through; if not, use the closest supported param), `claude-haiku-5-5` for verify notes. Tool budgets enforced with `ToolCallLimitMiddleware` on the exact tool names. `MAX_CONCURRENT_SPECIALISTS` setting (default 4) in case the Anthropic tier rate-limits.

**Keenable:** refuse to start a run without `KEENABLE_API_KEY` (the langchain-keenable 0.1.2 README, read on PyPI 2026-11-14, says that without a key "both search and fetch transparently fall back to their keyless public endpoints", so a missing key would not raise an error).

**Neon (Claude's call):** `dev` branch for building, `main` for the demo. Settings rewrite `postgresql://` → `postgresql+psycopg://`; `pool_pre_ping=True` (Neon suspends idle compute). Portable SQLAlchemy 2 types so unit tests run on SQLite. Tables: `runs, sources, search_results, claims, events`. SQLite is for fast unit tests only: every schema constraint (NOT NULL, foreign key, CHECK, unique) is proven by an integration test against the Neon `dev` branch that inserts the row the constraint exists to stop (AGENTS.md §4).

**Public URL safety (Claude's call):** anyone can open History and the 3 stored demo runs; starting a live run needs `DEMO_PASSCODE`. Nothing reads secrets at import/startup (the kit's CI image check runs with no secrets).

**Deploy (Claude's call, changed after review):** **Render free web service** from the kit's Dockerfile. Hugging Face Spaces is out: HF's Spaces overview (https://huggingface.co/docs/hub/spaces-overview, read 2026-11-14) says Docker Spaces need a paid plan and outbound traffic is limited to ports 80/443/8080, so Neon's 5432 is blocked. Render's free-tier page (https://render.com/docs/free, read 2026-11-14) says the free tier blocks only ports 25/465/587, and that a service sleeps after 15 min idle and takes about a minute to wake, so hit the URL before judging. Uvicorn must bind `${PORT:-8000}`; today's Dockerfile CMD fixes port 8000 in exec form, so W2 changes it (and drops its stale `infra/terraform` comment).

## Repo bootstrap (Jay's agentic-standard kit)

`bin/new-project --answers receipts.toml` (agentic-standard kit) with
`name="Receipts", slug="receipts", stack="python", presets=["api-fastapi"], cloud="none", tracker="github", vendors=["anthropic","openai"], visibility="public", github=true` (`openai` because Codex sends repo code to OpenAI; Mel also runs on an OpenAI key, set by Jay 2026-11-14, so no vendor is added). Keenable, Neon, Render, Vercel, Mel, Codex, FAL and Skillry are third parties: ADR-0004 lists what each receives, and ADR-0005 records hosting. Commit this spec as `docs/superpowers/specs/2026-11-14-receipts-design.md`.

**Gate profile (Jay's decision): hackathon profile recorded in an ADR, written in W0.** Pyright stays strict on every `src/receipts/` path except `ui/`, which runs in basic mode because of Gradio's typing. Any pip-audit advisories in the Gradio/LangChain tree are triaged in that ADR, each by advisory id with an expiry no later than 2026-11-30, instead of blocking merges. These are exceptions to AGENTS.md §1 and §6, allowed only as ADR-0006 records them; AGENTS.md §9 points to that ADR. Tests, lint and format stay fully enforced. W0 locks every dependency and gets all five required checks green with stub Gradio/LangChain code; **lanes may not add dependencies**.

**Start (Jay's answer):** the hackathon has started, so Wave 0 begins as soon as this plan is approved.

## Execution steps after approval

1. Jay, in parallel: get keys (Anthropic, Keenable, Neon with a `dev` branch, Render account), install Mel and add a model key, then put the keys in `~/.zshenv` as `export NAME=...` lines (AGENTS.md §6: secrets live in the environment; config holds `${NAME}` references). On Render they go in the service's environment settings.
2. ✅ Done 2026-11-14: `bin/new-project` created https://github.com/JayR1031/receipts (12 of 13 report rows `done`; `pre-commit` skipped because it is not installed locally — CI still runs every gate on each PR). This spec and the third-party ADRs land through issue #1.
3. `/improve-prompt` with this spec → brief → `/orchestrate <brief>` → plan-graph → Jay approves → W0 on main.
4. W1: the orchestrator dispatches L1–L3 to Claude worktrees and writes the L4/L5 briefs; Jay starts Codex (L4) and Mel (L5).
5. Each lane: `bin/jig` green → `/judge` → merge in the fixed order.
6. W2 integration + Render deploy → W3 ship assets → `/verify-claims` on the submission text before posting.

## Build flow and fan-out (improve-prompt → orchestrate → worktrees → judge; `bin/jig` before done; 3 repairs then escalate)

| Wave | Lane | Built by | Scope (folder) |
|---|---|---|---|
| 0 | Contracts, deps, CI green, fakes | Claude Code (main) | `contracts.py`, settings, pyproject lock, mount stub, fakes |
| 1 | L1 Harness | Claude Code worktree | `harness/` pack loader, SpecialistRunner, Coordinator, RunService |
| 1 | L2 Verifier | Claude Code worktree | `verify/` |
| 1 | L3 Packs + golden set | Claude Code worktree | `packs/`, 3 demo comparisons, golden tests |
| 1 | L4 Persistence + API | **Codex** | `db/`, `api/` (RunRepo on Neon, routes, history) |
| 1 | L5 Gradio UI | **Mel** (Jay drives) | `ui/` input, live agent panel, battlecard with receipts, History |
| 1 | L6 Landing page | Claude Code | own repository outside this one; Next.js 16 on Vercel; license check first |
| 2 | Integration + deploy | Claude Code | real wiring, e2e on 3 comparisons, Render, stored demo runs |
| 3 | Ship | Claude Code + Jay | README + diagram, demo video, OG image (the preview picture social sites show for a link; skillry `bs-duolingo-style-og`), submission text through `/verify-claims` |

- **Merge order** (branches must be up to date with main): L3 → L2 → L1 → L4 → L5. L6 lives in its own repository and merges independently.
- **Lane paths:** AGENTS.md §9 gives each lane's exact source and test globs.
- **Codex/Mel hand-off:** the orchestrator creates the L4/L5 worktrees and briefs (`docs/superpowers/briefs/L4-api.md`, `L5-ui.md`). Jay points Codex at L4 and opens L5 in Mel and pastes the brief. Both read `AGENTS.md`. The judge reviews their branches like any other. README credits each tool's lanes.
- **Fallback:** if L5 isn't judge-green by H20, Claude Code finishes the UI (the UI is on the demo's critical path).
- **Time box:** W0 H0–3 · W1 H3–20 · W2 H20–32 · W3 H32–42 · buffer/sleep H42–48.

## Verification

- Per lane: `bin/jig` green, then a `/judge` verdict before merge.
- Unit (no network): pack schema validation; Verifier exact/fuzzy/miss/markdown/fetch-failed cases; coordinator with fakes; event-union serialization; URL rewrite.
- Integration (marked, needs keys): one live `pricing` run; Neon round-trip on `dev`; each schema constraint rejecting its bad row on `dev`.
- E2E: the 3 demo comparisons via `/ui` and `/api/runs`; record verified/total and wall time per run (target median < 90 s over the 3 runs).
- Manual on the Render URL: run one live comparison with the passcode, open a History run, click 5 receipts and confirm each quote is on its page.

## Prerequisites Jay provides

Anthropic API key · Keenable key (free account) · Neon project + connection string · Render account linked to GitHub · Mel installed with a model key (done 2026-11-14: OpenAI) · Codex in the repo · optional: skillry purchase ($4.99) + FAL key for the OG image · the hackathon's rules/judging criteria and tracks 10–12 if available.
