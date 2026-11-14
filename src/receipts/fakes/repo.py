"""An in-memory `RunRepo`. Unit tests use it in place of the database."""

from __future__ import annotations

from receipts.contracts import Battlecard, RunEvent, RunId, RunSummary


class InMemoryRunRepo:
    def __init__(self) -> None:
        self.runs: dict[RunId, RunSummary] = {}
        self.events: dict[RunId, list[RunEvent]] = {}
        self.battlecards: dict[RunId, Battlecard] = {}

    async def save_run(self, summary: RunSummary) -> None:
        self.runs[summary.run_id] = summary

    async def append_event(self, event: RunEvent) -> None:
        self.events.setdefault(event.run_id, []).append(event)

    async def save_battlecard(self, card: Battlecard) -> None:
        self.battlecards[card.run_id] = card

    async def get_run(self, run_id: RunId) -> Battlecard | None:
        return self.battlecards.get(run_id)

    async def list_runs(self) -> list[RunSummary]:
        """Newest first, by `started_at`, the order the History list shows."""
        return sorted(self.runs.values(), key=lambda s: s.started_at, reverse=True)
