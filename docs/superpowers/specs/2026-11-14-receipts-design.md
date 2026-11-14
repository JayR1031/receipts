# Receipts — verified competitive-intel crew (Miami AI Hackathon, 48 h, solo)

> "Receipts" (every claim shows its receipt) is Claude's working name; rename freely.

## Context

Jay is entering the Miami AI Hackathon solo with ~48 hours to submit. Tracks: **02 Agentic Marketing** (competitive intelligence, SEO/AEO/GEO) and **08 Research, Productivity & Developer Agents** (research bots, result verification). Jay's stack decisions: Gradio UI, LangChain, Keenable web search, FastAPI/Starlette, Neon Postgres, and an **agent harness that makes each agent domain-specific**. The build fans out across three builders: **Claude Code** worktree agents, **Codex** (Jay's other terminal), and **Mel** (the hackathon-promoted agentic terminal; Jay chose to split work between Claude Code and Mel).

The product: a founder/marketer/sales rep types "Us vs. Rival" and gets a one-page battlecard where **every line carries a receipt** — a source URL plus a verbatim quote re-checked against the fetched page, or a logged search result. Claims without a receipt are dropped and counted ("23 of 27 verified"). That answers the judges' first question about any research agent: "how do you know it didn't make that up?"

## Goals / non-goals / anti-goals

- **Must ship:** 4 specialists + Verifier on one harness; live agent progress in Gradio; battlecard with receipts and a verified/total score; runs in Neon with a History tab; public URL; 2-min demo video; README with architecture diagram.
- **Stretch (only if ahead at H30):** "what changed since last run" diff; adding a 5th pack live during the demo; a one-page landing site built from the Aceternity "cryptgen" template kept outside the repo (Next.js 16), using only its hero and features sections, deployed on Vercel. Before it goes into the public repo, confirm the Aceternity license allows that. Its fake testimonials, pricing and logo cloud are cut, because invented social proof contradicts a product about receipts.
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

**Keenable:** refuse to start a run without `KEENABLE_API_KEY` (the keyless tier silently caps at 1,000 req/h/IP).

**Neon (Claude's call):** `dev` branch for building, `main` for the demo. Settings rewrite `postgresql://` → `postgresql+psycopg://`; `pool_pre_ping=True` (Neon suspends idle compute). Portable SQLAlchemy 2 types so unit tests run on SQLite. Tables: `runs, sources, search_results, claims, events`.

**Public URL safety (Claude's call):** anyone can open History and the 3 stored demo runs; starting a live run needs `DEMO_PASSCODE`. Nothing reads secrets at import/startup (the kit's CI image check runs with no secrets).

**Deploy (Claude's call, changed after review):** **Render free web service** from the kit's Dockerfile. Hugging Face Spaces is out: HF docs say Docker Spaces need a paid plan and outbound traffic is limited to ports 80/443/8080, so Neon's 5432 is blocked. Render's free tier blocks only ports 25/465/587; it sleeps after 15 min idle (~1 min wake), so hit the URL before judging. Uvicorn binds `${PORT:-8000}`.

## Repo bootstrap (Jay's agentic-standard kit)

`bin/new-project --answers receipts.toml` (agentic-standard kit) with
`name="Receipts", slug="receipts", stack="python", presets=["api-fastapi"], cloud="none", tracker="github", vendors=["anthropic","openai"], visibility="public", github=true` (`openai` because Codex sends repo code to OpenAI; add `google` if Mel runs on a Gemini key). Keenable, Neon, Render, Mel, FAL are third parties → ADR-0003/0004 by hand. Commit this spec as `docs/superpowers/specs/2026-11-14-receipts-design.md`.

**Gate profile (Jay's decision): hackathon profile recorded in an ADR, written in W0.** Pyright stays strict on `contracts`, `harness/`, `verify/` and `db/`; `ui/` runs in basic mode because of Gradio's typing. Any pip-audit advisories in the Gradio/LangChain tree are triaged in that ADR, each with an expiry date, instead of blocking merges. Tests, lint and format stay fully enforced. W0 locks every dependency and gets all five required checks green with stub Gradio/LangChain code; **lanes may not add dependencies**.

**Start (Jay's answer):** the hackathon has started, so Wave 0 begins as soon as this plan is approved.

## Execution steps after approval

1. Jay, in parallel: get keys (Anthropic, Keenable, Neon with a `dev` branch, Render account), install Mel and add a model key, then put the keys in the repo's untracked `.env` once the repo exists.
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
| 2 | Integration + deploy | Claude Code | real wiring, e2e on 3 comparisons, Render, stored demo runs |
| 3 | Ship | Claude Code + Jay | README + diagram, demo video, OG image (skillry `bs-duolingo-style-og`), submission text through `/verify-claims` |

- **Merge order** (branches must be up to date with main): L3 → L2 → L1 → L4 → L5.
- **Codex/Mel hand-off:** the orchestrator creates the L4/L5 worktrees and briefs (`docs/superpowers/briefs/L4-api.md`, `L5-ui.md`). Jay points Codex at L4 and opens L5 in Mel and pastes the brief. Both read `AGENTS.md`. The judge reviews their branches like any other. README credits each tool's lanes.
- **Fallback:** if L5 isn't judge-green by H20, Claude Code finishes the UI (the UI is on the demo's critical path).
- **Time box:** W0 H0–3 · W1 H3–20 · W2 H20–32 · W3 H32–42 · buffer/sleep H42–48.

## Verification

- Per lane: `bin/jig` green, then a `/judge` verdict before merge.
- Unit (no network): pack schema validation; Verifier exact/fuzzy/miss/markdown/fetch-failed cases; coordinator with fakes; event-union serialization; URL rewrite.
- Integration (marked, needs keys): one live `pricing` run; Neon round-trip on `dev`.
- E2E: the 3 demo comparisons via `/ui` and `/api/runs`; record verified/total and wall time per run (target median < 90 s over the 3 runs).
- Manual on the Render URL: run one live comparison with the passcode, open a History run, click 5 receipts and confirm each quote is on its page.

## Prerequisites Jay provides

Anthropic API key · Keenable key (free account) · Neon project + connection string · Render account linked to GitHub · Mel installed with a model key · Codex in the repo · optional: skillry purchase ($4.99) + FAL key for the OG image · the hackathon's rules/judging criteria and tracks 10–12 if available.
