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

## Routes

The same routes as `docs/api/openapi.json`. Sign-in is optional (issue #41, ADR-0008).

| Route | Answers |
|---|---|
| `GET /healthz` | 200 `{"status", "sha", "version"}`; header `X-Receipts-Mode: live` or `demo`. |
| `POST /api/runs` | 202 `{"run_id"}`. Checked in this order: 401 `a valid X-Demo-Passcode is required`; 429 once today's (UTC) runs with no user have reached `SIGNED_OUT_RUNS_PER_DAY` (default 20), detail `20 of 20 signed-out runs used today (UTC); the limit resets at 00:00 UTC`; 503 `KEENABLE_API_KEY is not set`. 422 for a bad body. Every API run is a signed-out run: it is never linked to a user, even when the request carries a session cookie. |
| `GET /api/runs` | 200, a list of `RunSummary`, newest first. With a valid session cookie, that user's runs; without one, the runs that belong to no user. On the demo, the demo's list. |
| `GET /api/runs/{run_id}` | 200 `Battlecard`, or 404. Anyone with the id can read it, signed in or not. |
| `GET /auth/login` | 302 to Google's authorization endpoint (scopes `openid email`, with `state`, `nonce` and a PKCE S256 `code_challenge`), setting the 10-minute round-trip cookie `receipts_oauth`. On `127.0.0.1`, a 302 to `http://localhost:8000/auth/login` first. 503 naming the first missing of `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SESSION_SECRET`, `DATABASE_URL`, never a value. |
| `GET /auth/callback` | Google sends the browser here with `code` and `state`. 302 to `/ui` with the session cookie `receipts_session` (7 days). 400 `sign-in check failed: <check>` naming the failed check only (`round_trip`, `state`, `code`, `token_exchange`, `jwks`, `id_token`, `iss`, `aud`, `exp` or `nonce`). 503 when sign-in is not configured, or `sign-in check failed: user_store` when the users store fails. |
| `POST /auth/logout` | 303 to `/ui`, clearing the session cookie. |
| `GET /auth/me` | 200 `{"email": ...}` with `Cache-Control: no-store` for a valid session whose user still exists; otherwise 401 `not signed in`. |

Both cookies are signed (HS256 under `SESSION_SECRET`), host-only, `HttpOnly`, `Secure`,
`SameSite=Lax`, `Path=/`. The session cookie carries our user id and its expiry only.

Local sign-in starts at `http://localhost:8000`, not `127.0.0.1`: the registered local callback is
`http://localhost:8000/auth/callback` and the cookies are host-only (`docs/runbooks/render.md`).
