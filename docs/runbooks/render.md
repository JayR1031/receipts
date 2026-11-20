# Runbook: Render

The one service (ADR-0005): `srv-dbsf8q0n74is739mv2jg`, https://receipts-h745.onrender.com,
Docker from `./Dockerfile`, autoDeploy from `main`. Do not create a second service or trigger a
manual deploy; a merge to `main` is the deploy.

## Environment variables on the service

`ANTHROPIC_API_KEY`, `KEENABLE_API_KEY`, `DATABASE_URL` (Neon), `DEMO_PASSCODE`,
`MAX_CONCURRENT_SPECIALISTS=2`, `PORT=8000` (Render injects it; the `CMD` binds `${PORT:-8000}`).
`RENDER_GIT_COMMIT` is set by Render and feeds `/healthz`'s `sha` (the image bakes
`GIT_SHA=unknown`, which counts as unset). Nothing reads a key at import or startup.

Sign-in (issue #41, ADR-0008) needs `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` and
`SESSION_SECRET`, plus `DATABASE_URL`. Two more are optional, with defaults that need no entry:
`RUNS_PER_USER_PER_DAY` (5) and `SIGNED_OUT_RUNS_PER_DAY` (20). The deployed service sets
`SIGNED_OUT_RUNS_PER_DAY=10` and `DEMO_PASSCODE=receipts-demo`, a passcode published on purpose so
anyone can try the app; the shared daily cap is what limits spend. The main session set both
through Render's API at the owner's request on 2026-11-20, read them back, and redeployed
(`dep-dbvs51qjnfac73894bdg`, live at 03:47 UTC), because settings are read once per process. (It
was 5 with a private passcode from 2026-11-18, `dep-dbujqss9v7es738psfqg`.) The issue #41 brief records that
the main session set the first three through Render's API on 2026-11-15; this runbook has not
re-checked them, so check their names (never their values) in the Render dashboard before relying
on sign-in. With any of the four missing, `/auth/login` answers 503 naming it and the UI shows no
sign-in link. Changing `SESSION_SECRET` signs everyone out.

## Live or demo

`/healthz` names the mode in its `X-Receipts-Mode` header: `live` when `ANTHROPIC_API_KEY`,
`KEENABLE_API_KEY` and `DATABASE_URL` are all set (a blank value counts as unset), else `demo`.
In demo mode a run replays the invented demo script (Acme Widgets vs Zeta Gadgets) under those
invented names, never the names typed in, and nothing is written to Neon.

- `DEMO_PASSCODE` unset (local dev): the `/ui` Run panel replays the demo with no passcode and
  History lists it. `POST /api/runs` still answers 401: the API never starts a run without a
  configured passcode. If the three live settings are present, the UI refuses signed-out
  visitors too; a signed-in visitor can start runs.
- `DEMO_PASSCODE` set (Render): a signed-out visitor in the UI, and every `POST /api/runs`, needs
  the passcode, then room under `SIGNED_OUT_RUNS_PER_DAY` (all runs with no user today, UTC; the
  API answers 429 at the cap), then `KEENABLE_API_KEY`. A visitor signed in with Google needs no
  passcode and may start `RUNS_PER_USER_PER_DAY` runs per UTC day. If a live setting is missing,
  the first run logs
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

Each seeded run is a signed-out run: it counts against `SIGNED_OUT_RUNS_PER_DAY` for that UTC day
and appears in signed-out History, and in signed-in History alongside that person's own runs.

## Sign-in (issue #41, ADR-0008)

**Who can sign in.** While the Google OAuth app's consent screen is in Testing mode, only the
repository owner can sign in (the owner is its only test user); everyone else uses the passcode.
Publishing the consent screen (an owner action in the Google Cloud console) opens sign-in to any
Google account. Whether Google reviews an app that asks only for `openid email` before it is
published is unconfirmed (an open question in the issue #41 brief).

**Registered callbacks.** `http://localhost:8000/auth/callback` and
`https://receipts-h745.onrender.com/auth/callback`. The app builds `https://<host>/auth/callback`
for any other host, and Google refuses a callback it does not have registered, so a new domain
needs its callback registered first.

**When the UI offers it.** The "Sign in with Google" link shows only when the four sign-in
settings and the three live settings are all set. With the four sign-in settings set but
`ANTHROPIC_API_KEY` or `KEENABLE_API_KEY` missing, `/auth/login` and `/auth/me` still work while
the UI hides the link and treats every visitor as signed out (ADR-0008, "Half-configured
deploys").

### Sign in locally

```sh
source ~/.zshenv                                  # GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET; never print them
export SESSION_SECRET="$(openssl rand -hex 32)"   # throwaway, local only
uv run uvicorn receipts.api.app:app --reload
```

Open `http://localhost:8000/ui`, not `127.0.0.1`: the registered local callback is on `localhost`
and the cookies are host-only, so `/auth/login` on `127.0.0.1` sends the browser to
`http://localhost:8000/auth/login` first. `DATABASE_URL` in `~/.zshenv` is the deployed Neon
database, so a local sign-in writes your `users` row there.

### The `runs.user_id` column on Neon

Nothing to run by hand. `create_schema` (`src/receipts/db/repo.py`) adds the column on the first
live request after a deploy, on Postgres only, after `create_all` has created `users`:

```sql
ALTER TABLE runs ADD COLUMN IF NOT EXISTS user_id VARCHAR(64) REFERENCES users(id);
CREATE INDEX IF NOT EXISTS ix_runs_user_id ON runs (user_id);
```

Both are additive and idempotent. The `db` task's Neon integration run already applied them on
2026-11-16 (the owner's answer (a) in the issue #41 plan). To check, in the Neon SQL editor:

```sql
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_name = 'runs' AND column_name = 'user_id';
-- expected: 1 row: user_id | character varying | 64 | YES

SELECT pg_get_constraintdef(oid) FROM pg_constraint
WHERE conrelid = 'runs'::regclass AND contype = 'f';
-- expected: 1 row: FOREIGN KEY (user_id) REFERENCES users(id)

SELECT indexname FROM pg_indexes WHERE tablename = 'runs' AND indexname = 'ix_runs_user_id';
-- expected: 1 row
```

The same facts are tested by `tests/test_db_constraints.py::test_create_schema_twice_is_idempotent_on_neon`:

```sh
source ~/.zshenv   # DATABASE_URL; never print it
uv run pytest tests/test_db_constraints.py -q -m integration -rs --tb=short
```

The file runs `create_schema` itself, adds nothing else, and deletes every row it writes. Keep
`--tb=short`: when a test in it fails, pytest's long traceback prints the `engine` fixture's repr,
which shows the database user and host (the password is masked as `***`), and the leak gate
fails on the host suffix if that output is pasted into the repository.

### Delete a person's data

A person asks the repository owner (AGENTS.md section 9). In the Neon SQL editor, find their id,
then delete their runs before the row: the foreign key has no `ON DELETE`, so Postgres refuses to
delete a `users` row that runs still cite.

```sql
SELECT id FROM users WHERE email = '<their address>';
DELETE FROM runs WHERE user_id = '<id>';
DELETE FROM users WHERE id = '<id>';
```

Do not set `runs.user_id` to NULL instead: that would move the person's runs into the signed-out
History everyone sees. A session cookie the person still holds then reads as signed out when they
start a run (ADR-0008, "A deleted user's cookie").

### After the deploy: the owner's acceptance steps

From the issue #41 brief; the owner records the results in the PR or the issue. Steps 3 and 4 are
live runs, which spend Anthropic and Keenable credits.

1. `curl -sS -o /dev/null -w '%{http_code}\n' https://receipts-h745.onrender.com/auth/me` prints
   `401` (no cookie).
2. Sign in with Google at https://receipts-h745.onrender.com/ui. The account line reads
   `<your address> · 0 of 5 runs used today (UTC)` and the passcode field is hidden.
3. Start one run signed in. It appears in History while signed in, and not after signing out
   (claimed runs stay private).
4. Signed out, start one run with the passcode (or Ask Receipts). It appears in History signed
   out, and still appears while signed in, in the same list as your own runs.
5. The `runs.user_id` check above.
