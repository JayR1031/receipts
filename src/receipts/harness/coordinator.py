"""Fan a run out over its domain packs, bounded by a semaphore, and merge the event streams.

`StartedEvent` is always first and `DoneEvent` always last. A specialist that raises becomes an
`ErrorEvent` for its domain; the other specialists finish. One task per pack is created up front
and joined with `asyncio.gather`; `asyncio.Semaphore(max_concurrent)` bounds how many run at once.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Sequence
from typing import Protocol

from receipts.contracts import (
    ClaimEvent,
    DomainPack,
    DoneEvent,
    ErrorEvent,
    RunEvent,
    RunId,
    RunRequest,
    StartedEvent,
    VerifiedEvent,
)
from receipts.harness.specialist import Clock, utc_now


class Specialist(Protocol):
    """What the Coordinator needs from a runner; `SpecialistRunner` satisfies it."""

    def run(
        self, run_id: RunId, request: RunRequest, pack: DomainPack
    ) -> AsyncIterator[RunEvent]: ...


class Coordinator:
    def __init__(
        self,
        packs: Sequence[DomainPack],
        specialist: Specialist,
        *,
        max_concurrent: int,
        clock: Clock = utc_now,
    ) -> None:
        if max_concurrent < 1:
            raise ValueError("max_concurrent must be at least 1")
        self._packs = tuple(packs)
        self._specialist = specialist
        self._max_concurrent = max_concurrent
        self._clock = clock

    async def _one(
        self,
        run_id: RunId,
        request: RunRequest,
        pack: DomainPack,
        gate: asyncio.Semaphore,
        queue: asyncio.Queue[RunEvent | None],
    ) -> None:
        try:
            async with gate:
                async for event in self._specialist.run(run_id, request, pack):
                    await queue.put(event)
        except Exception as exc:  # a failing specialist must not kill the others
            message = f"{pack.id} specialist failed: {type(exc).__name__}: {exc}"
            await queue.put(
                ErrorEvent(run_id=run_id, ts=self._clock(), domain=pack.id, message=message)
            )
        finally:
            await queue.put(None)

    async def run(self, run_id: RunId, request: RunRequest) -> AsyncIterator[RunEvent]:
        yield StartedEvent(
            run_id=run_id,
            ts=self._clock(),
            subject=request.subject,
            rival=request.rival,
            category=request.category,
            domains=tuple(pack.id for pack in self._packs),
        )
        gate = asyncio.Semaphore(self._max_concurrent)
        queue: asyncio.Queue[RunEvent | None] = asyncio.Queue()
        tasks = [
            asyncio.create_task(self._one(run_id, request, pack, gate, queue))
            for pack in self._packs
        ]
        pending = len(tasks)
        verified = total = 0
        while pending:
            event = await queue.get()
            if event is None:
                pending -= 1
                continue
            total += isinstance(event, ClaimEvent)
            verified += isinstance(event, VerifiedEvent)
            yield event
        await asyncio.gather(*tasks)
        yield DoneEvent(run_id=run_id, ts=self._clock(), verified_count=verified, total_count=total)
