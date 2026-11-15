"""`InProcessRunService`: starts a run as a background task, streams its events to any number of
subscribers (late subscribers replay the history first) and persists through an injected `RunRepo`.

`events()` is an `async def` generator, which satisfies the protocol's plain `def events(...) ->
AsyncIterator[RunEvent]`. Every stream ends with a `DoneEvent`, also after a failure (preceded by
an `ErrorEvent`), so a UI can always stop on `done`.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from datetime import datetime

from receipts.contracts import (
    Battlecard,
    Claim,
    DoneEvent,
    DroppedEvent,
    ErrorEvent,
    RunEvent,
    RunId,
    RunRepo,
    RunRequest,
    RunStatus,
    RunSummary,
    StartedEvent,
    VerifiedEvent,
)
from receipts.harness.coordinator import Coordinator
from receipts.harness.specialist import Clock, utc_now


def new_uuid_run_id() -> RunId:
    return RunId(f"run-{uuid.uuid4().hex[:12]}")


@dataclass
class _RunState:
    request: RunRequest
    started_at: datetime
    history: list[RunEvent] = field(default_factory=list[RunEvent])
    subscribers: list[asyncio.Queue[RunEvent | None]] = field(
        default_factory=list[asyncio.Queue[RunEvent | None]]
    )
    claims: list[Claim] = field(default_factory=list[Claim])
    verified_count: int = 0
    total_count: int = 0
    done: bool = False
    task: asyncio.Task[None] | None = None


class InProcessRunService:
    def __init__(
        self,
        coordinator: Coordinator,
        repo: RunRepo,
        *,
        clock: Clock = utc_now,
        new_run_id: Callable[[], RunId] = new_uuid_run_id,
    ) -> None:
        self._coordinator = coordinator
        self._repo = repo
        self._clock = clock
        self._new_run_id = new_run_id
        self._runs: dict[RunId, _RunState] = {}

    # --- RunService ------------------------------------------------------------------------

    async def start(self, request: RunRequest) -> RunId:
        run_id = self._new_run_id()
        state = _RunState(request=request, started_at=self._clock())
        self._runs[run_id] = state
        await self._repo.save_run(self._summary(run_id, state, "running"))
        state.task = asyncio.create_task(self._drive(run_id, state))
        return run_id

    async def events(self, run_id: RunId) -> AsyncIterator[RunEvent]:
        state = self._runs.get(run_id)
        if state is None:
            return
        queue: asyncio.Queue[RunEvent | None] = asyncio.Queue()
        state.subscribers.append(queue)  # registered before the snapshot, with no await between
        snapshot = list(state.history)
        finished = state.done
        for event in snapshot:
            yield event
        if finished:
            return
        while (event := await queue.get()) is not None:
            yield event

    async def get(self, run_id: RunId) -> Battlecard | None:
        return await self._repo.get_run(run_id)

    async def list(self) -> list[RunSummary]:
        return await self._repo.list_runs()

    async def wait(self, run_id: RunId) -> None:
        """Block until the run's background task has finished (tests and W2 use this)."""
        state = self._runs.get(run_id)
        if state is not None and state.task is not None:
            await state.task

    # --- the background task ------------------------------------------------------------------

    async def _drive(self, run_id: RunId, state: _RunState) -> None:
        try:
            async for event in self._coordinator.run(run_id, state.request):
                await self._publish(run_id, state, event)
            await self._finish(run_id, state, "done")
        except Exception as exc:  # the run must still end with a DoneEvent for its subscribers
            message = f"run failed: {type(exc).__name__}: {exc}"
            await self._publish(
                run_id, state, ErrorEvent(run_id=run_id, ts=self._clock(), message=message)
            )
            await self._publish(
                run_id,
                state,
                DoneEvent(
                    run_id=run_id,
                    ts=self._clock(),
                    verified_count=state.verified_count,
                    total_count=state.total_count,
                ),
            )
            await self._finish(run_id, state, "error")
        finally:
            state.done = True
            for queue in state.subscribers:
                queue.put_nowait(None)

    async def _publish(self, run_id: RunId, state: _RunState, event: RunEvent) -> None:
        self._record(state, event)
        state.history.append(event)
        await self._repo.append_event(event)
        for queue in state.subscribers:
            queue.put_nowait(event)

    @staticmethod
    def _record(state: _RunState, event: RunEvent) -> None:
        if isinstance(event, StartedEvent):
            state.started_at = event.ts
        elif isinstance(event, VerifiedEvent | DroppedEvent):
            state.claims.append(event.claim)
        elif isinstance(event, DoneEvent):
            state.verified_count = event.verified_count
            state.total_count = event.total_count

    async def _finish(self, run_id: RunId, state: _RunState, status: RunStatus) -> None:
        finished_at = state.history[-1].ts if state.history else self._clock()
        await self._repo.save_battlecard(
            Battlecard(
                run_id=run_id,
                subject=state.request.subject,
                rival=state.request.rival,
                claims=tuple(state.claims),
                verified_count=state.verified_count,
                total_count=state.total_count,
                started_at=state.started_at,
                finished_at=finished_at,
            )
        )
        await self._repo.save_run(self._summary(run_id, state, status))

    @staticmethod
    def _summary(run_id: RunId, state: _RunState, status: RunStatus) -> RunSummary:
        return RunSummary(
            run_id=run_id,
            subject=state.request.subject,
            rival=state.request.rival,
            status=status,
            verified_count=state.verified_count,
            total_count=state.total_count,
            started_at=state.started_at,
        )
