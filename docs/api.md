# API

- Run locally: `uv run uvicorn receipts.api.app:app --reload` → http://127.0.0.1:8000/healthz
- `/healthz` reports the git sha the image was built from (`GIT_SHA` build arg); `unknown` locally.
- `api-fastapi` only: `uv run python scripts/export_openapi.py` writes `docs/api/openapi.json`;
  commit it with any change to the API shape so the diff shows in review.
- Image: `docker build --build-arg GIT_SHA="$(git rev-parse HEAD)" -t receipts-api .`
  The `api-image` workflow builds and runs it on every pull request and push to `main`, and
  passes only when `/healthz` reports that commit.
- Deploy: no cloud was chosen (ADR-0001, cloud `none`), so nothing in this repository deploys the
  image. Push it to the registry of whatever host runs it and publish port 8000. Choosing a cloud
  later is a new ADR that supersedes ADR-0001.
