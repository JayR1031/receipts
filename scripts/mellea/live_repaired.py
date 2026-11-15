"""Live repaired claims for issue #39 (Mellea): Mel vs Warp with repairs on.

Runs the real Anthropic model and Keenable clients, so it spends model and search credits. Each
run uses a fresh temporary SQLite repo (never the Neon database) and the verifier and Mellea
repair loop of the checkout it runs in. Prints one line per run: mode, run_id, UTC start,
verified/total, dropped, wall seconds, and the per-domain `claim repair:` log lines (repairs-on
runs only). Also prints each verified pricing claim with its quote.
The README's `run-a7be7a53cba9` came from this script.
Keys come from the environment (`ANTHROPIC_API_KEY`, `KEENABLE_API_KEY`); none is printed.

usage: uv run python scripts/mellea/live_repaired.py [runs]
"""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from receipts.contracts import DoneEvent, DroppedEvent, QuoteReceipt, RunRequest, VerifiedEvent
from receipts.db import SqlRunRepo, create_schema
from receipts.settings import get_settings

SUBJECT, RIVAL, CATEGORY = "Mel", "Warp", "agentic terminal"


class Capture(logging.Handler):
    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        msg = record.getMessage()
        if msg.startswith("claim repair:"):
            self.lines.append(msg)


async def one_run(repairs_on: bool) -> str:
    from receipts.api.wiring import build_live_service

    get_settings.cache_clear()
    settings = get_settings()
    cap = Capture()
    log = logging.getLogger("receipts.harness.specialist")
    log.setLevel(logging.INFO)
    log.addHandler(cap)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            repo = SqlRunRepo(url=f"sqlite:///{Path(tmp) / 'live.db'}")
            await create_schema(repo.engine)
            kwargs = {} if repairs_on else {"repair_factory": None}
            service = build_live_service(settings, repo=repo, **kwargs)
            start_utc = datetime.now(UTC).strftime("%H:%M:%SZ")
            t0 = time.monotonic()
            run_id = await service.start(
                RunRequest(subject=SUBJECT, rival=RIVAL, category=CATEGORY)
            )
            events = [event async for event in service.events(run_id)]
            wall = time.monotonic() - t0
            await service.wait(run_id)
    finally:
        log.removeHandler(cap)
    done = events[-1]
    dropped = sum(isinstance(e, DroppedEvent) for e in events)
    counts = (
        f"{done.verified_count}/{done.total_count}"
        if isinstance(done, DoneEvent)
        else f"ended {done.kind}"
    )
    for e in events:
        if isinstance(e, VerifiedEvent) and e.domain == "pricing":
            q = (
                e.claim.receipt.quote
                if isinstance(e.claim.receipt, QuoteReceipt)
                else f"search: {e.claim.receipt.query!r}"
            )
            print(
                f"  VERIFIED [{e.claim.verify_method}] claim={e.claim.text[:110]!r}\n"
                f"      quote={q[:130]!r}",
                flush=True,
            )
    mode = "repairs-on " if repairs_on else "repairs-off"
    repair = " | ".join(cap.lines) if cap.lines else "-"
    return (
        f"{mode} {run_id} start={start_utc} verified={counts} dropped={dropped} "
        f"wall={wall:.1f}s repair: {repair}"
    )


async def main(pairs: int) -> None:
    settings = get_settings()
    if settings.anthropic_api_key is None or settings.keenable_api_key is None:
        print("SKIP: ANTHROPIC_API_KEY and KEENABLE_API_KEY are needed")
        return
    for i in range(pairs):
        print(f"repaired run {i + 1}: {await one_run(True)}", flush=True)


asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 2))
