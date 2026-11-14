# ADR-0005: App architecture and hosting

**Status:** accepted · **Date:** 2026-11-14

## Context

Receipts is a hackathon build (about 48 hours, one person, three coding agents in parallel). The design spec is `docs/superpowers/specs/2026-11-14-receipts-design.md`. It needs a chat-style UI, a JSON API, live web search, a Postgres store and a public URL, and every lane must be buildable against shared contracts without waiting on the others.

## Decision

- **One process.** FastAPI (from the `api-fastapi` preset) serves the JSON API; the Gradio UI is mounted into the same app at `/ui` with `gr.mount_gradio_app`, which works because FastAPI is built on Starlette. `/` redirects to `/ui`.
- **Agents.** LangChain 1.x agents, one generic `SpecialistRunner` configured by YAML "domain packs" in `src/receipts/packs/` (loaded with `importlib.resources` so they ship inside the image). Tool budgets use `ToolCallLimitMiddleware`. Search and fetch use `langchain-keenable`.
- **Database.** Neon Postgres through SQLAlchemy 2 and psycopg 3. Settings rewrite `postgresql://` to `postgresql+psycopg://` and enable `pool_pre_ping` because Neon suspends idle compute.
- **Hosting.** A Render free web service built from the repository's `Dockerfile`; uvicorn must bind `${PORT:-8000}` (the Dockerfile's CMD fixes port 8000 today; W2 changes it). This is the hosting decision ADR-0001 deferred ("Re-run the matrix below when hosting is needed."). ADR-0001's cloud answer stays `none`: Render and Vercel are managed hosts, with no cloud account and no Terraform.
- **Landing page.** A one-page Next.js 16 site from the Aceternity "cryptgen" template, in its own repository, on Vercel; it links to the Render app (lane L6).

## Consequences

- The UI reads the run's event stream in-process; there is no second service to deploy.
- Render's free tier (https://render.com/docs/free, read 2026-11-14) sleeps after 15 minutes without traffic and takes about a minute to wake, so the URL is opened shortly before judging.
- The same page says Render "might restart a Free web service at any time", which kills any run in progress, and "may suspend" one that sends an unusually high volume of outbound traffic, which here means calls to Neon, Anthropic and Keenable. Each event is written to Neon as it happens, so a restart loses only the run in flight, and the 3 stored demo runs are the fallback if a live run dies during judging. A suspended Free service comes back only "by moving it to any paid compute plan" (same page), which also takes History and the stored runs down; the fallback for suspension is upgrading the Render service to a paid plan, and the recorded demo video covers the time that takes.
- The landing page may be published: verdict **permitted** (one condition on the repository, below), under the "Aceternity License" (https://ui.aceternity.com/licence, read 2026-11-14, the page the cryptgen product page https://ui.aceternity.com/templates/cryptgen-marketing-aceternity links to as "Licence"), which grants "an ongoing, non-exclusive, worldwide license" to "create unlimited end products for yourself or your clients", lists "Commercial or personal websites" among end products, says they "may be sold, licensed, sub-licensed, or freely distributed" and has no attribution clause, so the public Vercel deployment is allowed. The template is sold only with All-Access ("All-Access includes all 17 templates, 182 blocks and 5 pages. Pay once.", product page above; the Free plan on https://ui.aceternity.com/pricing, read 2026-11-14, lists only "Access to all 100+ free components"), and the repository owner confirmed on 2026-11-14 that they hold an All-Access licence, so the licence applies. One condition binds the deploy: the landing-page repository stays private (no public GitHub repository), because the same page says "You cannot re-distribute the Item as a stock image or its source files, regardless of modifications" and a public repository of the page would redistribute the template's modified source files. The downloaded zip is a GitHub archive of `manuarora700/cryptgen-template-aceternity` at `0f6acc1` (the GitHub API returned 404 for that repository on 2026-11-14) with no LICENSE file and no `license` field in `package.json`, so the web page is the only licence text.
- Nothing reads secrets at import or startup, so the `api-image` CI check can boot the container with no secrets.

## Alternatives considered

- **Hugging Face Spaces (Docker).** Rejected. HF's Spaces overview (https://huggingface.co/docs/hub/spaces-overview, read 2026-11-14) says Gradio and Docker Spaces need a paid plan to create, and that Spaces may connect out only on ports 80, 443 and 8080, so Neon's Postgres port 5432 is unreachable.
- **A separate Next.js front end for the app.** Rejected for the core build: a second toolchain and deploy in a 48-hour solo build. Next.js is used only for the static landing page (Decision), which shares no code with the app.
