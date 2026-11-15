"""One real comparison end to end: real Anthropic model, real Keenable search and fetch, L2's
verifier, `SqlRunRepo` over a temporary SQLite file (never the Neon database).

Marked `integration`; skipped with a named reason when the keys are absent. Prints one line,
`run_id verified/total wall_s`, that the W2 PR body records. The pair is the hackathon's demo
pair (a live web search over two real public products).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from receipts.contracts import (
    DoneEvent,
    FetchEvent,
    RunEvent,
    RunRequest,
    SearchEvent,
    VerifiedEvent,
)
from receipts.db import SqlRunRepo, create_schema
from receipts.settings import get_settings

pytestmark = pytest.mark.integration

SUBJECT = "Mel"
RIVAL = "Warp"
CATEGORY = "agentic terminal"


def _receipt_urls_seen(events: list[RunEvent]) -> set[str]:
    seen: set[str] = set()
    for event in events:
        if isinstance(event, FetchEvent):
            seen.add(event.url)
        elif isinstance(event, SearchEvent):
            seen.update(row.url for row in event.results)
    return seen


async def test_one_live_comparison_runs_end_to_end(tmp_path: Path) -> None:
    get_settings.cache_clear()
    settings = get_settings()
    if settings.anthropic_api_key is None or settings.keenable_api_key is None:
        pytest.skip("ANTHROPIC_API_KEY and KEENABLE_API_KEY are needed for the live run")

    from receipts.api.wiring import build_live_service

    repo = SqlRunRepo(url=f"sqlite:///{tmp_path / 'live.db'}")
    await create_schema(repo.engine)
    service = build_live_service(settings, repo=repo)

    started = time.monotonic()
    run_id = await service.start(RunRequest(subject=SUBJECT, rival=RIVAL, category=CATEGORY))
    events = [event async for event in service.events(run_id)]
    wall_s = time.monotonic() - started
    await service.wait(run_id)

    assert events, "the stream produced no events"
    done = events[-1]
    assert isinstance(done, DoneEvent), f"stream did not end with DoneEvent: {done.kind}"
    assert done.total_count >= 1, "no claims at all"

    seen = _receipt_urls_seen(events)
    verified = [e.claim for e in events if isinstance(e, VerifiedEvent)]
    for claim in verified:
        assert claim.receipt.url in seen, (
            f"receipt URL not fetched or searched: {claim.receipt.url}"
        )

    card = await service.get(run_id)
    assert card is not None and card.run_id == run_id
    summaries = await service.list()
    assert [s.run_id for s in summaries] == [run_id]
    assert summaries[0].status == "done", f"run ended {summaries[0].status}"

    print(f"\nLIVE RUN {run_id} {done.verified_count}/{done.total_count} {wall_s:.1f}s")
