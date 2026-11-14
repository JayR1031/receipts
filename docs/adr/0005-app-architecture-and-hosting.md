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
- The landing page is published only after the Aceternity template's license is confirmed to allow a public deployment. Status: **pending**, owned by L6, which records the license name, source URL, date read and verdict here.
- Nothing reads secrets at import or startup, so the `api-image` CI check can boot the container with no secrets.

## Alternatives considered

- **Hugging Face Spaces (Docker).** Rejected. HF's Spaces overview (https://huggingface.co/docs/hub/spaces-overview, read 2026-11-14) says Gradio and Docker Spaces need a paid plan to create, and that Spaces may connect out only on ports 80, 443 and 8080, so Neon's Postgres port 5432 is unreachable.
- **A separate Next.js front end for the app.** Rejected for the core build: a second toolchain and deploy in a 48-hour solo build. Next.js is used only for the static landing page (Decision), which shares no code with the app.
