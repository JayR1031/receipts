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
- **Sign-in (added 2026-11-15, the owner's decision, issue #41, ADR-0008):** optional "Sign in with Google". A signed-in visitor starts runs without the passcode, under a daily limit of their own. History lists their runs plus the same shared unsigned runs a signed-out visitor sees (passcode, Ask Receipts, seed); another signed-in person's runs stay private. Signed-out visitors keep the passcode path. The app stores only the Google subject id and email of people who sign in (AGENTS.md section 9). Google, the sign-in provider, is a third party; ADR-0004 lists what it receives.
- **Non-goals:** scheduling, scraping behind logins, PDF export.
- **Voice (added 2026-11-15, Jay's decision, issue #37; ElevenLabs was a hackathon sponsor):** an ElevenLabs-narrated demo video, and "Ask Receipts", an ElevenLabs Conversational AI agent that loads on the landing page only when a visitor clicks "Talk to Receipts". It reads stored battlecards through the app's read-only API (`GET /api/runs`, `GET /api/runs/{id}`). Since 2026-11-20 (the owner's request) it can also start a run with a third tool, `start_comparison` (`POST /api/runs` with the public passcode in `X-Demo-Passcode`), only after the visitor says yes; such runs are signed-out runs and count against `SIGNED_OUT_RUNS_PER_DAY`. Tests on ElevenLabs suites `suite_4001m7vp0y0we69r2abtmfyq8d1w` and `suite_9901m7vp3yydethb30cr1n9hwpf6`, 4 of 4 passed: no run starts before a yes, a yes starts the named pair, no facts from memory while a run is in progress, and a 429 is explained as the daily limit. On ElevenLabs branch `voice-announce` (`agtbrch_8301m7vsd3d1fks851x301zry3qa`, 0% live traffic, not merged) a fourth tool, `check_run_status` (another `GET /api/runs`), is called at the start of every turn after a start, including silent `skip_turn` wake-ups; as soon as the run is done the agent announces the score and top verified findings without being asked. Failed, slow, or unreachable runs are reported honestly; results are never invented. Tests on suite `suite_3101m7vvg8dbfqb9c7qwy14svwmb`, 13 of 13 passed on 2026-11-20 (mocked tools; the tests did not start live runs). Those battlecards also contain unverified claims (`verified: false`), so stating only verified claims rests on the agent's instructions and its tests: ElevenLabs suite `suite_1801m7egf059fsbbp2rpbpd856aa`, test runs `trun_5001m7egf05he3bbr1md1w0qm8rk` and `trun_2301m7egf05jfgvt69d4fty3qfs3`, 2 of 2 passed on 2026-11-15 (a tool-use test, and a simulated call with mocked tool responses in which it stated the verified price with its source and refused the unverified one). Budget guard (the anti-goal below), set through the ElevenLabs API (ADR-0004): an origin allowlist that refuses browsers on other sites, and a cap of 3 at once, 50 per day and 300 s per call, which bounds the cost even if the origin header is forged. ADR-0004 lists what ElevenLabs and the widget's hosts receive.
- **Anti-goals:** any claim shown without a receipt; a demo that hangs >2 min or dies on a rate limit; specialists written as copy-pasted code instead of config; secrets in git; strangers burning Jay's API budget on the public URL.

## Architecture

```
Gradio Blocks at /ui ─┐   FastAPI: POST /api/runs → run_id (202), GET /api/runs/{id}, GET /api/runs, /healthz, / → 302 /ui, /auth/* (optional Google sign-in)
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

**Neon (Claude's call):** The integration tests and the deployed app use the same Neon database, the one `DATABASE_URL` names; no `dev` branch is in use (W1 plan, coordinator ruling 2026-11-15; owner's answer 2, 2026-11-16). Settings rewrite `postgresql://` → `postgresql+psycopg://`; `pool_pre_ping=True` (Neon suspends idle compute). Portable SQLAlchemy 2 types so unit tests run on SQLite. Tables that exist today: `runs` and `users`. SQLite is for fast unit tests only. The Neon tests run against the live Neon database under the owner's 2026-11-16 ruling (additive changes only, test rows deleted), not a `dev` branch, and prove a constraint by inserting the row it exists to stop (AGENTS.md §4) for the `runs` NOT NULLs and primary key, `users.sub` UNIQUE and the `runs.user_id` foreign key (9 of the 12 Neon tests); a tenth test writes one valid row through `claim_run` and reads `user_id` back, which shows the column exists but rejects nothing. Not yet proven by a rejected insert: the `users.id` primary key and the three `users` NOT NULLs (`sub`, `email`, `created_at`), 4 of the 5 `users` constraints.

**Public URL safety (Claude's call; sign-in added by issue #41, ADR-0008):** anyone can open a battlecard by its id, and signed-out History lists the runs that belong to no one, the 3 stored demo runs among them. Starting a live run takes one of two paths (option b, the owner's decision, 2026-11-15). Signed out: `DEMO_PASSCODE` is required, and all signed-out runs together, in the UI and through `POST /api/runs`, are capped at `SIGNED_OUT_RUNS_PER_DAY` (default 20) per UTC day, so a leaked passcode costs at most that many runs a day. Signed in with Google: no passcode, `RUNS_PER_USER_PER_DAY` (default 5) runs per person per UTC day. History is scoped: signed out, the runs that belong to no one; signed in, your own runs plus those same shared runs. Another signed-in person's runs stay private. A refusal at a limit names its count and the limit ("5 of 5 runs used today (UTC)"). Nothing reads secrets at import/startup (the kit's CI image check runs with no secrets).

**Deploy (Claude's call, changed after review):** **Render free web service** from the kit's Dockerfile. Hugging Face Spaces is out: HF's Spaces overview (https://huggingface.co/docs/hub/spaces-overview, read 2026-11-14) says Docker Spaces need a paid plan and outbound traffic is limited to ports 80/443/8080, so Neon's 5432 is blocked. Render's free-tier page (https://render.com/docs/free, read 2026-11-14) says the free tier blocks only ports 25/465/587, and that a service sleeps after 15 min idle and takes about a minute to wake, so hit the URL before judging. Uvicorn must bind `${PORT:-8000}`; today's Dockerfile CMD fixes port 8000 in exec form, so W2 changes it (and drops its stale `infra/terraform` comment).

## Repo bootstrap (Jay's agentic-standard kit)

`bin/new-project --answers receipts.toml` (agentic-standard kit) with
`name="Receipts", slug="receipts", stack="python", presets=["api-fastapi"], cloud="none", tracker="github", vendors=["anthropic","openai"], visibility="public", github=true` (`openai` because Codex sends repo code to OpenAI; Mel also runs on an OpenAI key, set by Jay 2026-11-14, so no vendor is added). Keenable, Neon, Render, Vercel, Mel, Codex, FAL, Skillry, ElevenLabs and the voice widget's hosts (unpkg.com, Google Cloud Storage, jsDelivr, FingerprintJS) are third parties: ADR-0004 lists what each receives, and ADR-0005 records hosting. Commit this spec as `docs/superpowers/specs/2026-11-14-receipts-design.md`.

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
