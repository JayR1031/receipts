Brief: Wave 3 — ship (lean, scope cut 2026-11-14).

Source: plan `docs/superpowers/plans/2026-11-14-w0-foundations-and-w1-lanes.md` ("Scope cut 2026-11-14" rows 8–9, "W2 facts", "Escalations", lane verdict tables); spec `docs/superpowers/specs/2026-11-14-receipts-design.md` (Build flow row W3, Verification); ADR-0004 (what each third party receives; README credits each tool's lanes), ADR-0005 (landing page). Standard: `AGENTS.md`; `/verify-claims` before any text leaves the repo. Written by the orchestrator 2026-11-15 ~01:35 UTC, to be dispatched after W2 is merged and live. Clock: submission ~05:30 UTC; **W3 by ~05:00 UTC.** Demo video is the user's; OG image is dropped.

## Goal

A stranger landing on the repository or the landing page understands "every claim carries a receipt" in one minute, can open the live app, and nothing they read is a claim the repo cannot back: README with an architecture diagram and honest numbers from the recorded live run; the landing page's app link points at the Render URL on a free production alias that is not `receipts-landing.vercel.app`; the submission text has passed `/verify-claims`.

## Why it matters

The judges read the README and the submission text before they click anything; one unverifiable number or a dead link costs more than a missing feature. ADR-0004 commits the README to crediting which tool built which lane, and the landing page is public already (production alias `receipts-landing-nine.vercel.app`), so its copy must match what shipped.

## Constraints

- **Every number carries its set and denominator** (AGENTS.md): "N of M verified" quotes the run id and UTC time from the W2 PR body or `scripts/seed_demo_runs.py` output; no averages over runs that were not recorded.
- **Nothing promised that was cut:** two packs (`pricing`, `positioning_seo`), one `runs` table, no Haiku notes, plain History list. Say "two domain specialists today; packs are YAML so more can be added".
- **Credits per ADR-0004:** Claude Code built W0, L1–L5, W2, W3 and the landing page; Codex and Mel are named only for what they actually did (Codex: nothing in the final build; Mel: QA/docs if the user confirms — ask, do not assume). Anthropic (specialists), Keenable (search/fetch), Neon (Postgres), Render (app), Vercel (landing) named with what each receives (copy ADR-0004's table rows, do not rewrite them).
- **Licence (ADR-0005):** the landing-page repository stays private; the README may link the live page, not its source.
- **Verifier honesty:** the README states the verifier rules exactly as merged — exact substring; fuzzy ≥ 90 only when the match covers the whole quote and every number token appears on the page; search receipts match a logged row; fetch failure is "fetch failed", not "false"; unverified claims are shown, marked unverified. Mention the known gap the judge recorded (an exact match of `$19` inside `$199` verifies) under "Known limitations", unless W2/W3 fixed it.
- **No secrets, no run output committed**; leak gate and gitleaks stay green.
- **Vercel:** `VERCEL_TOKEN` in `~/.zshenv`; non-interactive `CI=1 npx -y vercel@65.16.0 <cmd> --token "$VERCEL_TOKEN" --yes </dev/null`; project `receipts-landing` exists; production deploys are allowed (user, 23:42 UTC). The alias must not be `receipts-landing.vercel.app` (owned by another account). Set `NEXT_PUBLIC_APP_URL=https://receipts-h745.onrender.com` on the project (production env), redeploy `--prod`, and add a free alias (e.g. `receipts-receipts.vercel.app` or the user's pick — ask once if unsure).

## File scope

`Allowed:` `README.md`; `docs/assets/architecture.md` or `docs/assets/architecture.mmd` (Mermaid source; render to `docs/assets/architecture.svg` only if a renderer is available offline, else keep Mermaid in the README); `docs/submission/submission.md` (new; the text to paste into the hackathon form, with a "Claims and evidence" table used by `/verify-claims`); `docs/submission/verify-claims.md` (the `/verify-claims` result); the landing-page repository `/Users/jay/Projects/receipts-landing` (copy fixes from the carried L6 LOWs: live-panel wording, "adding a domain" sentence, "quote is found" → include fuzzy rule, LICENSE-TEMPLATE file list; `lib/site.ts` reads `NEXT_PUBLIC_APP_URL`, `githubUrl` → this repository's URL).
`Forbidden:` everything under `src/`, `tests/`, `scripts/` (except reading), ADRs, the spec, `AGENTS.md`, `.github/**`, `pyproject.toml`, `uv.lock`, `Dockerfile`.

## What W3 ships

1. `README.md`: one-paragraph pitch; "Try it" (Render URL; History is public; a live run needs the demo passcode the user shares with judges separately); architecture diagram (Mermaid: UI/API → InProcessRunService → Coordinator → two SpecialistRunners (Anthropic via LangChain, Keenable tools with budgets) → Verifier → SqlRunRepo (Neon) → History); "How verification works" (rules above); "What shipped / what was cut" (scope cut table, honest); "Built with" credits per ADR-0004; "Run locally" (`uv sync --frozen`, env var names, `uv run uvicorn receipts.api.app:app`); "Evidence" (the live-run line(s) with run id, verified/total, wall time, UTC; link to `docs/superpowers/plans/verdicts/`); "Known limitations".
2. `docs/submission/submission.md`: ≤ 300 words for the form + the claims/evidence table; every sentence with a number or a capability maps to a row with a command, file, URL or run id.
3. `/verify-claims` on `submission.md` and the README's Evidence section; result saved to `docs/submission/verify-claims.md`; FAIL rows fixed before the PR.
4. Landing page: env var + production redeploy + free alias; copy fixes; confirm with `curl` that the alias serves the new copy and the "Open the app" link is the Render URL.

## Acceptance tests

- `bin/jig` exit 0 (docs-only; still run). `python3 scripts/leak_gate/check_tracked.py` exit 0; gitleaks exit 0.
- `grep -n 'of [0-9]* verified\|[0-9]* s\b' README.md docs/submission/submission.md` — every match has a run id and UTC time within two lines.
- `grep -c -i 'four domain\|news_social\|product pack' README.md docs/submission/submission.md` → 0 (unless under "cut").
- Every URL in README/submission returns 200 (`curl -fsS -o /dev/null`), the Render `/healthz` sha equals `git rev-parse --short origin/main`.
- `CI=1 npx -y vercel@65.16.0 ls receipts-landing --token "$VERCEL_TOKEN" </dev/null` shows the new production deployment Ready; `curl -sS <alias> | grep -c 'receipts-h745.onrender.com'` ≥ 1; the alias is not `receipts-landing.vercel.app`.
- `docs/submission/verify-claims.md` ends with PASS and lists the claims checked with their evidence (denominators included).

## Verification (reviewer)

1. Diff touches only Allowed paths. 2. Each README number traces to a cited run/verdict file; spot-check two by opening the cited source. 3. Credits match ADR-0004 rows verbatim. 4. The verifier description matches `src/receipts/verify/rules.py` at `main` (read the code, not the README). 5. Landing alias and link verified by `curl`, and the Vercel project has no Git link and no public repo (`vercel project ls`, `git -C /Users/jay/Projects/receipts-landing remote -v` empty). 6. `/verify-claims` was run by a fresh context (the `claims-judge` agent), not the writer.

## Do not

- Do not invent metrics, testimonials, or users; do not average unrecorded runs; do not say "verified" for anything the Verifier marked unverified.
- Do not publish the landing-page source or create a GitHub repository for it (licence condition).
- Do not touch product code; a README claim that the code cannot back is changed in the README, not by a last-minute code edit.
- Do not skip `/verify-claims`; do not count a "could not check" row as a pass.

## Assumptions

- W2 is merged and the Render deploy of `main` is healthy before W3 starts; the live-run line exists in the W2 PR body.
- The user records the demo video and provides the hackathon form fields; W3 supplies text, links and the diagram.
- The demo passcode is shared with judges out of band; the README says a passcode is required and where History is public.
