"""Seed 1..3 live demo runs and wait for each to finish.

Two modes:
- API (default): POST `/api/runs` with `X-Demo-Passcode` from the env var named by
  `--passcode-env`, then poll `GET /api/runs/{id}` until the run's status is `done` or `error`.
- `--in-process`: build the live service from the environment (`DATABASE_URL`, `KEENABLE_API_KEY`,
  `ANTHROPIC_API_KEY`) and run in this process; the runs land in that database.

Prints one line per run: `run_id verified/total wall_s status`. Reads keys from the environment
only; writes nothing but stdout.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request

from pydantic import TypeAdapter

from receipts.api.models import RunAccepted
from receipts.contracts import RunSummary

PAIRS: tuple[tuple[str, str, str], ...] = (
    ("Mel", "Warp", "agentic terminal"),
    ("Cursor", "Windsurf", "AI code editor"),
    ("Linear", "Jira", "issue tracker"),
)

_SUMMARIES: TypeAdapter[list[RunSummary]] = TypeAdapter(list[RunSummary])


def _request(
    url: str, *, method: str, body: dict[str, str] | None, headers: dict[str, str]
) -> object:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 (https URL from the CLI)
        loaded: object = json.loads(resp.read().decode())
        return loaded


def _start(base: str, body: dict[str, str], headers: dict[str, str]) -> str:
    raw = _request(f"{base}/api/runs", method="POST", body=body, headers=headers)
    return RunAccepted.model_validate(raw).run_id


def _poll_status(base: str, run_id: str) -> RunSummary | None:
    """`GET /api/runs` carries the status; `GET /api/runs/{id}` the card once stored."""
    raw = _request(f"{base}/api/runs", method="GET", body=None, headers={})
    return next((row for row in _SUMMARIES.validate_python(raw) if row.run_id == run_id), None)


def _wait(base: str, run_id: str, started: float, timeout_s: float) -> RunSummary | None:
    row = _poll_status(base, run_id)
    while (row is None or row.status not in ("done", "error")) and (
        time.monotonic() - started < timeout_s
    ):
        time.sleep(5)
        row = _poll_status(base, run_id)
    return row


def _seed_one(
    base: str, pair: tuple[str, str, str], headers: dict[str, str], timeout_s: float
) -> bool:
    """One run; True when it ended `done`. A cold Render instance can time out: that is a
    failed run, reported on one line, not a traceback."""
    subject, rival, category = pair
    started = time.monotonic()
    try:
        run_id = _start(base, {"subject": subject, "rival": rival, "category": category}, headers)
        row = _wait(base, run_id, started, timeout_s)
    except urllib.error.HTTPError as exc:
        print(f"{subject} vs {rival}: HTTP {exc.code} {exc.read().decode()[:200]}")
        return False
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"{subject} vs {rival}: {type(exc).__name__}: {exc}")
        return False
    wall = time.monotonic() - started
    if row is None:
        print(f"{run_id} not listed after {wall:.1f}s")
        return False
    print(f"{row.run_id} {row.verified_count}/{row.total_count} {wall:.1f}s {row.status}")
    return row.status == "done"


def seed_via_api(base: str, n: int, passcode: str, timeout_s: float) -> int:
    headers = {"Content-Type": "application/json", "X-Demo-Passcode": passcode}
    return sum(not _seed_one(base, pair, headers, timeout_s) for pair in PAIRS[:n])


async def seed_in_process(n: int) -> int:
    from receipts.api.wiring import build_live_service
    from receipts.contracts import DoneEvent, RunRequest
    from receipts.db import SqlRunRepo, create_schema
    from receipts.settings import get_settings

    repo = SqlRunRepo()
    await create_schema(repo.engine)
    service = build_live_service(get_settings(), repo=repo)
    failures = 0
    for subject, rival, category in PAIRS[:n]:
        started = time.monotonic()
        run_id = await service.start(RunRequest(subject=subject, rival=rival, category=category))
        done: DoneEvent | None = None
        async for event in service.events(run_id):
            if isinstance(event, DoneEvent):
                done = event
        await service.wait(run_id)
        wall = time.monotonic() - started
        summaries = {s.run_id: s for s in await service.list()}
        status = summaries[run_id].status if run_id in summaries else "unknown"
        counts = f"{done.verified_count}/{done.total_count}" if done else "?/?"
        print(f"{run_id} {counts} {wall:.1f}s {status}")
        failures += status != "done"
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=1, choices=(1, 2, 3))
    parser.add_argument("--base-url", default="https://receipts-h745.onrender.com")
    parser.add_argument("--passcode-env", default="DEMO_PASSCODE")
    parser.add_argument("--in-process", action="store_true")
    parser.add_argument("--timeout-s", type=float, default=600.0)
    args = parser.parse_args(argv)
    if args.in_process:
        return asyncio.run(seed_in_process(args.n))
    passcode = os.environ.get(args.passcode_env)
    if not passcode:
        print(f"{args.passcode_env} is not set", file=sys.stderr)
        return 2
    return seed_via_api(args.base_url.rstrip("/"), args.n, passcode, args.timeout_s)


if __name__ == "__main__":
    sys.exit(main())
