# ADR-0005: App architecture and hosting

**Status:** accepted · **Date:** 2026-11-14

## Context

Receipts is a hackathon build (about 48 hours, one person, three coding agents in parallel). The design spec is `docs/superpowers/specs/2026-11-14-receipts-design.md`. It needs a chat-style UI, a JSON API, live web search, a Postgres store and a public URL, and every lane must be buildable against shared contracts without waiting on the others.

## Decision

- **One process.** FastAPI (from the `api-fastapi` preset) serves the JSON API; the Gradio UI is mounted into the same app at `/ui` with `gr.mount_gradio_app`, which works because FastAPI is built on Starlette. `/` redirects to `/ui`.
- **Agents.** LangChain 1.x agents, one generic `SpecialistRunner` configured by YAML "domain packs" in `src/receipts/packs/` (loaded with `importlib.resources` so they ship inside the image). Tool budgets use `ToolCallLimitMiddleware`. Search and fetch use `langchain-keenable`.
- **Database.** Neon Postgres through SQLAlchemy 2 and psycopg 3. Settings rewrite `postgresql://` to `postgresql+psycopg://` and enable `pool_pre_ping` because Neon suspends idle compute.
- **Hosting.** A Render free web service built from the repository's `Dockerfile`; uvicorn binds `${PORT:-8000}`.

## Consequences

- The UI reads the run's event stream in-process; there is no second service to deploy.
- Render's free tier sleeps after 15 minutes without traffic and takes about a minute to wake, so the URL is opened shortly before judging.
- Nothing reads secrets at import or startup, so the `api-image` CI check can boot the container with no secrets.

## Alternatives considered

- **Hugging Face Spaces (Docker).** Rejected. HF's Spaces overview (read 2026-11-14) says Gradio and Docker Spaces need a paid plan to create, and that Spaces may connect out only on ports 80, 443 and 8080, so Neon's Postgres port 5432 is unreachable.
- **A separate Next.js front end.** Rejected for the core build: a second toolchain and deploy in a 48-hour solo build. Kept as a stretch landing page only (spec, Goals).
