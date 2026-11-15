# Runbook: Render

The one service (ADR-0005): `srv-dbsf8q0n74is739mv2jg`, https://receipts-h745.onrender.com,
Docker from `./Dockerfile`, autoDeploy from `main`. Do not create a second service or trigger a
manual deploy; a merge to `main` is the deploy.

## Environment variables on the service

`ANTHROPIC_API_KEY`, `KEENABLE_API_KEY`, `DATABASE_URL` (Neon), `DEMO_PASSCODE`,
`MAX_CONCURRENT_SPECIALISTS=2`, `PORT=8000` (Render injects it; the `CMD` binds `${PORT:-8000}`).
`RENDER_GIT_COMMIT` is set by Render and feeds `/healthz`'s `sha`. Nothing reads a key at import
or startup: with none of the four set the app boots and serves the demo fakes.

## Check a deploy

```sh
source ~/.zshenv   # RENDER_API_KEY; never print it
curl -fsS -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/srv-dbsf8q0n74is739mv2jg/deploys?limit=1"
curl -fsS https://receipts-h745.onrender.com/healthz   # sha == git rev-parse --short origin/main
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
