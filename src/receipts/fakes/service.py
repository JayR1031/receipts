"""A `RunService` that replays a scripted event list. The UI and API lanes test against it."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence

from receipts.contracts import (
    Battlecard,
    DoneEvent,
    RunEvent,
    RunId,
    RunRequest,
    RunStatus,
    RunSummary,
    VerifiedEvent,
)


class FakeRunService:
    """Every `start()` replays the same script; `delay_s` spaces the events out."""

    def __init__(self, script: Sequence[RunEvent], delay_s: float = 0.0) -> None:
        if not script:
            raise ValueError("FakeRunService needs at least one scripted event")
        self.script: tuple[RunEvent, ...] = tuple(script)
        self.delay_s = delay_s
        self.requests: dict[RunId, RunRequest] = {}

    @property
    def run_id(self) -> RunId:
        return self.script[0].run_id

    async def start(self, request: RunRequest) -> RunId:
        self.requests[self.run_id] = request
        return self.run_id

    async def events(self, run_id: RunId) -> AsyncIterator[RunEvent]:
        if run_id != self.run_id:
            return
        for event in self.script:
            if self.delay_s:
                await asyncio.sleep(self.delay_s)
            yield event

    async def get(self, run_id: RunId) -> Battlecard | None:
        request = self.requests.get(run_id)
        if request is None:
            return None
        done = self._done()
        verified = tuple(e.claim for e in self.script if isinstance(e, VerifiedEvent))
        return Battlecard(
            run_id=run_id,
            subject=request.subject,
            rival=request.rival,
            claims=verified,
            verified_count=done.verified_count if done else len(verified),
            total_count=done.total_count if done else len(verified),
            started_at=self.script[0].ts,
            finished_at=self.script[-1].ts,
        )

    async def list(self) -> list[RunSummary]:
        done = self._done()
        status: RunStatus = "done" if done else "running"
        return [
            RunSummary(
                run_id=run_id,
                subject=request.subject,
                rival=request.rival,
                status=status,
                verified_count=done.verified_count if done else 0,
                total_count=done.total_count if done else 0,
                started_at=self.script[0].ts,
            )
            for run_id, request in self.requests.items()
        ]

    def _done(self) -> DoneEvent | None:
        return next((e for e in self.script if isinstance(e, DoneEvent)), None)
