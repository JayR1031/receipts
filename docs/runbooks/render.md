# Runbook: Render

The one service (ADR-0005): `srv-dbsf8q0n74is739mv2jg`, https://receipts-h745.onrender.com,
Docker from `./Dockerfile`, autoDeploy from `main`. Do not create a second service or trigger a
manual deploy; a merge to `main` is the deploy.

## Environment variables on the service

`ANTHROPIC_API_KEY`, `KEENABLE_API_KEY`, `DATABASE_URL` (Neon), `DEMO_PASSCODE`,
`MAX_CONCURRENT_SPECIALISTS=2`, `PORT=8000` (Render injects it; the `CMD` binds `${PORT:-8000}`).
`RENDER_GIT_COMMIT` is set by Render and feeds `/healthz`'s `sha` (the image bakes
`GIT_SHA=unknown`, which counts as unset). Nothing reads a key at import or startup.

## Live or demo

`/healthz` names the mode in its `X-Receipts-Mode` header: `live` when `ANTHROPIC_API_KEY`,
`KEENABLE_API_KEY` and `DATABASE_URL` are all set (a blank value counts as unset), else `demo`.
In demo mode a run replays the invented demo script (Acme Widgets vs Zeta Gadgets) under those
invented names, never the names typed in, and nothing is written to Neon.

- `DEMO_PASSCODE` unset (local dev): the `/ui` Run panel replays the demo with no passcode and
  History lists it. `POST /api/runs` still answers 401: the API never starts a run without a
  configured passcode. If the three live settings are present, the UI refuses too.
- `DEMO_PASSCODE` set (Render): the UI and the API both need the passcode, then
  `KEENABLE_API_KEY`. If a live setting is missing, the first run logs
  `WARNING ... demo mode: DEMO_PASSCODE is set but <names> is missing ...`. On Render that means
  the service's variables drifted; the repository owner fixes them in the Render dashboard
  (agents never change them). The warning names variables, never their values.

## Check a deploy

```sh
source ~/.zshenv   # RENDER_API_KEY; never print it
curl -fsS -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/srv-dbsf8q0n74is739mv2jg/deploys?limit=1"
curl -fsS -D - https://receipts-h745.onrender.com/healthz
# body sha == git rev-parse --short origin/main; header x-receipts-mode: live
```

## Logs

```sh
curl -fsS -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/logs?ownerId=<owner>&resource=srv-dbsf8q0n74is739mv2jg&limit=100"
```

(The owner id comes from `GET /v1/services/srv-dbsf8q0n74is739mv2jg` → `ownerId`.)

## Before judging: wake the service

The free tier sleeps after 15 minutes idle. Hit `/healthz` and wait for a 200 (first response can
take ~30 s), then open `/ui`. To leave fresh runs in History:

```sh
source ~/.zshenv
uv run python scripts/seed_demo_runs.py --n 1 --base-url https://receipts-h745.onrender.com
```
