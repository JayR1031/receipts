# API

- Run locally: `uv run uvicorn receipts.api.app:app --reload` → http://127.0.0.1:8000/healthz
- `/healthz` reports the git sha the image was built from (`GIT_SHA` build arg); `unknown` locally.
- `api-fastapi` only: `uv run python scripts/export_openapi.py` writes `docs/api/openapi.json`;
  commit it with any change to the API shape so the diff shows in review.
- Image: `docker build --build-arg GIT_SHA="$(git rev-parse HEAD)" -t receipts-api .`
  The `api-image` workflow builds and runs it on every pull request and push to `main`, and
  passes only when `/healthz` reports that commit.
- Deploy: Render (ADR-0005) builds `./Dockerfile` from `main` on every merge (autoDeploy) and
  runs it at https://receipts-h745.onrender.com; nothing is pushed to a registry. The `CMD` binds
  `${PORT:-8000}`, so Render's injected `PORT` wins and the local default stays 8000. `/healthz`
  reports a baked `GIT_SHA`, except that the image's default `unknown` (or a blank value) counts
  as unset; then the first seven characters of `RENDER_GIT_COMMIT`, else `unknown`. Its
  `X-Receipts-Mode` header says `live` or `demo`. See `docs/runbooks/render.md`.
